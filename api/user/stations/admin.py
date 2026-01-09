from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.user.stations.models import (
    Station, StationSlot, StationAmenity, StationAmenityMapping,
    StationIssue, StationMedia, PowerBank, UserStationFavorite
)


@admin.register(Station)
class StationAdmin(ModelAdmin):
    list_display = ['station_name', 'address', 'status', 'total_slots', 'is_maintenance', 'last_heartbeat']
    list_filter = ['status', 'is_maintenance', 'created_at']
    search_fields = ['station_name', 'address', 'serial_number', 'imei']
    readonly_fields = ['created_at', 'updated_at', 'last_heartbeat']


@admin.register(StationSlot)
class StationSlotAdmin(ModelAdmin):
    list_display = ['station', 'slot_number', 'status', 'battery_level', 'current_rental', 'last_updated']
    list_filter = ['status', 'station', 'last_updated']
    search_fields = ['station__station_name']
    readonly_fields = ['created_at', 'last_updated']


@admin.register(StationAmenity)
class StationAmenityAdmin(ModelAdmin):
    list_display = ['name', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(StationAmenityMapping)
class StationAmenityMappingAdmin(ModelAdmin):
    list_display = ['station', 'amenity', 'is_available']
    list_filter = ['is_available', 'amenity']
    search_fields = ['station__station_name', 'amenity__name']


@admin.register(StationIssue)
class StationIssueAdmin(ModelAdmin):
    list_display = ['station', 'issue_type', 'priority', 'status', 'reported_by', 'reported_at']
    list_filter = ['issue_type', 'priority', 'status', 'reported_at']
    search_fields = ['station__station_name', 'description', 'reported_by__username']
    readonly_fields = ['reported_at', 'resolved_at', 'created_at']


@admin.register(StationMedia)
class StationMediaAdmin(ModelAdmin):
    list_display = ['station', 'media_type', 'title', 'is_primary', 'created_at']
    list_filter = ['media_type', 'is_primary', 'created_at']
    search_fields = ['station__station_name', 'title']
    readonly_fields = ['created_at']


@admin.register(PowerBank)
class PowerBankAdmin(ModelAdmin):
    list_display = ['serial_number', 'model', 'status', 'battery_level', 'current_station', 'last_updated']
    list_filter = ['status', 'model', 'current_station']
    search_fields = ['serial_number', 'model']
    readonly_fields = ['created_at', 'last_updated']


@admin.register(UserStationFavorite)
class UserStationFavoriteAdmin(ModelAdmin):
    list_display = ['user', 'station', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'station__station_name']
    readonly_fields = ['created_at']