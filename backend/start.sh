#!/bin/sh
set -e

echo "=== [Railway Deploy] Starting Tribal Scholar Backend ==="

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

# 5. Start Gunicorn production WSGI server
echo "==> Starting Gunicorn on port ${PORT:-8000}..."
exec gunicorn tribel_scholar.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${GUNICORN_WORKERS:-2} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile -
