from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.rentals.models.rental import Rental, RentalPackage, RentalExtension, RentalIssue, RentalLocation

@admin.register(RentalPackage)
class RentalPackageAdmin(ModelAdmin):
    list_display = ['name', 'package_type', 'duration_minutes', 'price', 'payment_model', 'is_active']
    list_filter = ['package_type', 'payment_model', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['price']


@admin.register(Rental)
class RentalAdmin(ModelAdmin):
    list_display = ['rental_code', 'user', 'station', 'status', 'payment_status', 'started_at', 'due_at', 'ended_at']
    list_filter = ['status', 'payment_status', 'started_at', 'due_at']
    search_fields = ['rental_code', 'user__username', 'user__phone_number', 'station__name']
    readonly_fields = ['rental_code', 'started_at', 'ended_at', 'amount_paid', 'overdue_amount']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'station', 'package')


@admin.register(RentalExtension)
class RentalExtensionAdmin(ModelAdmin):
    list_display = ['rental', 'package', 'extended_minutes', 'extension_cost', 'extended_at']
    list_filter = ['extended_at']
    search_fields = ['rental__rental_code', 'rental__user__username']
    readonly_fields = ['extended_at']


@admin.register(RentalIssue)
class RentalIssueAdmin(ModelAdmin):
    list_display = ['rental', 'issue_type', 'status', 'reported_at', 'resolved_at']
    list_filter = ['issue_type', 'status', 'reported_at']
    search_fields = ['rental__rental_code', 'description']
    readonly_fields = ['reported_at']


@admin.register(RentalLocation)
class RentalLocationAdmin(ModelAdmin):
    list_display = ['rental', 'latitude', 'longitude', 'accuracy', 'recorded_at']
    list_filter = ['recorded_at']
    search_fields = ['rental__rental_code']
    readonly_fields = ['recorded_at']
