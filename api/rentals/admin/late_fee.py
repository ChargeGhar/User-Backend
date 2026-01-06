from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.rentals.models.late_fee import LateFeeConfiguration

@admin.register(LateFeeConfiguration)
class LateFeeConfigurationAdmin(ModelAdmin):
    list_display = [
        'name', 'fee_type', 'multiplier', 'flat_rate_per_hour',
        'grace_period_minutes', 'is_active', 'get_description_short'
    ]
    list_filter = ['fee_type', 'is_active', 'created_at']
    search_fields = ['name', 'fee_type']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'get_calculated_description']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        self.help_text = """
        <div style="background: #f8f9fa; padding: 15px; margin-bottom: 15px; border-left: 4px solid #007bff;">
            <h3 style="color: #007bff; margin-top: 0;">💡 Late Fee Configuration Help</h3>
            <p>Sets the extra charges for customers who return power banks after their rental time expires.</p>
        </div>
        """
        return form

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if 'adminform' in context and hasattr(context['adminform'].form, 'help_text'):
             context['adminform'].form.help_text = getattr(self, 'help_text', "")
        return super().render_change_form(request, context, add, change, form_url, obj)

    fieldsets = (
        ('Basic Information', {'fields': ('name', 'is_active')}),
        ('Fee Configuration', {'fields': ('fee_type', 'multiplier', 'flat_rate_per_hour', 'grace_period_minutes', 'max_daily_rate')}),
        ('Calculated Information', {'fields': ('get_calculated_description',), 'classes': ('collapse',)}),
    )

    def get_description_short(self, obj):
        desc = obj.get_description()
        return desc[:50] + '...' if len(desc) > 50 else desc
    get_description_short.short_description = 'Description'

    def get_calculated_description(self, obj):
        return obj.get_description()
    get_calculated_description.short_description = 'Full Description'

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            LateFeeConfiguration.objects.filter(is_active=True).exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)
