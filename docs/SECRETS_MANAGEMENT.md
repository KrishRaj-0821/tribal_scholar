# Secrets Management & Credential Policy

This document establishes the mandatory security and secrets management protocols for the **Tribel_Scholor** repository (SIH Problem Statement 26239).

---

## 1. Core Principles & Non-Negotiable Rules

1. **No Plaintext Production Credentials in Repository:**
   - Production secrets, master database credentials, TLS certificates, and API tokens must never be hardcoded or checked into Git.
   - All runtime environments must inject secrets via encrypted secret managers (e.g., HashiCorp Vault, AWS Secrets Manager, Kubernetes Secrets) or isolated environment variables.

2. **No Passwords in Tests:**
   - Test suites must use transient mocked users or dedicated test credentials provided explicitly via test fixtures and environment configuration.
   - Tests must never attempt to connect to production databases or store static credentials.

3. **No Passwords or Secrets in Logs:**
   - Application loggers, Celery task logs, and HTTP request logs must filter and redact all sensitive keys (`password`, `access_token`, `refresh_token`, `api_key`, `secret`, `token`, `authorization`, `cookie`, `document_content`).
   - Logging formatters must enforce automatic redaction before emitting log records to console or storage.

4. **Zero Tolerance for Password Enumeration or Brute-Forcing:**
   - Developers and automated agents must **never** write scripts or execute commands that attempt to enumerate passwords, guess database credentials, or brute-force local or remote authentication systems.
   - Explicit developer-provided environment variables or unauthenticated local test configurations (e.g., trust authentication for isolated local test databases) must be utilized.

5. **No Reading Credential Stores:**
   - Code and automated tools must never inspect local password stores, pgAdmin `.pgpass` files, operating system credential lockers, browser secret caches, or command-line shell histories.

6. **No Committing `.env` Files:**
   - `.env` and all `.env.*` variants (except `.env.example`) are strictly ignored via `.gitignore`.
   - `.env.example` must contain **placeholders only** (`POSTGRES_DB=`, `POSTGRES_PASSWORD=`), with zero real secrets or default credentials committed.

7. **Development Credentials Must Be Rotatable:**
   - All credentials used in staging and development must support immediate rotation without application redeployment or code modifications.

---

## 2. Environment Variable Configuration Standard

The application standardizes on the following environment variables:

| Variable | Description | Default / Requirement |
| :--- | :--- | :--- |
| `POSTGRES_DB` / `DB_NAME` | Database name | Mandatory in production |
| `POSTGRES_USER` / `DB_USER` | Database role | Mandatory in production |
| `POSTGRES_PASSWORD` / `DB_PASSWORD` | Database user password | Mandatory in production (placeholder only in repo) |
| `POSTGRES_HOST` / `DB_HOST` | Database host | `127.0.0.1` |
| `POSTGRES_PORT` / `DB_PORT` | Database port | `5432` (or `5433` for local isolated test instance) |
| `DATABASE_ENGINE` | Database engine selection | `postgresql` |
| `DJANGO_SECRET_KEY` | Django cryptographic signing key | Injected at runtime |
| `REDIS_URL` | Redis broker and cache endpoint | Injected at runtime |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Object storage credentials | Injected at runtime |

---

## 3. Sensitive Data Redaction in Logging

The Django application implements a centralized log filter (`SensitiveDataSanitizingFilter`) that intercepts and masks:
- User passwords and hashes
- Bearer tokens, JWT tokens, session IDs
- Applicant personally identifiable information (Aadhaar number, bank account details)
- Document binaries and raw extraction buffers
- Database connection strings and connection URLs

---

## 4. Secret Auditing & Repository Hygiene

Routine pre-commit hooks and CI pipelines execute automated pattern scanning for:
- `password\s*=`
- `PASSWORD\s*=`
- `secret\s*=`
- `api_key\s*=`
- `token\s*=`
- `credential\s*=`

Any match on tracked source files halts the pipeline and requires immediate credential revocation and file scrubbing.
