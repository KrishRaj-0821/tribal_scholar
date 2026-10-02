#!/bin/sh
set -e

echo "=== [Railway Deploy] Starting Tribal Scholar Backend ==="

export FLAGS_enable_pir_api=0
export FLAGS_use_mkldnn=0
export PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=2

# 0. Wait for database connection to be ready
echo "==> Verifying database connection..."
python - << 'EOF'
import sys, time, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tribel_scholar.settings")
django.setup()
from django.db import connection

for attempt in range(1, 31):
    try:
        connection.ensure_connection()
        print("Database connection verified successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"[Attempt {attempt}/30] Database not ready yet: {e}")
        time.sleep(2)

print("ERROR: Database connection timed out after 60 seconds.")
sys.exit(1)
EOF

# 1. Apply database migrations
echo "==> Running database migrations..."
python manage.py migrate --noinput

# 2. Seed statutory schemes and reference datasets (idempotent)
echo "==> Seeding MoTA statutory schemes (NFST, TOP_CLASS, NOS)..."
python manage.py seed_schemes || echo "WARN: seed_schemes encountered a non-fatal warning."

# 3. Validate statutory scheme integrity and SHA-256 provenance
echo "==> Validating scheme statutory integrity..."
python manage.py validate_schemes || echo "WARN: validate_schemes encountered a non-fatal warning."

# 4. Collect static files for WhiteNoise
echo "==> Collecting static assets..."
python manage.py collectstatic --noinput

# 4.5. Start ClamAV daemon if available
if command -v clamd >/dev/null 2>&1; then
    echo "==> Starting ClamAV daemon on 127.0.0.1:3310..."
    clamd || echo "WARN: clamd failed to start."
fi

# 5. Start Gunicorn production WSGI server
echo "==> Starting Gunicorn on port ${PORT:-8000}..."
exec gunicorn tribel_scholar.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${GUNICORN_WORKERS:-2} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile -
