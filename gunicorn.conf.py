# Gunicorn configuration for Barangay Official Attendance Registry
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
loglevel = "info"
accesslog = "/var/log/boar/gunicorn_access.log"
errorlog  = "/var/log/boar/gunicorn_error.log"
capture_output = True

# Process naming
proc_name = "boar_gunicorn"

# Reload on code change (disable in production)
reload = False
