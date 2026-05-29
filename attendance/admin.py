from django.contrib import admin
from .models import UserProfile, Hall, Session, Citizen, AttendanceRecord, Announcement, LoginActivity

admin.site.site_header = "San Jose Barangay Admin"
admin.site.site_title = "Barangay Official Attendance Registry"
admin.site.index_title = "Barangay Management"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'position', 'contact_number', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'user__username']


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'capacity', 'status']
    list_filter = ['status']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'session_type', 'date', 'start_time', 'status', 'hall', 'attendance_count']
    list_filter = ['session_type', 'status', 'date']
    search_fields = ['title', 'presided_by']
    date_hierarchy = 'date'


@admin.register(Citizen)
class CitizenAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'category', 'gender', 'contact_number', 'is_active']
    list_filter = ['category', 'gender', 'civil_status', 'is_active']
    search_fields = ['first_name', 'last_name', 'contact_number', 'voter_id']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['citizen', 'session', 'status', 'time_in', 'time_out', 'marked_by']
    list_filter = ['status', 'session__date']
    search_fields = ['citizen__first_name', 'citizen__last_name']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'is_published', 'published_by', 'created_at']
    list_filter = ['priority', 'is_published']


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ['username_attempted', 'user', 'action', 'ip_address', 'timestamp']
    list_filter = ['action']
    search_fields = ['username_attempted', 'user__username', 'ip_address']
    readonly_fields = ['user', 'username_attempted', 'action', 'ip_address', 'user_agent', 'timestamp', 'notes']
    date_hierarchy = 'timestamp'
