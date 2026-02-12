from __future__ import annotations

from django.contrib import admin

from api.partners.common.models import (
    Partner,
    PartnerIotHistory,
    PayoutRequest,
    RevenueDistribution,
    StationDistribution,
    StationRevenueShare,
)


class BasePartnerAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    list_per_page = 50
    date_hierarchy = "created_at"
    save_on_top = True


class NoDeleteAdmin(BasePartnerAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Partner)
class PartnerAdmin(BasePartnerAdmin):
    list_display = (
        "code",
        "business_name",
        "partner_type",
        "vendor_type",
        "status",
        "parent",
        "balance",
        "total_earnings",
        "has_dashboard_access_display",
        "created_at",
    )
    list_filter = ("partner_type", "vendor_type", "status", "created_at", "assigned_at")
    search_fields = (
        "code",
        "business_name",
        "contact_phone",
        "contact_email",
        "user__email",
        "user__phone_number",
        "parent__code",
        "parent__business_name",
    )
    list_select_related = ("user", "parent", "assigned_by")
    autocomplete_fields = ("user", "parent", "assigned_by")
    readonly_fields = BasePartnerAdmin.readonly_fields + ("assigned_at",)
    list_editable = ("status",)
    fieldsets = (
        ("Identity", {"fields": ("id", "code", "partner_type", "vendor_type", "status")}),
        ("Account Link", {"fields": ("user", "parent")}),
        ("Business", {"fields": ("business_name", "contact_phone", "contact_email", "address")}),
        ("Commercial", {"fields": ("upfront_amount", "revenue_share_percent", "balance", "total_earnings")}),
        ("Request Context", {"fields": ("subject", "message", "notes"), "classes": ("collapse",)}),
        ("Assignment", {"fields": ("assigned_by", "assigned_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(boolean=True, description="Dashboard Access")
    def has_dashboard_access_display(self, obj):
        return obj.has_dashboard_access


@admin.register(StationDistribution)
class StationDistributionAdmin(BasePartnerAdmin):
    list_display = (
        "station",
        "partner",
        "distribution_type",
        "is_active",
        "effective_date",
        "expiry_date",
        "created_at",
    )
    list_filter = ("distribution_type", "is_active", "effective_date", "created_at")
    search_fields = (
        "station__serial_number",
        "station__station_name",
        "partner__code",
        "partner__business_name",
        "notes",
    )
    list_select_related = ("station", "partner", "assigned_by")
    autocomplete_fields = ("station", "partner", "assigned_by")
    readonly_fields = BasePartnerAdmin.readonly_fields + ("effective_date",)
    list_editable = ("is_active",)
    fieldsets = (
        ("Distribution", {"fields": ("id", "station", "partner", "distribution_type", "is_active")}),
        ("Validity", {"fields": ("effective_date", "expiry_date")}),
        ("Audit", {"fields": ("assigned_by", "notes")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(StationRevenueShare)
class StationRevenueShareAdmin(BasePartnerAdmin):
    list_display = (
        "distribution",
        "revenue_model",
        "partner_percent",
        "fixed_amount",
        "created_at",
    )
    list_filter = ("revenue_model", "created_at")
    search_fields = (
        "distribution__partner__code",
        "distribution__partner__business_name",
        "distribution__station__serial_number",
        "distribution__station__station_name",
    )
    list_select_related = ("distribution", "distribution__partner", "distribution__station")
    autocomplete_fields = ("distribution",)
    fieldsets = (
        ("Configuration", {"fields": ("id", "distribution", "revenue_model")}),
        ("Percentage Model", {"fields": ("partner_percent",)}),
        ("Fixed Model", {"fields": ("fixed_amount",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(RevenueDistribution)
class RevenueDistributionAdmin(NoDeleteAdmin):
    list_display = (
        "id",
        "transaction",
        "station",
        "gross_amount",
        "net_amount",
        "chargeghar_share",
        "franchise",
        "vendor",
        "is_distributed",
        "distributed_at",
        "is_reversal",
        "created_at",
    )
    list_filter = (
        "is_distributed",
        "is_reversal",
        "reversal_reason",
        "created_at",
        "distributed_at",
    )
    search_fields = (
        "id",
        "transaction__transaction_id",
        "station__serial_number",
        "station__station_name",
        "franchise__code",
        "vendor__code",
    )
    list_select_related = (
        "transaction",
        "rental",
        "station",
        "franchise",
        "vendor",
        "reversed_distribution",
    )
    autocomplete_fields = ("transaction", "station", "franchise", "vendor", "reversed_distribution")
    raw_id_fields = ("rental",)
    readonly_fields = BasePartnerAdmin.readonly_fields
    fieldsets = (
        ("Source", {"fields": ("id", "transaction", "rental", "station")}),
        ("Amounts", {"fields": ("gross_amount", "vat_amount", "service_charge", "net_amount")}),
        ("Shares", {"fields": ("chargeghar_share", "franchise", "franchise_share", "vendor", "vendor_share")}),
        ("Distribution", {"fields": ("is_distributed", "distributed_at")}),
        (
            "Reversal",
            {"fields": ("is_reversal", "reversed_distribution", "reversal_reason"), "classes": ("collapse",)},
        ),
        ("Details", {"fields": ("calculation_details",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(PayoutRequest)
class PayoutRequestAdmin(NoDeleteAdmin):
    list_display = (
        "reference_id",
        "partner",
        "payout_type",
        "amount",
        "net_amount",
        "status",
        "processed_by",
        "processed_at",
        "created_at",
    )
    list_filter = ("payout_type", "status", "created_at", "processed_at")
    search_fields = (
        "reference_id",
        "partner__code",
        "partner__business_name",
        "partner__user__email",
        "partner__user__phone_number",
        "bank_name",
        "account_number",
        "account_holder_name",
    )
    list_select_related = ("partner", "partner__user", "processed_by")
    autocomplete_fields = ("partner", "processed_by")
    readonly_fields = BasePartnerAdmin.readonly_fields + ("net_amount",)
    list_editable = ("status",)
    fieldsets = (
        ("Request", {"fields": ("id", "reference_id", "partner", "payout_type", "status")}),
        ("Amounts", {"fields": ("amount", "vat_deducted", "service_charge_deducted", "net_amount")}),
        ("Bank", {"fields": ("bank_name", "account_number", "account_holder_name")}),
        ("Processing", {"fields": ("processed_by", "processed_at", "rejection_reason", "admin_notes")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(PartnerIotHistory)
class PartnerIotHistoryAdmin(NoDeleteAdmin):
    list_display = (
        "partner",
        "performed_by",
        "station",
        "action_type",
        "performed_from",
        "is_successful",
        "is_free_ejection",
        "created_at",
    )
    list_filter = (
        "action_type",
        "performed_from",
        "is_successful",
        "is_free_ejection",
        "created_at",
    )
    search_fields = (
        "partner__code",
        "partner__business_name",
        "performed_by__email",
        "performed_by__phone_number",
        "station__serial_number",
        "station__station_name",
        "powerbank_sn",
        "error_message",
    )
    list_select_related = ("partner", "performed_by", "station", "rental")
    autocomplete_fields = ("partner", "performed_by", "station")
    raw_id_fields = ("rental",)
    readonly_fields = BasePartnerAdmin.readonly_fields
    fieldsets = (
        ("Action", {"fields": ("id", "partner", "performed_by", "station", "action_type", "performed_from")}),
        ("Eject Context", {"fields": ("powerbank_sn", "slot_number", "rental", "is_free_ejection")}),
        ("Result", {"fields": ("is_successful", "error_message")}),
        ("Payloads", {"fields": ("request_payload", "response_data"), "classes": ("collapse",)}),
        ("Client", {"fields": ("ip_address", "user_agent"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
