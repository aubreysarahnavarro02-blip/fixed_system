from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import datetime


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('punong_barangay', 'Punong Barangay (Captain)'),
        ('admin', 'Barangay Administrator'),
        ('secretary', 'Barangay Secretary'),
        ('treasurer', 'Barangay Treasurer'),
        ('kagawad', 'Barangay Kagawad'),
        ('sb_chairperson', 'SB Chairperson'),
        ('tanod', 'Barangay Tanod'),
        ('bhw', 'Barangay Health Worker'),
        ('bns', 'Barangay Nutrition Scholar'),
        ('utility', 'Utility / Admin Staff'),
        ('staff', 'Barangay Staff'),
        ('viewer', 'Viewer'),
    ]
    COMMITTEE_CHOICES = [
        ('', 'None'),
        ('peace_order', 'Peace and Order'),
        ('health', 'Health and Sanitation'),
        ('education', 'Education'),
        ('infrastructure', 'Infrastructure'),
        ('livelihood', 'Livelihood'),
        ('environment', 'Environment'),
        ('youth', 'Youth and Sports'),
        ('women', "Women's Affairs"),
        ('senior', 'Senior Citizens'),
        ('finance', 'Finance and Budget'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='viewer')
    contact_number = models.CharField(max_length=15, blank=True)
    position = models.CharField(max_length=100, blank=True)
    committee = models.CharField(max_length=30, choices=COMMITTEE_CHOICES, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Hall(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
    ]
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, default='Brgy. San Jose, Surigao City')
    capacity = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Hall / Venue"
        verbose_name_plural = "Halls / Venues"


class Session(models.Model):
    SESSION_TYPE_CHOICES = [
        ('regular', 'Regular Session'),
        ('special', 'Special Session'),
        ('emergency', 'Emergency Session'),
        ('committee', 'Committee Meeting'),
        ('assembly', 'Barangay Assembly'),
        ('seminar', 'Seminar / Training'),
        ('livelihood', 'Livelihood Program'),
        ('health', 'Health Program'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    title = models.CharField(max_length=200)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='regular')
    description = models.TextField(blank=True)
    hall = models.ForeignKey(Hall, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    presided_by = models.CharField(max_length=100, blank=True)
    agenda = models.TextField(blank=True)
    minutes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_late_threshold(self):
        return datetime.time(self.start_time.hour, self.start_time.minute + 15
                             if self.start_time.minute <= 44 else 0)

    def attendance_count(self):
        return self.attendance_records.filter(status__in=['present', 'late']).count()

    def __str__(self):
        return f"{self.title} - {self.date}"

    class Meta:
        ordering = ['-date', '-start_time']
        verbose_name = "Session"
        verbose_name_plural = "Sessions"


class Citizen(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    CIVIL_STATUS_CHOICES = [
        ('single', 'Single'), ('married', 'Married'),
        ('widowed', 'Widowed'), ('separated', 'Separated'),
    ]
    CATEGORY_CHOICES = [
        ('official', 'Barangay Official'), ('kagawad', 'Kagawad'),
        ('tanod', 'Barangay Tanod'), ('resident', 'Registered Resident'),
        ('sk', 'SK Official'), ('lumad', 'Lumad/Indigenous'),
        ('senior', 'Senior Citizen'), ('pwd', 'Person with Disability'),
        ('youth', 'Youth'), ('other', 'Other'),
    ]
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=10, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    civil_status = models.CharField(max_length=20, choices=CIVIL_STATUS_CHOICES, default='single')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='resident')
    address = models.TextField(default='Brgy. San Jose, Surigao City')
    contact_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    precinct_number = models.CharField(max_length=20, blank=True)
    voter_id = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to='citizens/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name[0] + '.')
        parts.append(self.last_name)
        if self.suffix:
            parts.append(self.suffix)
        return ' '.join(parts)

    @property
    def age(self):
        if self.date_of_birth:
            today = datetime.date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

    def attendance_rate(self):
        total = AttendanceRecord.objects.filter(citizen=self).count()
        if total == 0:
            return 0
        present = AttendanceRecord.objects.filter(citizen=self, status__in=['present', 'late']).count()
        return round((present / total) * 100, 1)

    def __str__(self):
        return self.full_name

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Citizen"
        verbose_name_plural = "Citizens"


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'), ('late', 'Late'),
        ('absent', 'Absent'), ('excused', 'Excused'),
    ]
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendance_records')
    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='absent')
    time_in = models.DateTimeField(null=True, blank=True)
    time_out = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_late(self):
        if self.time_in and self.session.start_time:
            session_dt = datetime.datetime.combine(self.session.date, self.session.start_time)
            grace_period = session_dt + datetime.timedelta(minutes=15)
            return self.time_in.replace(tzinfo=None) > grace_period
        return False

    def __str__(self):
        return f"{self.citizen.full_name} - {self.session.title} ({self.status})"

    class Meta:
        unique_together = ['session', 'citizen']
        ordering = ['-created_at']
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"


class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent'),
    ]
    TARGET_CHOICES = [
        ('all', 'All'), ('officials', 'Officials Only'), ('tanod', 'Tanod'),
        ('bhw', 'Health Workers'), ('bns', 'Nutrition Scholars'), ('residents', 'Residents'),
    ]
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    target_audience = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all')
    is_published = models.BooleanField(default=True)
    published_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self):
        if self.expires_at:
            return self.is_published and timezone.now() < self.expires_at
        return self.is_published

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"


