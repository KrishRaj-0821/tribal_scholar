#!/bin/sh
set -e

echo "=== [Railway Deploy] Starting Tribal Scholar Celery Worker ==="

export FLAGS_enable_pir_api=0
export FLAGS_use_mkldnn=0
export PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export FLAGS_allocator_strategy=naive_best_fit
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

WORKER_ROLE="${WORKER_ROLE:-all}"
echo "==> Worker operating mode: ${WORKER_ROLE}"

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

CLAMAV_HOST="${CLAMAV_HOST:-127.0.0.1}"
if [ "$WORKER_ROLE" = "ocr" ]; then
    echo "==> OCR Worker mode: ClamAV daemon disabled in this container to prevent memory contention."
elif [ "$CLAMAV_HOST" != "127.0.0.1" ]; then
    echo "==> Remote ClamAV host configured (${CLAMAV_HOST}:${CLAMAV_PORT:-3310}). Skipping local clamd startup."
elif command -v clamd >/dev/null 2>&1; then
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

if [ "$WORKER_ROLE" = "ocr" ]; then
    echo "==> Starting dedicated OCR Celery worker process (queues: ocr, memory recycling: 850MB)..."
    exec celery -A tribel_scholar worker --loglevel=info --queues=ocr --concurrency=1 --max-memory-per-child=850000
elif [ "$WORKER_ROLE" = "scanner" ]; then
    echo "==> Starting dedicated Malware Scanner Celery worker process (queues: security_scan,notifications,default, memory recycling: 350MB)..."
    exec celery -A tribel_scholar worker --loglevel=info --queues=security_scan,notifications,default --concurrency=1 --max-memory-per-child=350000
else
    echo "==> Starting unified Celery worker process (queues: default,security_scan,ocr,notifications)..."
    exec celery -A tribel_scholar worker --loglevel=info --queues=default,security_scan,ocr,notifications --concurrency=1 --max-memory-per-child=850000
fi
