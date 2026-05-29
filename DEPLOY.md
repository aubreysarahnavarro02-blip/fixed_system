# 🚀 Deployment Guide — Barangay Official Attendance Registry

## Option 1: Local / LAN (Development)
```bash
python run.py
# Access: http://localhost:8000
```

## Option 2: Production / 24-7 Hosting (Railway, Render, VPS)

### Render.com (Free Tier — 24/7)
1. Push this folder to a GitHub repository
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn barangay_config.wsgi:application`
   - **Environment Variables:**
     - `SECRET_KEY` = (generate a random string)
     - `DEBUG` = `False`
     - `ALLOWED_HOSTS` = `your-app.onrender.com`

### Railway.app (Easy Deploy)
1. Push to GitHub
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Add environment variables as above
4. Railway auto-detects Django

### VPS / Dedicated Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run with production mode
python run.py --production --port 8000

# Or use gunicorn directly
gunicorn barangay_config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## Default Login
- **Username:** `admin`
- **Password:** `admin123`

## Features
- ✅ Attendance Form & Attendance List
- ✅ Citizen Profiles (edit, save, delete)
- ✅ User Form (register, edit, delete)
- ✅ Admin Login Activity Monitor
- ✅ REST API endpoints
- ✅ Session management with Time In/Out
- ✅ PDF & CSV export
- ✅ Calendar view
- ✅ Announcements
- ✅ Reports & Charts