class LoginActivity(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'), ('logout', 'Logout'),
        ('failed', 'Failed Login'), ('register', 'Registered'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='login_activities')
    username_attempted = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        name = self.user.username if self.user else self.username_attempted
        return f"{name} — {self.action} @ {self.timestamp:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Login Activity"
        verbose_name_plural = "Login Activities"


# ─── EXTENDED MODELS ──────────────────────────────────────────────────────────

class Ordinance(models.Model):
    TYPE_CHOICES = [('ordinance', 'Ordinance'), ('resolution', 'Resolution')]
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('pending_approval', 'Pending Captain Approval'),
        ('approved', 'Approved'), ('rejected', 'Rejected'), ('enacted', 'Enacted'),
    ]
    number = models.CharField(max_length=50)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='ordinance')
    title = models.CharField(max_length=300)
    content = models.TextField()
    committee = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    drafted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='drafted_ordinances')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_ordinances')
    approval_date = models.DateField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    date_filed = models.DateField(auto_now_add=True)
    date_enacted = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_type_display()} No. {self.number} — {self.title[:60]}"

    class Meta:
        ordering = ['-date_filed']
        verbose_name = "Ordinance / Resolution"
        verbose_name_plural = "Ordinances & Resolutions"


class ApprovalRequest(models.Model):
    TYPE_CHOICES = [
        ('document', 'Document Clearance'), ('financial', 'Financial Disbursement'),
        ('project', 'Project Proposal'), ('ordinance', 'Ordinance/Resolution'),
        ('program', 'Program Activity'), ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('returned', 'Returned for Revision'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approval_requests')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_display()}: {self.title} [{self.status}]"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Approval Request"
        verbose_name_plural = "Approval Requests"


class BarangayProject(models.Model):
    STATUS_CHOICES = [
        ('proposed', 'Proposed'), ('approved', 'Approved'), ('ongoing', 'Ongoing'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('suspended', 'Suspended'),
    ]
    CATEGORY_CHOICES = [
        ('infrastructure', 'Infrastructure'), ('health', 'Health'),
        ('education', 'Education'), ('livelihood', 'Livelihood'),
        ('environment', 'Environment'), ('peace_order', 'Peace and Order'),
        ('sports', 'Youth and Sports'), ('social', 'Social Services'), ('other', 'Other'),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    description = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='proposed')
    budget_allocated = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    budget_used = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    progress_percent = models.PositiveIntegerField(default=0)
    committee_in_charge = models.CharField(max_length=100, blank=True)
    project_head = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_projects')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_projects')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def budget_remaining(self):
        return self.budget_allocated - self.budget_used

    def __str__(self):
        return f"{self.title} [{self.status}]"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Barangay Project"
        verbose_name_plural = "Barangay Projects"


class FinancialRecord(models.Model):
    TYPE_CHOICES = [('revenue', 'Revenue'), ('expense', 'Expense'), ('transfer', 'Fund Transfer')]
    FUND_CHOICES = [
        ('general', 'General Fund'), ('20percent', '20% Development Fund'),
        ('sk', 'SK Fund'), ('trust', 'Trust Fund'), ('calamity', 'Calamity Fund'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('disbursed', 'Disbursed'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    fund = models.CharField(max_length=20, choices=FUND_CHOICES, default='general')
    description = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference_number = models.CharField(max_length=100, blank=True)
    or_number = models.CharField(max_length=50, blank=True, verbose_name="OR Number")
    payee = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='financial_records')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_finances')
    approved_at = models.DateTimeField(null=True, blank=True)
    transaction_date = models.DateField(default=datetime.date.today)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_display()}: {self.description} — P{self.amount:,.2f}"

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        verbose_name = "Financial Record"
        verbose_name_plural = "Financial Records"


class BudgetAllocation(models.Model):
    fiscal_year = models.PositiveIntegerField()
    fund = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2)
    used_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def remaining(self):
        return self.allocated_amount - self.used_amount

    def __str__(self):
        return f"FY{self.fiscal_year} — {self.fund}"

    class Meta:
        ordering = ['-fiscal_year']
        verbose_name = "Budget Allocation"
        verbose_name_plural = "Budget Allocations"


class Complaint(models.Model):
    STATUS_CHOICES = [
        ('filed', 'Filed'), ('under_investigation', 'Under Investigation'),
        ('mediation', 'For Mediation'), ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'), ('escalated', 'Escalated'),
    ]
    TYPE_CHOICES = [
        ('noise', 'Noise Complaint'), ('neighbor', 'Neighbor Dispute'),
        ('property', 'Property Dispute'), ('domestic', 'Domestic Issue'),
        ('criminal', 'Criminal Complaint'), ('environmental', 'Environmental'),
        ('other', 'Other'),
    ]
    case_number = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    complainant_name = models.CharField(max_length=200)
    respondent_name = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='filed')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints')
    filed_date = models.DateField(auto_now_add=True)
    resolved_date = models.DateField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Case {self.case_number}: {self.complainant_name} vs {self.respondent_name}"

    class Meta:
        ordering = ['-filed_date']
        verbose_name = "Complaint / Case"
        verbose_name_plural = "Complaints & Cases"


class IncidentReport(models.Model):
    TYPE_CHOICES = [
        ('crime', 'Crime'), ('accident', 'Accident'), ('fire', 'Fire'),
        ('flood', 'Flood/Disaster'), ('disturbance', 'Public Disturbance'),
        ('missing', 'Missing Person'), ('medical', 'Medical Emergency'), ('other', 'Other'),
    ]
    SEVERITY_CHOICES = [
        ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('critical', 'Critical'),
    ]
    report_number = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='moderate')
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=300)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='incident_reports')
    incident_date = models.DateTimeField()
    is_resolved = models.BooleanField(default=False)
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_number}: {self.title}"

    class Meta:
        ordering = ['-incident_date']
        verbose_name = "Incident Report"
        verbose_name_plural = "Incident Reports"


