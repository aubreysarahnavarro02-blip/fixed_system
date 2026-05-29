from django.conf import settings

def site_settings(request):
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Barangay Official Attendance Registry'),
        'SITE_SHORT': getattr(settings, 'SITE_SHORT', 'BOAR System'),
        'BARANGAY_NAME': getattr(settings, 'BARANGAY_NAME', 'Brgy. San Jose'),
        'BARANGAY_CITY': getattr(settings, 'BARANGAY_CITY', 'Surigao City'),
        'BARANGAY_PROVINCE': getattr(settings, 'BARANGAY_PROVINCE', 'Surigao del Norte'),
    }
