from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
import json
import datetime
import csv

from .models import (UserProfile, Hall, Session, Citizen, AttendanceRecord, Announcement, LoginActivity,
                    Ordinance, ApprovalRequest, BarangayProject, FinancialRecord, BudgetAllocation,
                    Complaint, IncidentReport, PatrolSchedule, HealthRecord, ImmunizationRecord,
                    NutritionRecord, FeedingProgram, HouseholdVisit, MaintenanceTask, InventoryItem,
                    DailyActivityLog, AuditLog)
from .forms import (LoginForm, UserRegistrationForm, HallForm, SessionForm,
                    CitizenForm, AttendanceForm, AnnouncementForm, DateRangeFilterForm,
                    UserProfileEditForm)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')


def is_punong_barangay(user):
    return hasattr(user, 'profile') and user.profile.role == 'punong_barangay'

def is_admin(user):
    return hasattr(user, 'profile') and user.profile.role == 'admin'

def is_captain_or_admin(user):
    return hasattr(user, 'profile') and user.profile.role in ['punong_barangay', 'admin']

def is_treasurer(user):
    return hasattr(user, 'profile') and user.profile.role in ['treasurer', 'admin']

def is_admin_or_secretary(user):
    return hasattr(user, 'profile') and user.profile.role in ['admin', 'secretary']

def is_staff_or_above(user):
    return hasattr(user, 'profile') and user.profile.role in ['admin', 'secretary', 'kagawad', 'staff']

def role_required(role_check_fn):
    def decorator(view_func):
        decorated = login_required(user_passes_test(role_check_fn)(view_func))
        return decorated
    return decorator


# ─── Auth Views ────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        username_attempted = request.POST.get('username', '')
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            LoginActivity.objects.create(
                user=user,
                username_attempted=user.username,
                action='login',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
            )
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            LoginActivity.objects.create(
                username_attempted=username_attempted,
                action='failed',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
                notes='Invalid credentials',
            )
    return render(request, 'registration/login.html', {'form': form})


@login_required
def logout_view(request):
    LoginActivity.objects.create(
        user=request.user,
        username_attempted=request.user.username,
        action='logout',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
    )
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
@user_passes_test(is_admin)
def register_user(request):
    form = UserRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.email = form.cleaned_data['email']
        user.save()
        user.profile.role = form.cleaned_data['role']
        user.profile.position = form.cleaned_data['position']
        user.profile.contact_number = form.cleaned_data['contact_number']
        user.profile.save()
        LoginActivity.objects.create(
            user=user,
            username_attempted=user.username,
            action='register',
            ip_address=get_client_ip(request),
            notes=f'Registered by {request.user.username}',
        )
        messages.success(request, f'User {user.username} registered successfully.')
        return redirect('user_list')
    return render(request, 'attendance/register_user.html', {'form': form})


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def my_profile(request):
    """View/edit current user's own profile."""
    profile = request.user.profile
    form = UserProfileEditForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        user=request.user
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('my_profile')
    recent_activity = LoginActivity.objects.filter(user=request.user).order_by('-timestamp')[:10]
    return render(request, 'attendance/my_profile.html', {
        'profile': profile,
        'form': form,
        'recent_activity': recent_activity,
    })


@login_required
@user_passes_test(is_admin)
def user_profile_view(request, pk):
    """Admin view of another user's profile."""
    target_user = get_object_or_404(User, pk=pk)
    profile = target_user.profile
    form = UserProfileEditForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        user=target_user,
        admin_edit=True,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Profile for {target_user.get_full_name()} updated.')
        return redirect('user_list')
    activities = LoginActivity.objects.filter(user=target_user).order_by('-timestamp')[:20]
    return render(request, 'attendance/user_profile_view.html', {
        'target_user': target_user,
        'profile': profile,
        'form': form,
        'activities': activities,
    })


@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    if request.method == 'POST':
        name = target_user.get_full_name() or target_user.username
        target_user.delete()
        messages.success(request, f'User "{name}" deleted.')
        return redirect('user_list')
    return render(request, 'attendance/confirm_delete.html', {'object': target_user, 'type': 'User'})


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year

    total_citizens = Citizen.objects.filter(is_active=True).count()
    total_sessions = Session.objects.count()
    today_sessions = Session.objects.filter(date=today)
    upcoming_sessions = Session.objects.filter(
        date__gte=today, status='scheduled'
    ).order_by('date', 'start_time')[:5]

    recent_sessions = Session.objects.filter(status='completed').order_by('-date')[:5]

    monthly_attendance = []
    for month in range(1, 13):
        sessions_in_month = Session.objects.filter(date__year=current_year, date__month=month)
        present_count = AttendanceRecord.objects.filter(
            session__in=sessions_in_month, status__in=['present', 'late']
        ).count()
        monthly_attendance.append(present_count)

    session_type_stats = list(
        Session.objects.values('session_type').annotate(count=Count('id')).order_by('-count')
    )

    announcements = Announcement.objects.filter(is_published=True).order_by('-created_at')[:3]

    context = {
        'total_citizens': total_citizens,
        'total_sessions': total_sessions,
        'today_sessions': today_sessions,
        'upcoming_sessions': upcoming_sessions,
        'recent_sessions': recent_sessions,
        'monthly_attendance': json.dumps(monthly_attendance),
        'session_type_stats': json.dumps(session_type_stats),
        'announcements': announcements,
        'today': today,
    }
    return render(request, 'attendance/dashboard.html', context)


# ─── Session CRUD ──────────────────────────────────────────────────────────────

@login_required
def session_list(request):
    sessions = Session.objects.select_related('hall').all()
    session_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    q = request.GET.get('q', '')

    if session_type:
        sessions = sessions.filter(session_type=session_type)
    if status:
        sessions = sessions.filter(status=status)
    if q:
        sessions = sessions.filter(Q(title__icontains=q) | Q(presided_by__icontains=q))

    paginator = Paginator(sessions, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/session_list.html', {
        'page_obj': page_obj, 'session_type': session_type,
        'status': status, 'q': q,
    })


@login_required
def session_detail(request, pk):
    session = get_object_or_404(Session, pk=pk)
    attendance_records = AttendanceRecord.objects.filter(
        session=session
    ).select_related('citizen').order_by('citizen__last_name')
    present_count = attendance_records.filter(status='present').count()
    late_count = attendance_records.filter(status='late').count()
    absent_count = attendance_records.filter(status='absent').count()
    excused_count = attendance_records.filter(status='excused').count()
    return render(request, 'attendance/session_detail.html', {
        'session': session,
        'attendance_records': attendance_records,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'excused_count': excused_count,
    })


