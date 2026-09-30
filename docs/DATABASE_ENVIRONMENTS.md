# Database Environments & Transactional Integrity Architecture

## 1. Overview & Architectural Principle

Tribel_Scholar provides statutory scholarship management for the Ministry of Tribal Affairs (MoTA). The platform enforces strict ACID guarantees, row-level locking (`SELECT FOR UPDATE`), multi-version concurrency control (MVCC), immutable snapshot auditing, and idempotency replay protection.

To ensure transactional correctness, **silent fallbacks to SQLite are strictly prohibited**. The project enforces explicit database modes and requires PostgreSQL for the official test suite and all integrity gates.

---

## 2. Explicit Database Modes

The application recognizes two explicit database modes via `DATABASE_ENGINE`:

| Mode | Environment Variable | Usage & Permissions |
| :--- | :--- | :--- |
| **PostgreSQL** (Default) | `DATABASE_ENGINE=postgresql` | **Mandatory** for Official Test Suite, CI, Integration Tests, Concurrency Tests, and Production. |
| **SQLite** (Restricted) | `DATABASE_ENGINE=sqlite` | Permitted **only** when explicitly requested for lightweight, isolated developer experiments that do not touch transactions or concurrency. |

### Fail-Fast Invariant
- If no explicit mode is supplied during test suite execution, Django fails fast with:
  ```
  django.core.exceptions.ImproperlyConfigured: PostgreSQL is required for the integrity test suite. Set DATABASE_ENGINE=postgresql.
  ```
- If PostgreSQL configuration is incomplete (e.g. `POSTGRES_DB` missing), the system fails immediately rather than falling back to SQLite.
- SQLite is **never inferred** as a silent fallback.

---

## 3. Database Environments

### A. Local PostgreSQL (Host Native)
* **Target Scenario**: Direct development and local test execution on a developer workstation with a native PostgreSQL service.
* **Service Port**: `5432` (Standard PostgreSQL port).
* **Host Address**: `127.0.0.1` or `localhost`.
* **Configuration**:
  ```env
  DATABASE_ENGINE=postgresql
  POSTGRES_DB=tribal_scholar
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=<workstation_password>
  POSTGRES_HOST=127.0.0.1
  POSTGRES_PORT=5432
  ```
* **Status Verification**:
  ```powershell
  python manage.py check_database
  ```

### B. Docker PostgreSQL (Containerized)
* **Target Scenario**: Containerized multi-service deployment via `docker-compose.yml`.
* **Container Service**: `db` running `postgres:16-alpine`.
* **Port Mapping**:
  - If the host workstation does **not** have a local PostgreSQL service running, port `5432:5432` is mapped:
    ```env
    POSTGRES_PORT=5432
    ```
  - If the host workstation **already** runs a native PostgreSQL instance on `5432`, Docker host port should map `5433:5432` to avoid collisions:
    ```env
    POSTGRES_PORT=5433
    ```
* **Internal Network**: Backend containers within the Docker network communicate directly with `POSTGRES_HOST=db` on port `5432`.
* **Configuration (`docker-compose.yml`)**:
  ```yaml
  services:
    db:
      image: postgres:16-alpine
      container_name: tribal_scholar_db
      environment:
        POSTGRES_DB: ${POSTGRES_DB:-tribal_scholar}
        POSTGRES_USER: ${POSTGRES_USER:-postgres}
        POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}
      ports:
        - "${POSTGRES_PORT:-5432}:5432"
      volumes:
        - pgdata:/var/lib/postgresql/data
  ```

### C. Test PostgreSQL (Integrity Gate & Pytest)
* **Target Scenario**: Automated test suite execution (`pytest`) and CI/CD validation gates.
* **Database Name**: Dedicated test database (e.g., `test_tribal_scholar`), managed and isolated by Django's test runner.
* **Isolation Guarantees**:
  - Multi-threaded tests use `django.db.connections.close_all()` per worker to prevent cross-thread descriptor leaks.
  - Transactions use `transaction=True` on `@pytest.mark.django_db` to test atomic rollbacks and savepoints.
  - Snapshot tables (`ApplicationSubmissionSnapshot`, `EligibilityInputSnapshot`, `EligibilityEvaluation`) strictly prohibit mutations and bulk deletions via model-level and QuerySet overrides.
* **Pre-Flight Verification**:
  Every test run automatically asserts:
  ```python
  assert connection.vendor == "postgresql"
  ```
  and outputs the database runtime identity banner:
  ```
  ==================================================
  DATABASE CHECK
  Backend: postgresql
  Database: test_tribal_scholar
  Host: 127.0.0.1
  Port: 5432
  Version: PostgreSQL 18.x
  ==================================================
  ```

---

## 4. SQLite Policy

SQLite is strictly quarantined.

### Permitted Scenarios:
1. Isolated unit tests that do not involve the Django ORM, transactions, locking, or concurrency (e.g. pure regex validators, logging filters, formatting algorithms).
2. Explicitly requested single-table developer scratchpad tests using `DATABASE_ENGINE=sqlite`.

### Forbidden Scenarios:
1. Concurrency stress tests (`tests/integration/test_concurrency_stress.py`).
2. Application submission transaction tests.
3. Idempotency race tests (replay defense with 20 parallel threads).
4. Audit log append-only immutability tests.
5. Snapshot immutability validation tests.
6. CI integrity gates and final release sign-offs.

Under no circumstances may a test skip or pass on SQLite and be counted towards official platform compliance.

---

## 5. Verification Commands

Verify connectivity and scheme integrity:
```bash
# 1. Verify PostgreSQL connection and backend identity
python manage.py check_database

# 2. Validate statutory scheme configuration
python manage.py validate_schemes

# 3. Execute unit and integration tests
python -m pytest -v

# 4. Execute dedicated concurrency stress suite
python -m pytest -v tests/test_concurrency_stress.py
```
