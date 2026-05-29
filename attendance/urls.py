from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register-user/', views.register_user, name='register_user'),
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/profile/', views.user_profile_view, name='user_profile_view'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # ── Profile ───────────────────────────────────────────────────────────────
    path('profile/', views.my_profile, name='my_profile'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Sessions ──────────────────────────────────────────────────────────────
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('sessions/<int:session_pk>/mark-attendance/', views.mark_attendance, name='mark_attendance'),
    path('sessions/<int:session_pk>/pdf/', views.pdf_report, name='pdf_report'),
    path('sessions/<int:session_pk>/export-csv/', views.export_csv, name='export_csv'),

    # ── Attendance ─────────────────────────────────────────────────────────────
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('sessions/<int:session_pk>/time-in/<int:citizen_pk>/', views.time_in, name='time_in'),
    path('sessions/<int:session_pk>/time-out/<int:citizen_pk>/', views.time_out, name='time_out'),

    # ── Citizens ──────────────────────────────────────────────────────────────
    path('citizens/', views.citizen_list, name='citizen_list'),
    path('citizens/register/', views.citizen_create, name='citizen_create'),
    path('citizens/<int:pk>/', views.citizen_detail, name='citizen_detail'),
    path('citizens/<int:pk>/edit/', views.citizen_edit, name='citizen_edit'),
    path('citizens/<int:pk>/delete/', views.citizen_delete, name='citizen_delete'),

    # ── Halls ─────────────────────────────────────────────────────────────────
    path('halls/', views.hall_list, name='hall_list'),
    path('halls/add/', views.hall_create, name='hall_create'),
    path('halls/<int:pk>/edit/', views.hall_edit, name='hall_edit'),
    path('halls/<int:pk>/delete/', views.hall_delete, name='hall_delete'),

    # ── Announcements ─────────────────────────────────────────────────────────
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/post/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),

    # ── Reports & Calendar ────────────────────────────────────────────────────
    path('reports/', views.reports, name='reports'),
    path('calendar/', views.calendar_view, name='calendar'),

    # ── Admin: Login Activity Log ──────────────────────────────────────────────
    path('admin-panel/login-activity/', views.login_activity_log, name='login_activity_log'),

    # ══ PUNONG BARANGAY (CAPTAIN) ══════════════════════════════════════════════
    path('captain/', views.captain_dashboard, name='captain_dashboard'),
    path('approvals/', views.approval_list, name='approval_list'),
    path('approvals/create/', views.approval_create, name='approval_create'),
    path('approvals/<int:pk>/action/', views.approval_action, name='approval_action'),

    # ── Ordinances & Resolutions ───────────────────────────────────────────────
    path('ordinances/', views.ordinance_list, name='ordinance_list'),
    path('ordinances/create/', views.ordinance_create, name='ordinance_create'),
    path('ordinances/<int:pk>/', views.ordinance_detail, name='ordinance_detail'),
    path('ordinances/<int:pk>/approve/', views.ordinance_approve, name='ordinance_approve'),

    # ── Projects & Programs ────────────────────────────────────────────────────
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/approve/', views.project_approve, name='project_approve'),

    # ── Complaints & Cases ────────────────────────────────────────────────────
    path('complaints/', views.complaint_list, name='complaint_list'),
    path('complaints/file/', views.complaint_create, name='complaint_create'),
    path('complaints/<int:pk>/', views.complaint_detail, name='complaint_detail'),

    # ══ TREASURER ══════════════════════════════════════════════════════════════
    path('treasurer/', views.treasurer_dashboard, name='treasurer_dashboard'),
    path('finances/', views.financial_list, name='financial_list'),
    path('finances/create/', views.financial_create, name='financial_create'),
    path('finances/<int:pk>/approve/', views.financial_approve, name='financial_approve'),
    path('budget/', views.budget_list, name='budget_list'),
    path('budget/create/', views.budget_create, name='budget_create'),

    # ══ TANOD ══════════════════════════════════════════════════════════════════
    path('tanod/', views.tanod_dashboard, name='tanod_dashboard'),
    path('incidents/', views.incident_list, name='incident_list'),
    path('incidents/report/', views.incident_create, name='incident_create'),
    path('incidents/<int:pk>/', views.incident_detail, name='incident_detail'),
    path('patrols/', views.patrol_list, name='patrol_list'),
    path('patrols/create/', views.patrol_create, name='patrol_create'),

    # ══ BHW ════════════════════════════════════════════════════════════════════
    path('bhw/', views.bhw_dashboard, name='bhw_dashboard'),
    path('health-records/', views.health_record_list, name='health_record_list'),
    path('health-records/create/', views.health_record_create, name='health_record_create'),
    path('immunizations/', views.immunization_list, name='immunization_list'),
    path('immunizations/create/', views.immunization_create, name='immunization_create'),
    path('household-visits/', views.household_visit_list, name='household_visit_list'),
    path('household-visits/create/', views.household_visit_create, name='household_visit_create'),

    # ══ BNS ════════════════════════════════════════════════════════════════════
    path('bns/', views.bns_dashboard, name='bns_dashboard'),
    path('nutrition-records/', views.nutrition_record_list, name='nutrition_record_list'),
    path('nutrition-records/create/', views.nutrition_record_create, name='nutrition_record_create'),
    path('feeding-programs/', views.feeding_program_list, name='feeding_program_list'),
    path('feeding-programs/create/', views.feeding_program_create, name='feeding_program_create'),

    # ══ UTILITY / ADMIN STAFF ══════════════════════════════════════════════════
    path('utility/', views.utility_dashboard, name='utility_dashboard'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/update/', views.task_update_status, name='task_update_status'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/create/', views.inventory_create, name='inventory_create'),
    path('daily-log/', views.daily_log_create, name='daily_log_create'),

    # ── Audit Log ─────────────────────────────────────────────────────────────
    path('audit-log/', views.audit_log_list, name='audit_log_list'),

    # ── REST API Endpoints ─────────────────────────────────────────────────────
    path('api/sessions/', views.api_sessions, name='api_sessions'),
    path('api/dashboard-stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/citizens/search/', views.api_citizen_search, name='api_citizen_search'),
    path('api/sessions/<int:session_pk>/attendance/<int:citizen_pk>/',
         views.api_attendance_record, name='api_attendance_record'),
    path('api/sessions/<int:session_pk>/summary/',
         views.api_session_attendance_summary, name='api_session_attendance_summary'),
    path('api/login-activities/', views.api_login_activities, name='api_login_activities'),
    path('api/users/', views.api_users, name='api_users'),
    path('api/captain-stats/', views.api_captain_stats, name='api_captain_stats'),
    path('api/financial-summary/', views.api_financial_summary, name='api_financial_summary'),
]