@login_required
@user_passes_test(is_staff_or_above)
def session_create(request):
    form = SessionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        session = form.save(commit=False)
        session.created_by = request.user
        session.save()
        messages.success(request, f'Session "{session.title}" created successfully.')
        return redirect('session_detail', pk=session.pk)
    return render(request, 'attendance/session_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_staff_or_above)
def session_edit(request, pk):
    session = get_object_or_404(Session, pk=pk)
    form = SessionForm(request.POST or None, instance=session)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Session "{session.title}" updated.')
        return redirect('session_detail', pk=session.pk)
    return render(request, 'attendance/session_form.html', {'form': form, 'session': session, 'action': 'Edit'})


@login_required
@user_passes_test(is_admin_or_secretary)
def session_delete(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.method == 'POST':
        session.delete()
        messages.success(request, 'Session deleted.')
        return redirect('session_list')
    return render(request, 'attendance/confirm_delete.html', {'object': session, 'type': 'Session'})


# ─── Citizen CRUD ──────────────────────────────────────────────────────────────

@login_required
def citizen_list(request):
    citizens = Citizen.objects.filter(is_active=True)
    category = request.GET.get('category', '')
    q = request.GET.get('q', '')
    if category:
        citizens = citizens.filter(category=category)
    if q:
        citizens = citizens.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(middle_name__icontains=q) | Q(contact_number__icontains=q)
        )
    paginator = Paginator(citizens, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/citizen_list.html', {
        'page_obj': page_obj, 'category': category, 'q': q,
        'categories': Citizen.CATEGORY_CHOICES,
    })


@login_required
def citizen_detail(request, pk):
    citizen = get_object_or_404(Citizen, pk=pk)
    records = AttendanceRecord.objects.filter(citizen=citizen).select_related('session').order_by('-session__date')[:20]
    return render(request, 'attendance/citizen_detail.html', {
        'citizen': citizen, 'records': records,
        'attendance_rate': citizen.attendance_rate(),
    })


@login_required
@user_passes_test(is_staff_or_above)
def citizen_create(request):
    form = CitizenForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        citizen = form.save()
        messages.success(request, f'{citizen.full_name} added to the registry.')
        return redirect('citizen_detail', pk=citizen.pk)
    return render(request, 'attendance/citizen_form.html', {'form': form, 'action': 'Register'})


@login_required
@user_passes_test(is_staff_or_above)
def citizen_edit(request, pk):
    citizen = get_object_or_404(Citizen, pk=pk)
    form = CitizenForm(request.POST or None, request.FILES or None, instance=citizen)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{citizen.full_name} updated.')
        return redirect('citizen_detail', pk=citizen.pk)
    return render(request, 'attendance/citizen_form.html', {
        'form': form, 'citizen': citizen, 'action': 'Edit'
    })


@login_required
@user_passes_test(is_admin_or_secretary)
def citizen_delete(request, pk):
    citizen = get_object_or_404(Citizen, pk=pk)
    if request.method == 'POST':
        citizen.is_active = False
        citizen.save()
        messages.success(request, f'{citizen.full_name} deactivated.')
        return redirect('citizen_list')
    return render(request, 'attendance/confirm_delete.html', {'object': citizen, 'type': 'Citizen'})


