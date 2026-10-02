#!/bin/sh
set -e

echo "=== [Railway Deploy] Starting Tribal Scholar Celery Worker ==="

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

echo "==> Starting Celery worker process (concurrency: 2)..."
exec celery -A tribel_scholar worker --loglevel=info --concurrency=2
