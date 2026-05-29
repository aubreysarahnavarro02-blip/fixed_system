"""
Management command: seed_data
Auto-generates 40 citizens, 10 sessions, ~200 attendance records.

Usage:
    python manage.py seed_data
    python manage.py seed_data --reset
"""

import random
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from attendance.models import UserProfile, Hall, Session, Citizen, AttendanceRecord, Announcement


FIRST_NAMES_M = ['UserM']
FIRST_NAMES_F = ['UserF']
LAST_NAMES = ['Surname']
MIDDLE_NAMES = ['Middle']
CATEGORIES = [
    ('official', 3), ('kagawad', 7), ('tanod', 5), ('resident', 15),
    ('sk', 3), ('senior', 4), ('pwd', 2), ('youth', 1),
]
SESSION_TYPES = [
    'regular', 'special', 'committee', 'assembly', 'seminar',
    'livelihood', 'health', 'emergency',
]
SESSION_TITLES = [
    'Session 1',
    'Session 2',
    'Session 3',
    'Session 4',
    'Session 5',
    'Session 6',
    'Session 7',
    'Session 8',
    'Session 9',
    'Session 10',
]
HALLS = [
    {'name': 'Hall 1', 'capacity': 100},
    {'name': 'Hall 2', 'capacity': 150},
    {'name': 'Hall 3', 'capacity': 80},
    {'name': 'Hall 4', 'capacity': 120},
]
ANNOUNCEMENTS = [
    {'title': 'Announcement 1', 'content': '', 'priority': 'normal'},
    {'title': 'Announcement 2', 'content': '', 'priority': 'normal'},
    {'title': 'Announcement 3', 'content': '', 'priority': 'normal'},
    {'title': 'Announcement 4', 'content': '', 'priority': 'normal'},
]