class PatrolSchedule(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'), ('ongoing', 'On Patrol'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    area = models.CharField(max_length=200)
    tanod_members = models.ManyToManyField(User, related_name='patrol_schedules', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_patrols')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Patrol — {self.area} on {self.date}"

    class Meta:
        ordering = ['-date', '-start_time']
        verbose_name = "Patrol Schedule"
        verbose_name_plural = "Patrol Schedules"


class HealthRecord(models.Model):
    CONDITION_CHOICES = [
        ('healthy', 'Healthy'), ('monitored', 'Under Monitoring'),
        ('critical', 'Critical'), ('referred', 'Referred to Facility'),
    ]
    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE, related_name='health_records')
    bhw = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='health_records_managed')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='healthy')
    blood_type = models.CharField(max_length=5, blank=True)
    allergies = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    last_checkup = models.DateField(null=True, blank=True)
    next_checkup = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Health Record — {self.citizen.full_name}"

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Health Record"
        verbose_name_plural = "Health Records"


class ImmunizationRecord(models.Model):
    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE, related_name='immunizations')
    vaccine_name = models.CharField(max_length=100)
    dose = models.CharField(max_length=50, blank=True)
    date_given = models.DateField()
    next_dose_date = models.DateField(null=True, blank=True)
    administered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.citizen.full_name} — {self.vaccine_name} ({self.date_given})"

    class Meta:
        ordering = ['-date_given']
        verbose_name = "Immunization Record"
        verbose_name_plural = "Immunization Records"


