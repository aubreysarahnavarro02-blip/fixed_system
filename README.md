# Barangay Official Attendance Registry (BOAR System)

**Brgy. San Jose, Surigao City, Surigao del Norte**

A comprehensive barangay management and attendance registry system built with Django.

---

## Modules & Role Access

| Role | Module |
|---|---|
| **Punong Barangay** | Executive Dashboard, Approvals, Ordinances, Projects, Finances (view/approve), Complaints, Audit Log |
| **Secretary** | Sessions, Citizens, Records, Announcements, Hall Booking |
| **Treasurer** | Financial Dashboard, Revenue/Expense, Budget Allocations |
| **SB Chairperson / Kagawad** | Ordinances, Projects, Complaints, Committee Work |
| **Tanod** | Incident Reporting, Patrol Schedule, Blotter Access |
| **BHW** | Health Records, Immunization, Household Visits |
| **BNS** | Nutrition Monitoring, Feeding Programs, Growth Tracking |
| **Utility / Admin Staff** | Task Management, Inventory, Daily Log |

---

## Quick Start (Local Development)

```bash
# 1. Clone or extract project
cd barangay_official_registry

# 2. Create virtualenv
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and edit environment file
cp .env.example .env
# Edit .env: set DEBUG=True, DB_ENGINE=sqlite

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Start development server
python manage.py runserver
# Visit: http://127.0.0.1:8000
```

---

## Production Deployment (VPS + Nginx + PostgreSQL)

### Requirements
- Ubuntu 22.04 / 24.04 VPS (1GB RAM minimum, 2GB recommended)
- Domain name pointed to your VPS IP
- Root SSH access

### Steps

```bash
# 1. Upload your project to /var/www/boar
scp -r barangay_official_registry/ root@YOUR_VPS_IP:/var/www/boar

# 2. Edit deploy.sh — set your DOMAIN variable
nano /var/www/boar/deploy.sh

# 3. Run the deployment script
sudo bash /var/www/boar/deploy.sh

# 4. Add SSL certificate (after DNS propagates)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 5. Verify everything is running
sudo systemctl status boar
sudo systemctl status nginx
```

### Service Management

```bash
sudo systemctl start   boar    # Start the app
sudo systemctl stop    boar    # Stop the app
sudo systemctl restart boar    # Restart after changes
sudo systemctl reload  boar    # Zero-downtime reload
sudo journalctl -u boar -f     # View live logs
```

### Updates / Deployments

```bash
# After pulling new code:
sudo bash /var/www/boar/update.sh
```

### Backup

```bash
# Manual backup:
sudo bash /var/www/boar/backup.sh

# Automated daily backup (add to crontab):
sudo crontab -e
# Add: 0 2 * * * /var/www/boar/backup.sh >> /var/log/boar/backup.log 2>&1
```

---

## File Structure

```
barangay_official_registry/
├── attendance/
│   ├── models.py          # All data models (18 models)
│   ├── views.py           # All view functions (~70 views)
│   ├── urls.py            # All URL routes (~80 routes)
│   ├── forms.py           # Django forms
│   ├── admin.py           # Django admin registration
│   └── context_processors.py
├── barangay_config/
│   ├── settings.py        # Production-ready settings
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py
├── templates/
│   ├── base.html          # Master layout with role-based nav
│   └── attendance/        # All 60+ page templates
├── static/                # CSS, JS, images
├── deploy.sh              # Full VPS deployment script
├── update.sh              # Zero-downtime update script
├── backup.sh              # Database + media backup script
├── gunicorn.conf.py       # Gunicorn server configuration
├── nginx.conf             # Nginx site configuration
├── boar.service           # systemd service unit
├── requirements.txt       # Python dependencies
└── .env.example           # Environment variable template
```

---

## Default Admin Credentials (Change Immediately!)
- **Username:** `admin`
- **Password:** `Admin@BOAR2025!`

---

## Tech Stack
- **Backend:** Django 4.2, Python 3.11
- **Database:** PostgreSQL (production) / SQLite (development)
- **Server:** Gunicorn + Nginx
- **Process Manager:** systemd
- **SSL:** Let's Encrypt / Certbot
- **Static Files:** WhiteNoise

## License
Submission Note

This project is submitted in compliance with the course requirements. The source code, documentation, and related project files are included in this submission. The required Copyright Submission Template from the Materials tab has been completed and submitted together with the project.

All work contained in this submission is original and developed for academic purposes.