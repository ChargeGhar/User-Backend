"""
Advertisement Admin
===================
Django admin configuration for advertisement models.
"""
from django.contrib import admin
from api.user.advertisements.models import AdRequest, AdContent, AdDistribution


@admin.register(AdRequest)
class AdRequestAdmin(admin.ModelAdmin):
    """Admin interface for AdRequest"""
    
    list_display = [
        'id', 'title', 'user', 'status', 'admin_price',
        'submitted_at', 'start_date', 'end_date'
    ]
    list_filter = ['status', 'submitted_at', 'start_date']
    search_fields = ['title', 'full_name', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'submitted_at', 'paid_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'full_name', 'contact_number', 'status')
        }),
        ('Ad Details', {
            'fields': ('title', 'description', 'duration_days', 'admin_price')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'admin_notes', 'rejection_reason')
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Payment', {
            'fields': ('transaction', 'paid_at')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'reviewed_by', 'approved_by', 'transaction'
        )


@admin.register(AdContent)
class AdContentAdmin(admin.ModelAdmin):
    """Admin interface for AdContent"""
    
    list_display = [
        'id', 'ad_request', 'content_type', 'duration_seconds',
        'display_order', 'is_active'
    ]
    list_filter = ['content_type', 'is_active', 'created_at']
    search_fields = ['ad_request__title', 'ad_request__user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'ad_request', 'content_type', 'media_upload')
        }),
        ('Display Settings', {
            'fields': ('duration_seconds', 'display_order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'ad_request', 'media_upload'
        )


@admin.register(AdDistribution)
class AdDistributionAdmin(admin.ModelAdmin):
    """Admin interface for AdDistribution"""
    
    list_display = [
        'id', 'ad_content', 'station', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'ad_content__ad_request__title',
        'station__station_name',
        'station__serial_number'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Distribution', {
            'fields': ('id', 'ad_content', 'station')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'ad_content__ad_request', 'station'
        )
