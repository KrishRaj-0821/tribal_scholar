import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole


def pytest_ignore_collect(collection_path, config):
    """
    If the file is the top-level test_concurrency_stress.py forwarder,
    only collect it if explicitly passed on the command line.
    Prevents running concurrency tests twice during full suite execution.
    """
    path_str = str(collection_path).replace("\\", "/")
    if path_str.endswith("backend/tests/test_concurrency_stress.py") or path_str.endswith("tests/test_concurrency_stress.py"):
        if not any("tests/test_concurrency_stress.py" in arg.replace("\\", "/") for arg in config.args):
            return True
    return False


def pytest_report_header(config):
    """
    Print database identity at test start.
    Reports backend, database, host, port, and PostgreSQL version without exposing passwords.
    """
    from django.db import connection
    vendor = connection.vendor
    settings_dict = connection.settings_dict
    db_name = settings_dict.get('NAME', '')
    db_host = settings_dict.get('HOST', '127.0.0.1')
    db_port = settings_dict.get('PORT', '5432')

    try:
        import psycopg
        password = settings_dict.get('PASSWORD', '')
        user = settings_dict.get('USER', 'postgres')
        with psycopg.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=db_host,
            port=db_port,
            connect_timeout=3
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                row = cur.fetchone()
                raw_version = row[0] if row else "Unknown"
                version_str = raw_version.split(',')[0]
    except Exception as e:
        version_str = f"PostgreSQL (connection error: {e})"

    return [
        "=" * 50,
        "DATABASE CHECK",
        f"Backend: {vendor}",
        f"Database: {db_name}",
        f"Host: {db_host}",
        f"Port: {db_port}",
        f"Version: {version_str}",
        "=" * 50,
    ]


@pytest.fixture(scope="session", autouse=True)
def assert_postgresql_database(django_db_setup, django_db_blocker):
    """
    Session-level database assertion.
    Guarantees the test suite runs strictly on PostgreSQL.
    Fails fast with AssertionError if vendor != 'postgresql'.
    """
    with django_db_blocker.unblock():
        from django.db import connection
        vendor = connection.vendor
        if vendor != "postgresql":
            raise AssertionError(
                f"PostgreSQL is required for the integrity test suite. "
                f"Current database vendor is '{vendor}'. Set DATABASE_ENGINE=postgresql."
            )


@pytest.fixture(autouse=True)
def check_requires_postgresql_marker(request):
    """
    Enforces that any test marked with 'requires_postgresql' fails immediately
    with an assertion error if the active backend is not PostgreSQL. Never skips.
    """
    marker = request.node.get_closest_marker("requires_postgresql")
    if marker:
        from django.db import connection
        assert connection.vendor == "postgresql", "Concurrency tests require PostgreSQL."


@pytest.fixture(autouse=True)
def check_redis_availability_for_integration(request):
    """
    Guarantees that integration tests use a real Redis server.
    Fails fast with an AssertionError if Redis is unavailable.
    Does NOT skip.
    """
    node_path = str(request.node.fspath).replace("\\", "/")
    if "tests/integration" in node_path or request.node.get_closest_marker("requires_redis"):
        import redis
        from django.conf import settings
        redis_url = getattr(settings, 'REDIS_URL', None)
        if redis_url:
            r = redis.from_url(redis_url, socket_timeout=2)
        else:
            host = getattr(settings, 'REDIS_HOST', '127.0.0.1')
            port = int(getattr(settings, 'REDIS_PORT', 6379))
            db = int(getattr(settings, 'REDIS_DB', 0))
            r = redis.Redis(host=host, port=port, db=db, socket_timeout=2)
        try:
            if not r.ping():
                raise AssertionError("Redis ping returned False")
        except Exception as exc:
            raise AssertionError(
                f"INTEGRATION GATE FAILURE: Real Redis is required for integration tests "
                f"at {host}:{port} db={db}, but connection failed ({exc}). "
                f"No silent fallback allowed. DO NOT SKIP."
            )


@pytest.fixture
def require_clamav():
    """
    Enforces that the ClamAV daemon is running and reachable via TCP socket.
    Fails immediately if unavailable. Does NOT skip.
    """
    import socket
    from django.conf import settings
    host = getattr(settings, 'CLAMAV_HOST', '127.0.0.1')
    port = int(getattr(settings, 'CLAMAV_PORT', 3310))
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3.0)
            s.connect((host, port))
            s.sendall(b"zPING\0")
            resp = s.recv(1024)
            if b"PONG" not in resp:
                raise AssertionError(f"Unexpected ClamAV response: {resp}")
    except Exception as exc:
        raise AssertionError(
            f"CLAMAV INTEGRATION GATE FAILURE: Real ClamAV daemon is required at {host}:{port} "
            f"but is unreachable ({exc}). DO NOT SKIP."
        )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='mota_admin',
        email='admin@tribal.gov.in',
        password='AdminPassword123!',
        role=UserRole.ADMIN,
        is_staff=True
    )
    return user


@pytest.fixture
def applicant_user(db):
    user = User.objects.create_user(
        username='tribal_scholar_applicant',
        email='student@example.org',
        password='StudentPassword123!',
        role=UserRole.APPLICANT
    )
    return user


@pytest.fixture
def scrutiny_officer(db):
    user = User.objects.create_user(
        username='scrutiny_officer_01',
        email='officer@tribal.gov.in',
        password='OfficerPassword123!',
        role=UserRole.SCRUTINY_OFFICER,
        is_staff=True
    )
    return user


@pytest.fixture
def seeded_db(db):
    from django.core.management import call_command
    call_command('seed_schemes')