# ─── Attendance Marking ────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff_or_above)
def mark_attendance(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    citizens = Citizen.objects.filter(is_active=True).order_by('last_name', 'first_name')

    existing_records = {
        r.citizen_id: r for r in AttendanceRecord.objects.filter(session=session)
    }

    if request.method == 'POST':
        select_all_status = request.POST.get('select_all_status')
        citizen_ids = request.POST.getlist('citizen_ids')

        for citizen in citizens:
            status = request.POST.get(f'status_{citizen.pk}', 'absent')
            if select_all_status and str(citizen.pk) in citizen_ids:
                status = select_all_status

            record, created = AttendanceRecord.objects.get_or_create(
                session=session, citizen=citizen,
                defaults={'status': status, 'marked_by': request.user}
            )
            if not created:
                record.status = status
                record.marked_by = request.user
                record.save()

        messages.success(request, f'Attendance marked for {session.title}.')
        return redirect('session_detail', pk=session.pk)

    citizen_data = []
    for citizen in citizens:
        record = existing_records.get(citizen.pk)
        citizen_data.append({
            'citizen': citizen,
            'record': record,
            'already_marked': record is not None,
        })

    return render(request, 'attendance/mark_attendance.html', {
        'session': session,
        'citizen_data': citizen_data,
    })


@login_required
def attendance_list(request):
    """Global attendance list with filters."""
    records = AttendanceRecord.objects.select_related('citizen', 'session').order_by('-session__date', '-created_at')
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    session_pk = request.GET.get('session', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if q:
        records = records.filter(
            Q(citizen__first_name__icontains=q) | Q(citizen__last_name__icontains=q) |
            Q(session__title__icontains=q)
        )
    if status:
        records = records.filter(status=status)
    if session_pk:
        records = records.filter(session_id=session_pk)
    if date_from:
        records = records.filter(session__date__gte=date_from)
    if date_to:
        records = records.filter(session__date__lte=date_to)

    paginator = Paginator(records, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    sessions = Session.objects.order_by('-date')[:50]
    return render(request, 'attendance/attendance_list.html', {
        'page_obj': page_obj,
        'q': q, 'status': status, 'session_pk': session_pk,
        'date_from': date_from, 'date_to': date_to,
        'sessions': sessions,
        'status_choices': AttendanceRecord.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_staff_or_above)
@require_POST
def time_in(request, session_pk, citizen_pk):
    session = get_object_or_404(Session, pk=session_pk)
    citizen = get_object_or_404(Citizen, pk=citizen_pk)
    now = timezone.now()
    record, created = AttendanceRecord.objects.get_or_create(
        session=session, citizen=citizen,
        defaults={'status': 'present', 'time_in': now, 'marked_by': request.user}
    )
    if not created:
        record.time_in = now
        record.status = 'late' if record.is_late else 'present'
        record.save()
    return JsonResponse({
        'success': True,
        'time_in': now.strftime('%I:%M %p'),
        'status': record.status,
        'citizen_name': citizen.full_name
    })


@login_required
@user_passes_test(is_staff_or_above)
@require_POST
def time_out(request, session_pk, citizen_pk):
    session = get_object_or_404(Session, pk=session_pk)
    citizen = get_object_or_404(Citizen, pk=citizen_pk)
    now = timezone.now()
    try:
        record = AttendanceRecord.objects.get(session=session, citizen=citizen)
        record.time_out = now
        record.save()
        return JsonResponse({'success': True, 'time_out': now.strftime('%I:%M %p')})
    except AttendanceRecord.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No time-in record found.'})


# ─── Reports ──────────────────────────────────────────────────────────────────

@login_required
def reports(request):
    form = DateRangeFilterForm(request.GET or None)
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    session_type = request.GET.get('session_type', '')

    sessions = Session.objects.all()
    if date_from:
        sessions = sessions.filter(date__gte=date_from)
    if date_to:
        sessions = sessions.filter(date__lte=date_to)
    if session_type:
        sessions = sessions.filter(session_type=session_type)

    session_stats = []
    for s in sessions.order_by('-date'):
        records = AttendanceRecord.objects.filter(session=s)
        session_stats.append({
            'session': s,
            'present': records.filter(status='present').count(),
            'late': records.filter(status='late').count(),
            'absent': records.filter(status='absent').count(),
            'excused': records.filter(status='excused').count(),
            'total': records.count(),
        })

    top_attendees = Citizen.objects.filter(is_active=True).annotate(
        present_count=Count('attendance_records', filter=Q(attendance_records__status__in=['present', 'late']))
    ).order_by('-present_count')[:10]

    session_type_counts = []
    for st_code, st_label in Session.SESSION_TYPE_CHOICES:
        count = sessions.filter(session_type=st_code).count()
        session_type_counts.append({'label': st_label, 'count': count})

    return render(request, 'attendance/reports.html', {
        'form': form,
        'session_stats': session_stats,
        'top_attendees': top_attendees,
        'session_type_counts': json.dumps(session_type_counts),
    })


@login_required
def pdf_report(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    records = AttendanceRecord.objects.filter(session=session).select_related('citizen').order_by('citizen__last_name')
    return render(request, 'attendance/pdf_report.html', {
        'session': session, 'records': records,
        'present_count': records.filter(status='present').count(),
        'late_count': records.filter(status='late').count(),
        'absent_count': records.filter(status='absent').count(),
        'excused_count': records.filter(status='excused').count(),
        'generated_at': timezone.now(),
        'generated_by': request.user,
    })


@login_required
def export_csv(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    records = AttendanceRecord.objects.filter(session=session).select_related('citizen')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{session.pk}_{session.date}.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Full Name', 'Category', 'Status', 'Time In', 'Time Out', 'Remarks'])
    for i, r in enumerate(records.order_by('citizen__last_name'), 1):
        writer.writerow([
            i, r.citizen.full_name, r.citizen.get_category_display(),
            r.get_status_display(),
            r.time_in.strftime('%I:%M %p') if r.time_in else '',
            r.time_out.strftime('%I:%M %p') if r.time_out else '',
            r.remarks,
        ])
    return response


# ─── Calendar ─────────────────────────────────────────────────────────────────

@login_required
def calendar_view(request):
    return render(request, 'attendance/calendar.html')


# ─── Halls CRUD ───────────────────────────────────────────────────────────────

@login_required
def hall_list(request):
    halls = Hall.objects.all()
    return render(request, 'attendance/hall_list.html', {'halls': halls})


@login_required
@user_passes_test(is_admin_or_secretary)
def hall_create(request):
    form = HallForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Hall/Venue added.')
        return redirect('hall_list')
    return render(request, 'attendance/hall_form.html', {'form': form, 'action': 'Add'})


@login_required
@user_passes_test(is_admin_or_secretary)
def hall_edit(request, pk):
    hall = get_object_or_404(Hall, pk=pk)
    form = HallForm(request.POST or None, instance=hall)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Hall updated.')
        return redirect('hall_list')
    return render(request, 'attendance/hall_form.html', {'form': form, 'hall': hall, 'action': 'Edit'})


@login_required
@user_passes_test(is_admin)
def hall_delete(request, pk):
    hall = get_object_or_404(Hall, pk=pk)
    if request.method == 'POST':
        hall.delete()
        messages.success(request, 'Hall deleted.')
        return redirect('hall_list')
    return render(request, 'attendance/confirm_delete.html', {'object': hall, 'type': 'Hall'})


# ─── Announcements ────────────────────────────────────────────────────────────

@login_required
def announcement_list(request):
    announcements = Announcement.objects.all()
    return render(request, 'attendance/announcement_list.html', {'announcements': announcements})


@login_required
@user_passes_test(is_admin_or_secretary)
def announcement_create(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ann = form.save(commit=False)
        ann.published_by = request.user
        ann.save()
        messages.success(request, 'Announcement posted.')
        return redirect('announcement_list')
    return render(request, 'attendance/announcement_form.html', {'form': form, 'action': 'Post'})


@login_required
@user_passes_test(is_admin_or_secretary)
def announcement_edit(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(request.POST or None, instance=ann)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Announcement updated.')
        return redirect('announcement_list')
    return render(request, 'attendance/announcement_form.html', {'form': form, 'action': 'Edit'})


@login_required
@user_passes_test(is_admin_or_secretary)
def announcement_delete(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, 'Announcement deleted.')
        return redirect('announcement_list')
    return render(request, 'attendance/confirm_delete.html', {'object': ann, 'type': 'Announcement'})


# ─── User Management ──────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    q = request.GET.get('q', '')
    role = request.GET.get('role', '')
    if q:
        users = users.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q))
    if role:
        users = users.filter(profile__role=role)
    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/user_list.html', {
        'page_obj': page_obj, 'q': q, 'role': role,
        'role_choices': UserProfile.ROLE_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def login_activity_log(request):
    """Admin view: see all login/logout/register events."""
    activities = LoginActivity.objects.select_related('user').all()
    action_filter = request.GET.get('action', '')
    q = request.GET.get('q', '')
    if action_filter:
        activities = activities.filter(action=action_filter)
    if q:
        activities = activities.filter(
            Q(username_attempted__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(ip_address__icontains=q)
        )
    paginator = Paginator(activities, 30)
    page_obj = paginator.get_page(request.GET.get('page'))
    total_logins = LoginActivity.objects.filter(action='login').count()
    total_failed = LoginActivity.objects.filter(action='failed').count()
    total_registered = LoginActivity.objects.filter(action='register').count()
    return render(request, 'attendance/login_activity.html', {
        'page_obj': page_obj,
        'action_filter': action_filter,
        'q': q,
        'total_logins': total_logins,
        'total_failed': total_failed,
        'total_registered': total_registered,
        'action_choices': LoginActivity.ACTION_CHOICES,
    })


# ─── REST API Endpoints ───────────────────────────────────────────────────────

@login_required
@require_GET
def api_sessions(request):
    sessions = Session.objects.all()
    data = []
    for s in sessions:
        status_color = {
            'scheduled': '#3498db', 'ongoing': '#2ecc71',
            'completed': '#95a5a6', 'cancelled': '#e74c3c', 'postponed': '#f39c12'
        }.get(s.status, '#3498db')
        data.append({
            'id': s.pk,
            'title': s.title,
            'start': f"{s.date}T{s.start_time}",
            'end': f"{s.date}T{s.end_time}" if s.end_time else None,
            'color': status_color,
            'status': s.status,
            'session_type': s.get_session_type_display(),
            'url': f'/sessions/{s.pk}/',
        })
    return JsonResponse(data, safe=False)


@login_required
@require_GET
def api_dashboard_stats(request):
    today = datetime.date.today()
    total_citizens = Citizen.objects.filter(is_active=True).count()
    total_sessions = Session.objects.count()
    today_sessions = Session.objects.filter(date=today).count()
    total_records = AttendanceRecord.objects.filter(status__in=['present', 'late']).count()
    online_today = LoginActivity.objects.filter(
        action='login',
        timestamp__date=today
    ).values('user').distinct().count()
    return JsonResponse({
        'total_citizens': total_citizens,
        'total_sessions': total_sessions,
        'today_sessions': today_sessions,
        'total_present_records': total_records,
        'users_online_today': online_today,
    })


@login_required
@require_GET
def api_citizen_search(request):
    q = request.GET.get('q', '')
    citizens = Citizen.objects.filter(is_active=True)
    if q:
        citizens = citizens.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )[:20]
    data = [{'id': c.pk, 'name': c.full_name, 'category': c.get_category_display()} for c in citizens]
    return JsonResponse(data, safe=False)


@login_required
def api_attendance_record(request, session_pk, citizen_pk):
    session = get_object_or_404(Session, pk=session_pk)
    citizen = get_object_or_404(Citizen, pk=citizen_pk)
    if request.method == 'GET':
        try:
            record = AttendanceRecord.objects.get(session=session, citizen=citizen)
            return JsonResponse({
                'status': record.status,
                'time_in': record.time_in.strftime('%I:%M %p') if record.time_in else None,
                'time_out': record.time_out.strftime('%I:%M %p') if record.time_out else None,
                'remarks': record.remarks,
            })
        except AttendanceRecord.DoesNotExist:
            return JsonResponse({'status': None})
    elif request.method == 'POST':
        if not is_staff_or_above(request.user):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        data = json.loads(request.body)
        record, _ = AttendanceRecord.objects.get_or_create(
            session=session, citizen=citizen,
            defaults={'marked_by': request.user}
        )
        record.status = data.get('status', record.status)
        record.remarks = data.get('remarks', record.remarks)
        record.marked_by = request.user
        record.save()
        return JsonResponse({'success': True, 'status': record.status})


@login_required
@require_GET
def api_session_attendance_summary(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    records = AttendanceRecord.objects.filter(session=session)
    return JsonResponse({
        'session_id': session_pk,
        'session_title': session.title,
        'present': records.filter(status='present').count(),
        'late': records.filter(status='late').count(),
        'absent': records.filter(status='absent').count(),
        'excused': records.filter(status='excused').count(),
        'total': records.count(),
    })


@login_required
@require_GET
def api_login_activities(request):
    """API: recent login activity for admin dashboard widget."""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    activities = LoginActivity.objects.select_related('user').order_by('-timestamp')[:20]
    data = [{
        'id': a.pk,
        'user': a.user.get_full_name() if a.user else a.username_attempted,
        'username': a.username_attempted,
        'action': a.action,
        'action_label': a.get_action_display(),
        'ip_address': a.ip_address,
        'timestamp': a.timestamp.strftime('%b %d %Y %I:%M %p'),
    } for a in activities]
    return JsonResponse(data, safe=False)


@login_required
@require_GET
def api_users(request):
    """API: list users (admin only)."""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    users = User.objects.select_related('profile').all()
    data = [{
        'id': u.pk,
        'username': u.username,
        'full_name': u.get_full_name(),
        'email': u.email,
        'role': u.profile.role if hasattr(u, 'profile') else '',
        'role_label': u.profile.get_role_display() if hasattr(u, 'profile') else '',
        'date_joined': u.date_joined.strftime('%Y-%m-%d'),
        'is_active': u.is_active,
    } for u in users]
    return JsonResponse(data, safe=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PUNONG BARANGAY (CAPTAIN) MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def is_official_level(user):
    return hasattr(user, 'profile') and user.profile.role in [
        'punong_barangay', 'admin', 'secretary', 'treasurer', 'kagawad', 'sb_chairperson'
    ]

@login_required
@user_passes_test(is_captain_or_admin)
def captain_dashboard(request):
    today = datetime.date.today()
    pending_approvals = ApprovalRequest.objects.filter(status='pending').count()
    active_projects = BarangayProject.objects.filter(status__in=['approved', 'ongoing']).count()
    open_complaints = Complaint.objects.filter(status__in=['filed', 'under_investigation', 'mediation']).count()
    pending_ordinances = Ordinance.objects.filter(status='pending_approval').count()
    recent_incidents = IncidentReport.objects.filter(is_resolved=False).order_by('-incident_date')[:5]
    upcoming_sessions = Session.objects.filter(date__gte=today, status='scheduled').order_by('date')[:5]
    total_residents = Citizen.objects.filter(is_active=True).count()
    monthly_revenue = FinancialRecord.objects.filter(
        type='revenue', transaction_date__month=today.month, transaction_date__year=today.year
    ).values_list('amount', flat=True)
    monthly_expense = FinancialRecord.objects.filter(
        type='expense', transaction_date__month=today.month, transaction_date__year=today.year
    ).values_list('amount', flat=True)
    rev_total = sum(monthly_revenue)
    exp_total = sum(monthly_expense)
    return render(request, 'attendance/captain_dashboard.html', {
        'pending_approvals': pending_approvals,
        'active_projects': active_projects,
        'open_complaints': open_complaints,
        'pending_ordinances': pending_ordinances,
        'recent_incidents': recent_incidents,
        'upcoming_sessions': upcoming_sessions,
        'total_residents': total_residents,
        'monthly_revenue': rev_total,
        'monthly_expense': exp_total,
        'monthly_balance': rev_total - exp_total,
        'today': today,
    })


@login_required
@user_passes_test(is_captain_or_admin)
def approval_list(request):
    qs = ApprovalRequest.objects.select_related('requested_by').all()
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if type_filter:
        qs = qs.filter(type=type_filter)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/approval_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'status_choices': ApprovalRequest.STATUS_CHOICES,
        'type_choices': ApprovalRequest.TYPE_CHOICES,
    })


@login_required
def approval_create(request):
    """Any staff member can file an approval request."""
    if request.method == 'POST':
        req_type = request.POST.get('type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        amount = request.POST.get('amount') or None
        ApprovalRequest.objects.create(
            type=req_type, title=title, description=description,
            amount=amount, requested_by=request.user
        )
        messages.success(request, 'Approval request submitted successfully.')
        return redirect('approval_list')
    return render(request, 'attendance/approval_form.html', {
        'type_choices': ApprovalRequest.TYPE_CHOICES,
        'action': 'Submit',
    })


@login_required
@user_passes_test(is_captain_or_admin)
def approval_action(request, pk):
    """Captain approves or rejects a request."""
    req = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('review_notes', '')
        if action in ['approved', 'rejected', 'returned']:
            req.status = action
            req.reviewed_by = request.user
            req.review_notes = notes
            req.reviewed_at = timezone.now()
            req.save()
            AuditLog.objects.create(
                user=request.user, action='approve' if action == 'approved' else 'reject',
                model_name='ApprovalRequest', object_id=str(req.pk),
                object_repr=str(req), ip_address=get_client_ip(request)
            )
            messages.success(request, f'Request marked as {action}.')
        return redirect('approval_list')
    return render(request, 'attendance/approval_action.html', {'req': req})


# ─── Ordinance & Resolution Management ───────────────────────────────────────

@login_required
@user_passes_test(is_official_level)
def ordinance_list(request):
    qs = Ordinance.objects.select_related('drafted_by', 'approved_by').all()
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    if type_filter:
        qs = qs.filter(type=type_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/ordinance_list.html', {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'type_choices': Ordinance.TYPE_CHOICES,
        'status_choices': Ordinance.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_official_level)
def ordinance_create(request):
    if request.method == 'POST':
        Ordinance.objects.create(
            number=request.POST.get('number'),
            type=request.POST.get('type'),
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            committee=request.POST.get('committee', ''),
            status='draft',
            drafted_by=request.user,
        )
        messages.success(request, 'Ordinance/Resolution drafted successfully.')
        return redirect('ordinance_list')
    return render(request, 'attendance/ordinance_form.html', {
        'type_choices': Ordinance.TYPE_CHOICES, 'action': 'Draft',
    })


@login_required
@user_passes_test(is_official_level)
def ordinance_detail(request, pk):
    ord_obj = get_object_or_404(Ordinance, pk=pk)
    return render(request, 'attendance/ordinance_detail.html', {'ord_obj': ord_obj})


@login_required
@user_passes_test(is_captain_or_admin)
def ordinance_approve(request, pk):
    ord_obj = get_object_or_404(Ordinance, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            ord_obj.status = 'approved'
            ord_obj.approved_by = request.user
            ord_obj.approval_date = datetime.date.today()
            ord_obj.approval_notes = request.POST.get('notes', '')
        elif action == 'enact':
            ord_obj.status = 'enacted'
            ord_obj.date_enacted = datetime.date.today()
        elif action == 'reject':
            ord_obj.status = 'rejected'
            ord_obj.approval_notes = request.POST.get('notes', '')
        ord_obj.save()
        messages.success(request, f'Ordinance status updated to {ord_obj.get_status_display()}.')
        return redirect('ordinance_list')
    return render(request, 'attendance/ordinance_approve.html', {'ord_obj': ord_obj})


# ─── Project & Program Monitoring ────────────────────────────────────────────

@login_required
@user_passes_test(is_official_level)
def project_list(request):
    qs = BarangayProject.objects.select_related('created_by', 'approved_by').all()
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if category_filter:
        qs = qs.filter(category=category_filter)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/project_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'status_choices': BarangayProject.STATUS_CHOICES,
        'category_choices': BarangayProject.CATEGORY_CHOICES,
    })


@login_required
@user_passes_test(is_official_level)
def project_create(request):
    if request.method == 'POST':
        BarangayProject.objects.create(
            title=request.POST.get('title'),
            category=request.POST.get('category'),
            description=request.POST.get('description'),
            location=request.POST.get('location', ''),
            budget_allocated=request.POST.get('budget_allocated') or 0,
            start_date=request.POST.get('start_date') or None,
            end_date=request.POST.get('end_date') or None,
            committee_in_charge=request.POST.get('committee_in_charge', ''),
            status='proposed',
            created_by=request.user,
        )
        messages.success(request, 'Project proposal submitted.')
        return redirect('project_list')
    return render(request, 'attendance/project_form.html', {
        'category_choices': BarangayProject.CATEGORY_CHOICES, 'action': 'Propose',
    })


@login_required
@user_passes_test(is_official_level)
def project_detail(request, pk):
    project = get_object_or_404(BarangayProject, pk=pk)
    return render(request, 'attendance/project_detail.html', {'project': project})


@login_required
@user_passes_test(is_captain_or_admin)
def project_approve(request, pk):
    project = get_object_or_404(BarangayProject, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['approved', 'ongoing', 'completed', 'cancelled', 'suspended']:
            project.status = new_status
            project.approved_by = request.user
            if request.POST.get('progress_percent'):
                project.progress_percent = int(request.POST.get('progress_percent'))
            project.save()
            messages.success(request, f'Project status updated to {project.get_status_display()}.')
        return redirect('project_list')
    return render(request, 'attendance/project_approve.html', {
        'project': project,
        'status_choices': BarangayProject.STATUS_CHOICES,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TREASURER MODULE
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(is_treasurer)
def treasurer_dashboard(request):
    today = datetime.date.today()
    month_revenues = FinancialRecord.objects.filter(
        type='revenue', transaction_date__month=today.month, transaction_date__year=today.year
    )
    month_expenses = FinancialRecord.objects.filter(
        type='expense', transaction_date__month=today.month, transaction_date__year=today.year
    )
    pending_disbursements = FinancialRecord.objects.filter(type='expense', status='pending').count()
    rev_total = sum(r.amount for r in month_revenues)
    exp_total = sum(r.amount for r in month_expenses)
    recent_records = FinancialRecord.objects.order_by('-created_at')[:10]
    budget_allocations = BudgetAllocation.objects.filter(fiscal_year=today.year)
    return render(request, 'attendance/treasurer_dashboard.html', {
        'rev_total': rev_total,
        'exp_total': exp_total,
        'balance': rev_total - exp_total,
        'pending_disbursements': pending_disbursements,
        'recent_records': recent_records,
        'budget_allocations': budget_allocations,
        'today': today,
    })


@login_required
@user_passes_test(is_treasurer)
def financial_list(request):
    qs = FinancialRecord.objects.select_related('recorded_by', 'approved_by').all()
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    fund_filter = request.GET.get('fund', '')
    if type_filter:
        qs = qs.filter(type=type_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if fund_filter:
        qs = qs.filter(fund=fund_filter)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/financial_list.html', {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'fund_filter': fund_filter,
        'type_choices': FinancialRecord.TYPE_CHOICES,
        'status_choices': FinancialRecord.STATUS_CHOICES,
        'fund_choices': FinancialRecord.FUND_CHOICES,
    })


@login_required
@user_passes_test(is_treasurer)
def financial_create(request):
    if request.method == 'POST':
        record = FinancialRecord.objects.create(
            type=request.POST.get('type'),
            fund=request.POST.get('fund', 'general'),
            description=request.POST.get('description'),
            amount=request.POST.get('amount'),
            or_number=request.POST.get('or_number', ''),
            payee=request.POST.get('payee', ''),
            reference_number=request.POST.get('reference_number', ''),
            transaction_date=request.POST.get('transaction_date') or datetime.date.today(),
            notes=request.POST.get('notes', ''),
            status='pending',
            recorded_by=request.user,
        )
        messages.success(request, 'Financial record created.')
        return redirect('financial_list')
    return render(request, 'attendance/financial_form.html', {
        'type_choices': FinancialRecord.TYPE_CHOICES,
        'fund_choices': FinancialRecord.FUND_CHOICES,
        'action': 'Record',
        'today': datetime.date.today(),
    })


@login_required
@user_passes_test(is_captain_or_admin)
def financial_approve(request, pk):
    record = get_object_or_404(FinancialRecord, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            record.status = 'approved'
            record.approved_by = request.user
            record.approved_at = timezone.now()
        elif action == 'disburse':
            record.status = 'disbursed'
        elif action == 'reject':
            record.status = 'rejected'
        record.save()
        messages.success(request, f'Financial record {action}d.')
        return redirect('financial_list')
    return render(request, 'attendance/financial_approve.html', {'record': record})


@login_required
@user_passes_test(is_treasurer)
def budget_list(request):
    today = datetime.date.today()
    year_filter = int(request.GET.get('year', today.year))
    allocations = BudgetAllocation.objects.filter(fiscal_year=year_filter)
    return render(request, 'attendance/budget_list.html', {
        'allocations': allocations,
        'year_filter': year_filter,
        'years': range(today.year - 3, today.year + 2),
    })


@login_required
@user_passes_test(is_treasurer)
def budget_create(request):
    if request.method == 'POST':
        BudgetAllocation.objects.create(
            fiscal_year=request.POST.get('fiscal_year'),
            fund=request.POST.get('fund'),
            description=request.POST.get('description'),
            allocated_amount=request.POST.get('allocated_amount'),
            created_by=request.user,
        )
        messages.success(request, 'Budget allocation added.')
        return redirect('budget_list')
    return render(request, 'attendance/budget_form.html', {
        'action': 'Add', 'today': datetime.date.today(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLAINT & CASE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(is_official_level)
def complaint_list(request):
    qs = Complaint.objects.select_related('assigned_to').all()
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if type_filter:
        qs = qs.filter(type=type_filter)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/complaint_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'status_choices': Complaint.STATUS_CHOICES,
        'type_choices': Complaint.TYPE_CHOICES,
    })


@login_required
@user_passes_test(is_official_level)
def complaint_create(request):
    if request.method == 'POST':
        import random
        case_number = f"CASE-{datetime.date.today().year}-{random.randint(1000, 9999)}"
        Complaint.objects.create(
            case_number=case_number,
            type=request.POST.get('type', 'other'),
            complainant_name=request.POST.get('complainant_name'),
            respondent_name=request.POST.get('respondent_name'),
            description=request.POST.get('description'),
            status='filed',
        )
        messages.success(request, f'Case {case_number} filed successfully.')
        return redirect('complaint_list')
    return render(request, 'attendance/complaint_form.html', {
        'type_choices': Complaint.TYPE_CHOICES, 'action': 'File',
    })


@login_required
@user_passes_test(is_official_level)
def complaint_detail(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    officials = User.objects.filter(profile__role__in=['punong_barangay', 'admin', 'kagawad', 'sb_chairperson'])
    if request.method == 'POST':
        complaint.status = request.POST.get('status', complaint.status)
        complaint.resolution_notes = request.POST.get('resolution_notes', complaint.resolution_notes)
        assigned_id = request.POST.get('assigned_to')
        if assigned_id:
            complaint.assigned_to_id = assigned_id
        if complaint.status == 'resolved':
            complaint.resolved_date = datetime.date.today()
        complaint.save()
        messages.success(request, 'Case updated.')
        return redirect('complaint_list')
    return render(request, 'attendance/complaint_detail.html', {
        'complaint': complaint,
        'status_choices': Complaint.STATUS_CHOICES,
        'officials': officials,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TANOD MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def is_tanod(user):
    return hasattr(user, 'profile') and user.profile.role in ['tanod', 'admin', 'punong_barangay']

def is_security_level(user):
    return hasattr(user, 'profile') and user.profile.role in [
        'tanod', 'punong_barangay', 'admin', 'secretary', 'kagawad', 'sb_chairperson'
    ]


@login_required
@user_passes_test(is_security_level)
def tanod_dashboard(request):
    today = datetime.date.today()
    my_patrols = PatrolSchedule.objects.filter(
        date=today
    ).filter(
        tanod_members=request.user
    ) if request.user.profile.role == 'tanod' else PatrolSchedule.objects.filter(date=today)
    
    recent_incidents = IncidentReport.objects.filter(is_resolved=False).order_by('-incident_date')[:8]
    open_incidents_count = IncidentReport.objects.filter(is_resolved=False).count()
    today_patrols = PatrolSchedule.objects.filter(date=today).count()
    return render(request, 'attendance/tanod_dashboard.html', {
        'my_patrols': my_patrols,
        'recent_incidents': recent_incidents,
        'open_incidents_count': open_incidents_count,
        'today_patrols': today_patrols,
        'today': today,
    })


@login_required
@user_passes_test(is_security_level)
def incident_list(request):
    qs = IncidentReport.objects.select_related('reported_by').all()
    type_filter = request.GET.get('type', '')
    resolved_filter = request.GET.get('resolved', '')
    if type_filter:
        qs = qs.filter(type=type_filter)
    if resolved_filter == '0':
        qs = qs.filter(is_resolved=False)
    elif resolved_filter == '1':
        qs = qs.filter(is_resolved=True)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/incident_list.html', {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'type_choices': IncidentReport.TYPE_CHOICES,
    })


@login_required
@user_passes_test(is_security_level)
def incident_create(request):
    if request.method == 'POST':
        import random
        report_number = f"INC-{datetime.date.today().strftime('%Y%m%d')}-{random.randint(100, 999)}"
        IncidentReport.objects.create(
            report_number=report_number,
            type=request.POST.get('type'),
            severity=request.POST.get('severity', 'moderate'),
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            location=request.POST.get('location'),
            incident_date=request.POST.get('incident_date') or timezone.now(),
            reported_by=request.user,
        )
        messages.success(request, f'Incident {report_number} reported.')
        return redirect('incident_list')
    return render(request, 'attendance/incident_form.html', {
        'type_choices': IncidentReport.TYPE_CHOICES,
        'severity_choices': IncidentReport.SEVERITY_CHOICES,
        'action': 'Report',
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M'),
    })


@login_required
@user_passes_test(is_security_level)
def incident_detail(request, pk):
    incident = get_object_or_404(IncidentReport, pk=pk)
    if request.method == 'POST':
        incident.resolution = request.POST.get('resolution', '')
        incident.is_resolved = True
        incident.save()
        messages.success(request, 'Incident marked as resolved.')
        return redirect('incident_list')
    return render(request, 'attendance/incident_detail.html', {'incident': incident})


@login_required
@user_passes_test(is_security_level)
def patrol_list(request):
    qs = PatrolSchedule.objects.all()
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/patrol_list.html', {'page_obj': page_obj})


@login_required
@user_passes_test(lambda u: hasattr(u, 'profile') and u.profile.role in ['punong_barangay', 'admin', 'secretary'])
def patrol_create(request):
    tanods = User.objects.filter(profile__role='tanod')
    if request.method == 'POST':
        schedule = PatrolSchedule.objects.create(
            date=request.POST.get('date'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            area=request.POST.get('area'),
            notes=request.POST.get('notes', ''),
            status='scheduled',
            created_by=request.user,
        )
        member_ids = request.POST.getlist('tanod_members')
        if member_ids:
            schedule.tanod_members.set(member_ids)
        messages.success(request, 'Patrol schedule created.')
        return redirect('patrol_list')
    return render(request, 'attendance/patrol_form.html', {
        'tanods': tanods, 'action': 'Create',
        'today': datetime.date.today(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# BARANGAY HEALTH WORKER (BHW) MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def is_bhw_level(user):
    return hasattr(user, 'profile') and user.profile.role in ['bhw', 'punong_barangay', 'admin', 'secretary']


@login_required
@user_passes_test(is_bhw_level)
def bhw_dashboard(request):
    today = datetime.date.today()
    total_health_records = HealthRecord.objects.count()
    critical_cases = HealthRecord.objects.filter(condition='critical').count()
    today_visits = HouseholdVisit.objects.filter(visit_date=today).count()
    upcoming_immunizations = ImmunizationRecord.objects.filter(
        next_dose_date__gte=today,
        next_dose_date__lte=today + datetime.timedelta(days=30)
    ).count()
    recent_visits = HouseholdVisit.objects.filter(
        visitor=request.user
    ).order_by('-visit_date')[:5] if request.user.profile.role == 'bhw' else \
        HouseholdVisit.objects.order_by('-visit_date')[:5]
    return render(request, 'attendance/bhw_dashboard.html', {
        'total_health_records': total_health_records,
        'critical_cases': critical_cases,
        'today_visits': today_visits,
        'upcoming_immunizations': upcoming_immunizations,
        'recent_visits': recent_visits,
        'today': today,
    })


@login_required
@user_passes_test(is_bhw_level)
def health_record_list(request):
    qs = HealthRecord.objects.select_related('citizen', 'bhw').all()
    condition_filter = request.GET.get('condition', '')
    q = request.GET.get('q', '')
    if condition_filter:
        qs = qs.filter(condition=condition_filter)
    if q:
        qs = qs.filter(
            Q(citizen__first_name__icontains=q) | Q(citizen__last_name__icontains=q)
        )
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/health_record_list.html', {
        'page_obj': page_obj,
        'condition_filter': condition_filter,
        'q': q,
        'condition_choices': HealthRecord.CONDITION_CHOICES,
    })


@login_required
@user_passes_test(is_bhw_level)
def health_record_create(request):
    citizens = Citizen.objects.filter(is_active=True).order_by('last_name')
    if request.method == 'POST':
        citizen_id = request.POST.get('citizen')
        existing = HealthRecord.objects.filter(citizen_id=citizen_id).first()
        if existing:
            messages.warning(request, 'Health record for this citizen already exists. Redirecting to edit.')
            return redirect('health_record_list')
        HealthRecord.objects.create(
            citizen_id=citizen_id,
            bhw=request.user,
            condition=request.POST.get('condition', 'healthy'),
            blood_type=request.POST.get('blood_type', ''),
            allergies=request.POST.get('allergies', ''),
            current_medications=request.POST.get('current_medications', ''),
            medical_notes=request.POST.get('medical_notes', ''),
            last_checkup=request.POST.get('last_checkup') or None,
            next_checkup=request.POST.get('next_checkup') or None,
        )
        messages.success(request, 'Health record created.')
        return redirect('health_record_list')
    return render(request, 'attendance/health_record_form.html', {
        'citizens': citizens,
        'condition_choices': HealthRecord.CONDITION_CHOICES,
        'action': 'Create',
    })


@login_required
@user_passes_test(is_bhw_level)
def immunization_list(request):
    qs = ImmunizationRecord.objects.select_related('citizen', 'administered_by').all()
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(citizen__first_name__icontains=q) | Q(citizen__last_name__icontains=q) |
            Q(vaccine_name__icontains=q)
        )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/immunization_list.html', {'page_obj': page_obj, 'q': q})


@login_required
@user_passes_test(is_bhw_level)
def immunization_create(request):
    citizens = Citizen.objects.filter(is_active=True).order_by('last_name')
    if request.method == 'POST':
        ImmunizationRecord.objects.create(
            citizen_id=request.POST.get('citizen'),
            vaccine_name=request.POST.get('vaccine_name'),
            dose=request.POST.get('dose', ''),
            date_given=request.POST.get('date_given'),
            next_dose_date=request.POST.get('next_dose_date') or None,
            administered_by=request.user,
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Immunization record added.')
        return redirect('immunization_list')
    return render(request, 'attendance/immunization_form.html', {
        'citizens': citizens, 'action': 'Record',
        'today': datetime.date.today(),
    })


@login_required
@user_passes_test(is_bhw_level)
def household_visit_list(request):
    if request.user.profile.role == 'bhw':
        qs = HouseholdVisit.objects.filter(visitor=request.user)
    else:
        qs = HouseholdVisit.objects.all()
    qs = qs.select_related('citizen', 'visitor')
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/household_visit_list.html', {'page_obj': page_obj})


@login_required
@user_passes_test(is_bhw_level)
def household_visit_create(request):
    citizens = Citizen.objects.filter(is_active=True).order_by('last_name')
    if request.method == 'POST':
        HouseholdVisit.objects.create(
            citizen_id=request.POST.get('citizen'),
            visitor=request.user,
            purpose=request.POST.get('purpose'),
            visit_date=request.POST.get('visit_date'),
            findings=request.POST.get('findings', ''),
            recommendations=request.POST.get('recommendations', ''),
            next_visit_date=request.POST.get('next_visit_date') or None,
        )
        messages.success(request, 'Household visit recorded.')
        return redirect('household_visit_list')
    return render(request, 'attendance/household_visit_form.html', {
        'citizens': citizens,
        'purpose_choices': HouseholdVisit.PURPOSE_CHOICES,
        'action': 'Record',
        'today': datetime.date.today(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# BARANGAY NUTRITION SCHOLAR (BNS) MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def is_bns_level(user):
    return hasattr(user, 'profile') and user.profile.role in ['bns', 'bhw', 'punong_barangay', 'admin']


@login_required
@user_passes_test(is_bns_level)
def bns_dashboard(request):
    today = datetime.date.today()
    total_monitored = NutritionRecord.objects.values('citizen').distinct().count()
    malnourished = NutritionRecord.objects.filter(
        nutritional_status__in=['underweight', 'severely_underweight']
    ).values('citizen').distinct().count()
    feeding_programs = FeedingProgram.objects.filter(
        status__in=['planned', 'ongoing']
    ).count()
    recent_records = NutritionRecord.objects.select_related('citizen').order_by('-monitoring_date')[:8]
    return render(request, 'attendance/bns_dashboard.html', {
        'total_monitored': total_monitored,
        'malnourished': malnourished,
        'feeding_programs': feeding_programs,
        'recent_records': recent_records,
        'today': today,
    })


@login_required
@user_passes_test(is_bns_level)
def nutrition_record_list(request):
    qs = NutritionRecord.objects.select_related('citizen', 'bns').all()
    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    if status_filter:
        qs = qs.filter(nutritional_status=status_filter)
    if q:
        qs = qs.filter(
            Q(citizen__first_name__icontains=q) | Q(citizen__last_name__icontains=q)
        )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/nutrition_record_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'status_choices': NutritionRecord.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_bns_level)
def nutrition_record_create(request):
    citizens = Citizen.objects.filter(is_active=True).order_by('last_name')
    if request.method == 'POST':
        NutritionRecord.objects.create(
            citizen_id=request.POST.get('citizen'),
            bns=request.user,
            weight_kg=request.POST.get('weight_kg') or None,
            height_cm=request.POST.get('height_cm') or None,
            muac_cm=request.POST.get('muac_cm') or None,
            nutritional_status=request.POST.get('nutritional_status', 'normal'),
            is_enrolled_feeding=request.POST.get('is_enrolled_feeding') == 'on',
            monitoring_date=request.POST.get('monitoring_date'),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Nutrition record saved.')
        return redirect('nutrition_record_list')
    return render(request, 'attendance/nutrition_record_form.html', {
        'citizens': citizens,
        'status_choices': NutritionRecord.STATUS_CHOICES,
        'action': 'Record',
        'today': datetime.date.today(),
    })


@login_required
@user_passes_test(is_bns_level)
def feeding_program_list(request):
    qs = FeedingProgram.objects.select_related('conducted_by').all()
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/feeding_program_list.html', {'page_obj': page_obj})


@login_required
@user_passes_test(is_bns_level)
def feeding_program_create(request):
    if request.method == 'POST':
        FeedingProgram.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            date=request.POST.get('date'),
            location=request.POST.get('location'),
            beneficiary_count=request.POST.get('beneficiary_count') or 0,
            status=request.POST.get('status', 'planned'),
            conducted_by=request.user,
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Feeding program added.')
        return redirect('feeding_program_list')
    return render(request, 'attendance/feeding_program_form.html', {
        'status_choices': FeedingProgram.STATUS_CHOICES,
        'action': 'Add',
        'today': datetime.date.today(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY / ADMIN STAFF MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def is_utility_level(user):
    return hasattr(user, 'profile') and user.profile.role in [
        'utility', 'staff', 'punong_barangay', 'admin', 'secretary'
    ]


@login_required
@user_passes_test(is_utility_level)
def utility_dashboard(request):
    today = datetime.date.today()
    my_tasks = MaintenanceTask.objects.filter(
        assigned_to=request.user, status__in=['pending', 'in_progress']
    )
    low_stock = [item for item in InventoryItem.objects.all() if item.is_low_stock]
    today_log = DailyActivityLog.objects.filter(user=request.user, date=today).first()
    return render(request, 'attendance/utility_dashboard.html', {
        'my_tasks': my_tasks,
        'low_stock': low_stock,
        'today_log': today_log,
        'today': today,
    })


@login_required
@user_passes_test(is_utility_level)
def task_list(request):
    if request.user.profile.role in ['utility', 'staff']:
        qs = MaintenanceTask.objects.filter(assigned_to=request.user)
    else:
        qs = MaintenanceTask.objects.all()
    qs = qs.select_related('assigned_to', 'assigned_by')
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/task_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': MaintenanceTask.STATUS_CHOICES,
    })


@login_required
@user_passes_test(lambda u: hasattr(u, 'profile') and u.profile.role in ['punong_barangay', 'admin', 'secretary'])
def task_create(request):
    staff_users = User.objects.filter(profile__role__in=['utility', 'staff', 'tanod'])
    if request.method == 'POST':
        MaintenanceTask.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            location=request.POST.get('location', ''),
            priority=request.POST.get('priority', 'normal'),
            assigned_to_id=request.POST.get('assigned_to') or None,
            due_date=request.POST.get('due_date') or None,
            status='pending',
            assigned_by=request.user,
        )
        messages.success(request, 'Task assigned.')
        return redirect('task_list')
    return render(request, 'attendance/task_form.html', {
        'staff_users': staff_users,
        'priority_choices': MaintenanceTask.PRIORITY_CHOICES,
        'action': 'Assign',
        'today': datetime.date.today(),
    })


@login_required
@user_passes_test(is_utility_level)
def task_update_status(request, pk):
    task = get_object_or_404(MaintenanceTask, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        task.status = new_status
        task.completion_notes = request.POST.get('completion_notes', '')
        if new_status == 'completed':
            task.completed_at = timezone.now()
        task.save()
        messages.success(request, f'Task marked as {task.get_status_display()}.')
    return redirect('task_list')


@login_required
@user_passes_test(is_utility_level)
def inventory_list(request):
    qs = InventoryItem.objects.all()
    category_filter = request.GET.get('category', '')
    if category_filter:
        qs = qs.filter(category=category_filter)
    low_stock_only = request.GET.get('low_stock', '')
    items = list(qs)
    if low_stock_only:
        items = [i for i in items if i.is_low_stock]
    return render(request, 'attendance/inventory_list.html', {
        'items': items,
        'category_filter': category_filter,
        'low_stock_only': low_stock_only,
        'category_choices': InventoryItem.CATEGORY_CHOICES,
    })


@login_required
@user_passes_test(lambda u: hasattr(u, 'profile') and u.profile.role in ['punong_barangay', 'admin', 'secretary', 'treasurer'])
def inventory_create(request):
    if request.method == 'POST':
        InventoryItem.objects.create(
            name=request.POST.get('name'),
            category=request.POST.get('category', 'other'),
            quantity=request.POST.get('quantity', 0),
            unit=request.POST.get('unit', 'piece'),
            minimum_stock=request.POST.get('minimum_stock', 5),
            location=request.POST.get('location', ''),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Inventory item added.')
        return redirect('inventory_list')
    return render(request, 'attendance/inventory_form.html', {
        'category_choices': InventoryItem.CATEGORY_CHOICES, 'action': 'Add',
    })


@login_required
@user_passes_test(is_utility_level)
def daily_log_create(request):
    today = datetime.date.today()
    existing = DailyActivityLog.objects.filter(user=request.user, date=today).first()
    if request.method == 'POST':
        if existing:
            existing.activities = request.POST.get('activities')
            existing.time_in = request.POST.get('time_in') or None
            existing.time_out = request.POST.get('time_out') or None
            existing.notes = request.POST.get('notes', '')
            existing.save()
            messages.success(request, 'Daily log updated.')
        else:
            DailyActivityLog.objects.create(
                user=request.user,
                date=today,
                activities=request.POST.get('activities'),
                time_in=request.POST.get('time_in') or None,
                time_out=request.POST.get('time_out') or None,
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, 'Daily log saved.')
        return redirect('utility_dashboard')
    return render(request, 'attendance/daily_log_form.html', {
        'existing': existing, 'today': today,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@user_passes_test(is_captain_or_admin)
def audit_log_list(request):
    qs = AuditLog.objects.select_related('user').all()
    q = request.GET.get('q', '')
    action_filter = request.GET.get('action', '')
    if q:
        qs = qs.filter(
            Q(model_name__icontains=q) | Q(object_repr__icontains=q) |
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
        )
    if action_filter:
        qs = qs.filter(action=action_filter)
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'attendance/audit_log_list.html', {
        'page_obj': page_obj,
        'q': q,
        'action_filter': action_filter,
        'action_choices': AuditLog.ACTION_CHOICES,
    })


# ─── API endpoints for new modules ────────────────────────────────────────────

@login_required
@require_GET
def api_captain_stats(request):
    if not is_captain_or_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    today = datetime.date.today()
    return JsonResponse({
        'pending_approvals': ApprovalRequest.objects.filter(status='pending').count(),
        'active_projects': BarangayProject.objects.filter(status__in=['approved', 'ongoing']).count(),
        'open_complaints': Complaint.objects.filter(status__in=['filed', 'under_investigation']).count(),
        'pending_ordinances': Ordinance.objects.filter(status='pending_approval').count(),
        'open_incidents': IncidentReport.objects.filter(is_resolved=False).count(),
    })


@login_required
@require_GET
def api_financial_summary(request):
    if not is_treasurer(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    today = datetime.date.today()
    monthly = []
    for m in range(1, 13):
        rev = sum(
            FinancialRecord.objects.filter(type='revenue', transaction_date__month=m, transaction_date__year=today.year).values_list('amount', flat=True)
        )
        exp = sum(
            FinancialRecord.objects.filter(type='expense', transaction_date__month=m, transaction_date__year=today.year).values_list('amount', flat=True)
        )
        monthly.append({'month': m, 'revenue': float(rev), 'expense': float(exp)})
    return JsonResponse({'monthly': monthly})
