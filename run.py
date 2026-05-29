#!/usr/bin/env python3
"""
run.py — Auto-setup and launch script for Brgy. San Jose Attendance Registry.

Usage:
    python run.py                  # Normal start (migrate + run on port 8000)
    python run.py --reset          # Clear DB, re-seed, then run
    python run.py --port 8080      # Run on custom port
    python run.py --reset --port 8080
    python run.py --production     # Run with gunicorn (for 24/7 hosting)

What this script does:
    1. Installs required dependencies (Django, Pillow, whitenoise, gunicorn)
    2. Runs database migrations
    3. Seeds sample data (if DB is fresh or --reset is passed)
    4. Launches the server (development or production)
"""

import os
import sys
import subprocess
import argparse
import platform


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANAGE = os.path.join(BASE_DIR, 'manage.py')
PYTHON = sys.executable


def run_cmd(cmd, check=True):
    print(f'\n▶  {" ".join(cmd)}\n{"─" * 50}')
    result = subprocess.run(cmd, cwd=BASE_DIR, check=check)
    return result.returncode


def is_windows():
    return platform.system().lower() == 'windows'


def install_deps():
    print('\n📦  Checking dependencies...')
    run_cmd([PYTHON, '-m', 'pip', 'install', '-r', 'requirements.txt', '-q'], check=False)


def main():
    parser = argparse.ArgumentParser(
        description='Auto-setup and run the Brgy. San Jose Attendance Registry'
    )
    parser.add_argument('--reset', action='store_true', help='Reset the database and re-seed all sample data')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on (default: 8000)')
    parser.add_argument('--no-seed', action='store_true', help='Skip seed data generation')
    parser.add_argument('--production', action='store_true', help='Run with gunicorn for production/24-7 hosting')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()

    print()
    print('=' * 60)
    print('  🏛️  BRGY. SAN JOSE — OFFICIAL ATTENDANCE & REGISTRY')
    print('=' * 60)
    print(f'  Location : Brgy. San Jose, Surigao City')
    print(f'  Port     : {args.port}')
    print(f'  Mode     : {"Production (gunicorn)" if args.production else "Development"}')
    print(f'  Reset    : {"Yes — will clear & re-seed data" if args.reset else "No"}')
    print('=' * 60)

    install_deps()

    print('\n⚙️   Running database migrations...')
    run_cmd([PYTHON, MANAGE, 'migrate', '--run-syncdb'])

    if not args.no_seed:
        print('\n🌱  Seeding sample data...')
        seed_cmd = [PYTHON, MANAGE, 'seed_data']
        if args.reset:
            seed_cmd.append('--reset')
        run_cmd(seed_cmd, check=False)

    if args.production:
        print('\n📦  Collecting static files...')
        run_cmd([PYTHON, MANAGE, 'collectstatic', '--noinput'])

    addr = f'{args.host}:{args.port}'
    print(f'\n🚀  Starting server at http://127.0.0.1:{args.port}/')
    print(f'    Admin panel   : http://127.0.0.1:{args.port}/admin/')
    print(f'    Login         : http://127.0.0.1:{args.port}/login/')
    print(f'    Activity Log  : http://127.0.0.1:{args.port}/admin-panel/login-activity/')
    print(f'\n    Default credentials: admin / admin123')
    print(f'    Press Ctrl+C to stop.\n')
    print('=' * 60)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barangay_config.settings')

    if args.production:
        if is_windows():
            print('\n⚠️  Gunicorn is unsupported on Windows. Falling back to Django runserver for compatibility.')
            run_cmd([PYTHON, MANAGE, 'runserver', addr])
        else:
            workers = 3
            if run_cmd(['gunicorn', 'barangay_config.wsgi:application',
                        f'--bind={addr}', f'--workers={workers}',
                        '--timeout=120', '--access-logfile=-'], check=False) != 0:
                print('\n⚠️  gunicorn failed; falling back to Django runserver.')
                run_cmd([PYTHON, MANAGE, 'runserver', addr])
    else:
        run_cmd([PYTHON, MANAGE, 'runserver', addr])


if __name__ == '__main__':
    main()