class NutritionRecord(models.Model):
    STATUS_CHOICES = [
        ('normal', 'Normal'), ('underweight', 'Underweight'),
        ('severely_underweight', 'Severely Underweight'),
        ('overweight', 'Overweight'), ('obese', 'Obese'),
    ]
    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE, related_name='nutrition_records')
    bns = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='nutrition_records_managed')
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    muac_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="MUAC (cm)")
    nutritional_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='normal')
    is_enrolled_feeding = models.BooleanField(default=False)
    monitoring_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nutrition — {self.citizen.full_name} ({self.monitoring_date})"

    class Meta:
        ordering = ['-monitoring_date']
        verbose_name = "Nutrition Record"
        verbose_name_plural = "Nutrition Records"


class FeedingProgram(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'), ('ongoing', 'Ongoing'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    location = models.CharField(max_length=200)
    beneficiary_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.date}"

    class Meta:
        ordering = ['-date']
        verbose_name = "Feeding Program"
        verbose_name_plural = "Feeding Programs"


class HouseholdVisit(models.Model):
    PURPOSE_CHOICES = [
        ('health_check', 'Health Check'), ('nutrition', 'Nutrition Monitoring'),
        ('immunization', 'Immunization Follow-up'), ('maternal', 'Maternal Care'),
        ('general', 'General Visit'),
    ]
    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE, related_name='household_visits')
    visitor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='conducted_visits')
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    visit_date = models.DateField()
    findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    next_visit_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visit — {self.citizen.full_name} ({self.visit_date})"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = "Household Visit"
        verbose_name_plural = "Household Visits"


class MaintenanceTask(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_tasks')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_tasks')
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} [{self.status}]"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Maintenance Task"
        verbose_name_plural = "Maintenance Tasks"


class InventoryItem(models.Model):
    CATEGORY_CHOICES = [
        ('office', 'Office Supplies'), ('cleaning', 'Cleaning Supplies'),
        ('medical', 'Medical Supplies'), ('equipment', 'Equipment'),
        ('furniture', 'Furniture'), ('other', 'Other'),
    ]
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50, default='piece')
    minimum_stock = models.PositiveIntegerField(default=5)
    location = models.CharField(max_length=100, blank=True)
    last_restocked = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"


class DailyActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_logs')
    date = models.DateField()
    activities = models.TextField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.date}"

    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
        verbose_name = "Daily Activity Log"
        verbose_name_plural = "Daily Activity Logs"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Created'), ('update', 'Updated'), ('delete', 'Deleted'),
        ('approve', 'Approved'), ('reject', 'Rejected'), ('view', 'Viewed'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    object_repr = models.CharField(max_length=300)
    changes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} {self.action} {self.model_name}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
