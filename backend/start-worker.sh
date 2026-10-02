#!/bin/sh
set -e

echo "=== [Railway Deploy] Starting Tribal Scholar Celery Worker ==="

export FLAGS_enable_pir_api=0
export FLAGS_use_mkldnn=0
export PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=2

# Wait for database & redis
python - << 'EOF'
import sys, time, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tribel_scholar.settings")
django.setup()
from django.db import connection
from django.conf import settings
import redis

for attempt in range(1, 31):
    try:
        connection.ensure_connection()
        redis_url = getattr(settings, 'REDIS_URL', None) or getattr(settings, 'CELERY_BROKER_URL', None)
        if redis_url:
            r = redis.from_url(redis_url, socket_timeout=2.0)
            if r.ping():
                print("Database and Redis connections verified for Celery worker!")
                sys.exit(0)
    except Exception as e:
        print(f"[Worker Attempt {attempt}/30] Waiting for dependencies: {e}")
        time.sleep(2)

print("ERROR: Worker dependencies timed out.")
sys.exit(1)
EOF

if command -v clamd >/dev/null 2>&1; then
    echo "==> Starting ClamAV daemon on 127.0.0.1:3310..."
    clamd || echo "WARN: clamd failed to start."
    sleep 2
    python - << 'CLAM_EOF'
import socket, time
for _ in range(10):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(("127.0.0.1", 3310))
            s.sendall(b"zPING\0")
            resp = s.recv(1024).decode('utf-8', errors='replace').strip()
            if "PONG" in resp:
                print("ClamAV daemon verified and responsive on 127.0.0.1:3310!")
                break
    except Exception:
        time.sleep(1)
CLAM_EOF
fi

echo "==> Starting Celery worker process (concurrency: 2, pool: threads)..."
exec celery -A tribel_scholar worker --loglevel=info --concurrency=2 --pool=threads
