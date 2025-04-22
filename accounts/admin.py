from django.contrib import admin
from .models import (
    UserProfile, Donor, Receiver,
    State, District, BloodBank, BloodStock
)

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')
    list_filter = ('state',)
    search_fields = ('name', 'state__name')

@admin.register(BloodBank)
class BloodBankAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'contact_number', 'email', 'is_active', 'updated_at')
    list_filter = ('is_active', 'district__state', 'district')
    search_fields = ('name', 'address', 'contact_number', 'email', 'license_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'district')
        }),
        ('Contact Details', {
            'fields': ('contact_number', 'email')
        }),
        ('Administrative', {
            'fields': ('license_number', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(BloodStock)
class BloodStockAdmin(admin.ModelAdmin):
    list_display = ('blood_bank', 'blood_group', 'component', 'units_available', 'stock_level_status', 'last_updated')
    list_filter = ('blood_group', 'component', 'blood_bank__district__state', 'blood_bank')
    search_fields = ('blood_bank__name',)
    readonly_fields = ('last_updated',)
    
    def stock_level_status(self, obj):
        percentage = obj.get_stock_level_percentage()
        if percentage > 70:
            return '✅ High'
        elif percentage > 30:
            return '⚠️ Medium'
        return '❌ Low'
    stock_level_status.short_description = 'Stock Level'

# Register existing models if not already registered
admin.site.register(UserProfile)
admin.site.register(Donor)
admin.site.register(Receiver)