class Command(BaseCommand):
    help = 'Seeds the database with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear all existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('🗑  Clearing existing data...')
            AttendanceRecord.objects.all().delete()
            Session.objects.all().delete()
            Citizen.objects.all().delete()
            Hall.objects.all().delete()
            Announcement.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING('   All data cleared.'))

        # ── Admin User ─────────────────────────────────────────────────────────
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
            }
        )
        admin.set_password('admin123')
        admin.email = 'admin@example.com'
        admin.first_name = 'Admin'
        admin.last_name = 'User'
        admin.is_superuser = True
        admin.is_staff = True
        admin.save()
        admin.profile.role = 'admin'
        admin.profile.position = 'Administrator'
        admin.profile.save()
        self.stdout.write(self.style.SUCCESS('✅  Admin user created or updated (username: admin / password: admin123)'))

        # ── Staff Users ────────────────────────────────────────────────────────
        staff_accounts = [
            ('secretary', 'Secretary', 'User', 'secretary', 'Secretary'),
            ('treasurer', 'Treasurer', 'User', 'treasurer', 'Treasurer'),
            ('tanod1', 'Tanod', 'User', 'tanod', 'Tanod'),
            ('bhw1', 'BHW', 'User', 'bhw', 'BHW'),
            ('bns1', 'BNS', 'User', 'bns', 'BNS'),
            ('utility1', 'Utility', 'User', 'utility', 'Utility Staff'),
            ('kagawad1', 'Kagawad', 'User', 'kagawad', 'Kagawad'),
            ('staff1', 'Staff', 'User', 'staff', 'Staff'),
        ]
        for uname, fname, lname, role, position in staff_accounts:
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'email': f'{uname}@example.com',
                }
            )
            u.set_password('brgy2024')
            u.first_name = fname
            u.last_name = lname
            u.email = f'{uname}@example.com'
            u.is_active = True
            u.save()
            u.profile.role = role
            u.profile.position = position
            u.profile.save()
        self.stdout.write(self.style.SUCCESS('✅  Staff accounts created or updated (password: brgy2024)'))

        admin_user = User.objects.filter(is_superuser=True).first()

        # ── Halls ──────────────────────────────────────────────────────────────
        halls = []
        for h in HALLS:
            hall, _ = Hall.objects.get_or_create(
                name=h['name'],
                defaults={
                    'location': 'Default Location',
                    'capacity': h['capacity'],
                    'status': 'available',
                }
            )
            halls.append(hall)
        self.stdout.write(self.style.SUCCESS(f'✅  {len(halls)} halls created'))

        # ── Citizens ───────────────────────────────────────────────────────────
        citizens = []
        random.seed(42)
        citizen_pool = []
        for cat, count in CATEGORIES:
            citizen_pool.extend([cat] * count)
        random.shuffle(citizen_pool)

        for i, category in enumerate(citizen_pool):
            gender = random.choice(['M', 'F'])
            first = random.choice(FIRST_NAMES_M if gender == 'M' else FIRST_NAMES_F)
            last = random.choice(LAST_NAMES)
            middle = random.choice(MIDDLE_NAMES)
            birth_year = random.randint(1950, 2005)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)
            contact = f'09{random.randint(100000000, 999999999)}'
            precinct = f'{random.randint(1, 8):02d}A'

            c, created = Citizen.objects.get_or_create(
                first_name=first,
                last_name=last,
                middle_name=middle,
                defaults={
                    'gender': gender,
                    'category': category,
                    'date_of_birth': datetime.date(birth_year, birth_month, birth_day),
                    'civil_status': random.choice(['single', 'married', 'widowed']),
                    'address': f'Address Line {random.randint(1, 8)}',
                    'contact_number': contact,
                    'precinct_number': precinct,
                    'is_active': True,
                }
            )
            citizens.append(c)

        self.stdout.write(self.style.SUCCESS(f'✅  {len(citizens)} citizens created'))

        # ── Sessions ───────────────────────────────────────────────────────────
        sessions = []
        today = datetime.date.today()
        for i, title in enumerate(SESSION_TITLES):
            days_ago = (len(SESSION_TITLES) - i - 2) * 14
            s_date = today - datetime.timedelta(days=days_ago)
            status = 'completed' if days_ago > 7 else ('ongoing' if days_ago == 0 else 'scheduled')

            session, _ = Session.objects.get_or_create(
                title=title,
                defaults={
                    'session_type': SESSION_TYPES[i % len(SESSION_TYPES)],
                    'hall': random.choice(halls),
                    'date': s_date,
                    'start_time': datetime.time(9, 0),
                    'end_time': datetime.time(12, 0),
                    'status': status,
                    'presided_by': 'Meeting Chairperson',
                    'agenda': f'Session agenda for {title}',
                    'created_by': admin_user,
                }
            )
            sessions.append(session)

        self.stdout.write(self.style.SUCCESS(f'✅  {len(sessions)} sessions created'))

        # ── Attendance Records ─────────────────────────────────────────────────
        record_count = 0
        for session in sessions:
            if session.status not in ['completed', 'ongoing']:
                continue
            for citizen in citizens:
                # Weighted random: 70% present/late, 20% absent, 10% excused
                roll = random.random()
                if roll < 0.60:
                    status = 'present'
                elif roll < 0.75:
                    status = 'late'
                elif roll < 0.90:
                    status = 'absent'
                else:
                    status = 'excused'

                time_in = None
                time_out = None
                if status in ('present', 'late'):
                    hour = 9 if status == 'present' else random.randint(9, 10)
                    minute = random.randint(0, 30) if status == 'present' else random.randint(15, 59)
                    dt = datetime.datetime.combine(session.date, datetime.time(hour, minute))
                    time_in = timezone.make_aware(dt)
                    time_out = time_in + datetime.timedelta(hours=random.randint(2, 4))

                rec, created = AttendanceRecord.objects.get_or_create(
                    session=session,
                    citizen=citizen,
                    defaults={
                        'status': status,
                        'time_in': time_in,
                        'time_out': time_out,
                        'marked_by': admin_user,
                    }
                )
                if created:
                    record_count += 1

        self.stdout.write(self.style.SUCCESS(f'✅  {record_count} attendance records created'))

        # ── Announcements ──────────────────────────────────────────────────────
        for ann_data in ANNOUNCEMENTS:
            Announcement.objects.get_or_create(
                title=ann_data['title'],
                defaults={
                    'content': ann_data['content'],
                    'priority': ann_data['priority'],
                    'is_published': True,
                    'published_by': admin_user,
                }
            )
        self.stdout.write(self.style.SUCCESS(f'✅  {len(ANNOUNCEMENTS)} announcements created'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  SEEDING COMPLETE — Sample Data Seed'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Citizens   : {Citizen.objects.count()}')
        self.stdout.write(f'  Sessions   : {Session.objects.count()}')
        self.stdout.write(f'  Records    : {AttendanceRecord.objects.count()}')
        self.stdout.write(f'  Halls      : {Hall.objects.count()}')
        self.stdout.write('')
        self.stdout.write('  Login Credentials:')
        self.stdout.write('  ┌─────────────┬──────────┬────────────┐')
        self.stdout.write('  │ Username    │ Password │ Role       │')
        self.stdout.write('  ├─────────────┼──────────┼────────────┤')
        self.stdout.write('  │ admin       │ admin123 │ Admin      │')
        self.stdout.write('  │ secretary   │ brgy2024 │ Secretary  │')
        self.stdout.write('  │ treasurer   │ brgy2024 │ Treasurer  │')
        self.stdout.write('  │ tanod1      │ brgy2024 │ Tanod      │')
        self.stdout.write('  │ bhw1        │ brgy2024 │ BHW        │')
        self.stdout.write('  │ bns1        │ brgy2024 │ BNS        │')
        self.stdout.write('  │ utility1    │ brgy2024 │ Utility    │')
        self.stdout.write('  │ kagawad1    │ brgy2024 │ Kagawad    │')
        self.stdout.write('  │ staff1      │ brgy2024 │ Staff      │')
        self.stdout.write('  └─────────────┴──────────┴────────────┘')
        self.stdout.write(self.style.SUCCESS('=' * 60))
