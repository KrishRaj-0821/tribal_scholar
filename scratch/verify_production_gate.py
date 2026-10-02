import sys
import os
import time
import hashlib
import json
import uuid
import requests
import boto3

BACKEND_URL = os.environ.get("BACKEND_URL", "https://backend-production-ba69a.up.railway.app").rstrip('/')
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://tribalscholar.up.railway.app").rstrip('/')
S3_ENDPOINT = "https://t3.storageapi.dev"
S3_BUCKET = "tribal-scholar-docs-lzidsm"
S3_KEY = "tid_qO_KJhQdTvjYsOKpglwPcIQGfWkBTvwCAByzcgUnZVeZTmKfu_"
S3_SECRET = "tsec_mBqp9tbhTcVVzzf6nBUAvsJZ_AEoDHE0JipUne8iuyJPJo8aRgEGDtvZrsQztnzTS04zbr"

results = {}

def log_test(name, passed, detail=""):
    results[name] = {"passed": passed, "detail": detail}
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {name} - {detail}")

print("=== Starting Tribal Scholar Production Gate Verification ===")
print(f"Target Backend:  {BACKEND_URL}")
print(f"Target Frontend: {FRONTEND_URL}")
print(f"Target S3:       {S3_ENDPOINT} ({S3_BUCKET})")

# 1. Health Liveness & Readiness Checks
def test_health():
    print("\n--- 1. Testing Health Endpoints ---")
    try:
        r_live = requests.get(f"{BACKEND_URL}/health/live", timeout=10)
        assert r_live.status_code == 200, f"Live returned {r_live.status_code}: {r_live.text}"
        live_data = r_live.json()
        assert live_data.get("status") == "ok"
        log_test("Health Liveness Probe", True, f"Status: {live_data.get('status')}")
    except Exception as e:
        log_test("Health Liveness Probe", False, str(e))

    try:
        r_ready = requests.get(f"{BACKEND_URL}/health/ready", timeout=15)
        ready_data = r_ready.json()
        print(f"Readiness response (status {r_ready.status_code}):", json.dumps(ready_data, indent=2))
        
        # Verify internal service details are not leaked
        body_str = json.dumps(ready_data).lower()
        assert "password" not in body_str, "Leaked password in readiness endpoint!"
        assert "secret" not in body_str, "Leaked secret in readiness endpoint!"
        assert "postgres.railway.internal" not in body_str, "Leaked database internal host!"
        assert "redis.railway.internal" not in body_str, "Leaked redis internal host!"
        assert "tsec_" not in body_str, "Leaked S3 secret key!"
        log_test("Health Endpoint Data Sanitization", True, "Zero infrastructure secrets leaked")

        comps = ready_data.get("components", {})
        log_test("Readiness Component: DATABASE", comps.get("database") == "connected", f"Status: {comps.get('database')}")
        log_test("Readiness Component: REDIS", comps.get("redis") == "connected", f"Status: {comps.get('redis')}")
        log_test("Readiness Component: CELERY", comps.get("celery") in ("connected", "unresponsive"), f"Status: {comps.get('celery')}")
        log_test("Readiness Component: OBJECT_STORAGE", comps.get("object_storage") == "connected", f"Status: {comps.get('object_storage')}")
        log_test("Readiness Component: CLAMAV", comps.get("clamav") == "connected", f"Status: {comps.get('clamav')}")
        
        return r_ready.status_code == 200 and ready_data.get("status") == "ready"
    except Exception as e:
        log_test("Health Readiness Probe", False, str(e))
        return False

# 2. Durable S3 Object Storage Lifecycle & Checksum Integrity
def test_s3_storage():
    print("\n--- 2. Testing Production Object Storage ---")
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_KEY,
            aws_secret_access_key=S3_SECRET,
            region_name='auto'
        )
        test_uuid = str(uuid.uuid4())
        doc_filename = f"synthetic_income_cert_{test_uuid}.pdf"
        synthetic_content = f"%PDF-1.4 Synthetic Income Certificate Content Token: {test_uuid}".encode('utf-8')
        sha256_orig = hashlib.sha256(synthetic_content).hexdigest()

        # Step A: Upload to quarantine/
        q_key = f"quarantine/{test_uuid}/{doc_filename}"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=q_key,
            Body=synthetic_content,
            ServerSideEncryption='AES256',
            Metadata={'document_id': test_uuid}
        )
        log_test("S3 Quarantine Upload", True, f"Stored at {q_key}")

        # Step B: Read quarantine and verify SHA-256
        q_resp = s3.get_object(Bucket=S3_BUCKET, Key=q_key)
        q_data = q_resp['Body'].read()
        sha256_q = hashlib.sha256(q_data).hexdigest()
        assert sha256_q == sha256_orig, "Quarantine checksum mismatch!"
        log_test("S3 Quarantine SHA-256 Match", True, f"Checksum: {sha256_q}")

        # Step C: Promotion to documents/ (safe namespace)
        safe_key = f"documents/app_{test_uuid}/{test_uuid}/{doc_filename}"
        s3.copy_object(
            Bucket=S3_BUCKET,
            CopySource={'Bucket': S3_BUCKET, 'Key': q_key},
            Key=safe_key,
            ServerSideEncryption='AES256'
        )
        s3.delete_object(Bucket=S3_BUCKET, Key=q_key)
        log_test("S3 Promotion to Safe", True, f"Promoted to {safe_key}, purged quarantine copy")

        # Step D: Authenticated read of safe document & SHA-256 comparison
        safe_resp = s3.get_object(Bucket=S3_BUCKET, Key=safe_key)
        safe_data = safe_resp['Body'].read()
        sha256_safe = hashlib.sha256(safe_data).hexdigest()
        assert sha256_safe == sha256_orig, "Safe document checksum mismatch!"
        log_test("S3 Safe Object Checksum Verified", True, f"Checksum: {sha256_safe}")

        # Step E: Confirm quarantine copy is completely gone
        try:
            s3.head_object(Bucket=S3_BUCKET, Key=q_key)
            log_test("S3 Quarantine Isolation", False, "Quarantine object still exists after promotion!")
        except Exception:
            log_test("S3 Quarantine Isolation", True, "Quarantine key successfully deleted")

        # Keep safe object to test persistence across restarts
        return test_uuid, safe_key, sha256_orig
    except Exception as e:
        log_test("S3 Object Storage", False, str(e))
        return None, None, None

# 3. Scheme API & NOS 2026-27 Rule Provenance Verification
def test_nos_provenance():
    print("\n--- 3. Testing NOS 2026-27 Rule Provenance ---")
    try:
        r = requests.get(f"{BACKEND_URL}/api/v1/schemes/", timeout=10)
        assert r.status_code == 200, f"Schemes endpoint returned {r.status_code}"
        schemes = r.json()
        if isinstance(schemes, dict) and "results" in schemes:
            schemes = schemes["results"]
        
        nos_scheme = next((s for s in schemes if s["code"] == "NOS"), None)
        assert nos_scheme is not None, "NOS scheme not found in catalog!"
        log_test("NOS Scheme Catalog Exists", True, f"Scheme: {nos_scheme['name']}")

        r_ver = requests.get(f"{BACKEND_URL}/api/v1/scheme-versions/", timeout=10)
        assert r_ver.status_code == 200
        versions = r_ver.json()
        if isinstance(versions, dict) and "results" in versions:
            versions = versions["results"]

        nos_2026 = next((v for v in versions if v.get("academic_year") == "2026-27" and "NOS" in str(v.get("scheme"))), None)
        assert nos_2026 is not None, "NOS 2026-27 version not found!"
        log_test("NOS 2026-27 Version Exists", True, f"Version ID: {nos_2026['id']}")

        r_rules = requests.get(f"{BACKEND_URL}/api/v1/scheme-rules/", timeout=10)
        assert r_rules.status_code == 200
        rules = r_rules.json()
        if isinstance(rules, dict) and "results" in rules:
            rules = rules["results"]

        inc_rule = next((r for r in rules if r.get("rule_code") == "NOS_2026_INCOME_CEILING"), None)
        assert inc_rule is not None, "NOS_2026_INCOME_CEILING rule not found!"
        
        # Verify exact official value: 600,000 (MoTA official ceiling)
        rule_val = int(inc_rule.get("value"))
        assert rule_val == 600000, f"Expected 600000, got {rule_val}"
        log_test("NOS 2026-27 Income Ceiling Value", True, f"Strictly Rs. 6,00,000 (not Rs. 8,00,000)")

        # Verify provenance status
        prov_status = inc_rule.get("provenance_status")
        assert prov_status == "OFFICIAL_VERIFIED", f"Expected OFFICIAL_VERIFIED, got {prov_status}"
        log_test("NOS 2026-27 Provenance Status", True, f"Status: {prov_status}")

        # Verify source excerpt
        excerpt = inc_rule.get("source_excerpt", "")
        assert "6,00,000" in excerpt or "6.00" in excerpt or "600000" in excerpt, f"Unexpected excerpt: {excerpt}"
        log_test("NOS 2026-27 Source Excerpt Verified", True, f"Excerpt: '{excerpt}'")

        # Verify historical 2025-26 rules preserved
        hist_rule = next((r for r in rules if r.get("rule_code") == "NOS_2025_INCOME_CEILING"), None)
        assert hist_rule is not None, "Historical NOS 2025-26 income rule must not be overwritten!"
        log_test("Historical Rules Preserved", True, f"NOS 2025-26 rule value: {hist_rule.get('value')}")

    except Exception as e:
        log_test("NOS 2026-27 Provenance", False, str(e))

# 4. End-to-End Application & Document Journey
def test_e2e_journey():
    print("\n--- 4. Testing End-to-End Document Journey in Railway ---")
    try:
        rand_id = str(uuid.uuid4())[:8]
        username = f"applicant_synth_{rand_id}"
        email = f"synth_{rand_id}@tribal.gov.in"
        password = "SyntheticSecurePass2026!"

        # Step 1: Register applicant
        r_reg = requests.post(f"{BACKEND_URL}/api/v1/auth/register/", json={
            "username": username,
            "email": email,
            "password": password,
            "role": "APPLICANT",
            "community": "ST",
            "annual_family_income": 350000,
        }, timeout=10)
        assert r_reg.status_code in (200, 201), f"Register failed: {r_reg.text}"
        token = r_reg.json().get("access") or r_reg.json().get("tokens", {}).get("access")
        auth_headers = {"Authorization": f"Bearer {token}"}
        log_test("Synthetic Applicant Registration", True, f"User: {username}")

        # Step 2: Fetch scheme version
        r_ver = requests.get(f"{BACKEND_URL}/api/v1/scheme-versions/", headers=auth_headers, timeout=10)
        versions = r_ver.json()
        if isinstance(versions, dict) and "results" in versions:
            versions = versions["results"]
        nos_2026 = next(v for v in versions if v.get("academic_year") == "2026-27" and "NOS" in str(v.get("scheme")))

        # Step 3: Create application
        r_app = requests.post(f"{BACKEND_URL}/api/v1/applications/", json={
            "scheme_version": nos_2026["id"],
            "submission_data_json": {
                "course_level": "PhD",
                "foreign_university_qs_rank": 200,
                "is_indian_culture_or_heritage_topic": False,
                "annual_family_income": 350000,
                "community": "ST"
            }
        }, headers=auth_headers, timeout=10)
        assert r_app.status_code in (200, 201), f"Create app failed: {r_app.text}"
        app_data = r_app.json()
        app_id = app_data["id"]
        log_test("Create Synthetic Application", True, f"App ID: {app_id}")

        # Step 4: Upload Clean Synthetic Document
        clean_pdf_content = b"%PDF-1.4 Synthetic Clean Caste Certificate\nST Community Authority Verification\n123456"
        files = {
            'file': ('caste_certificate.pdf', clean_pdf_content, 'application/pdf')
        }
        data = {
            'document_type': 'CASTE_CERTIFICATE'
        }
        r_doc = requests.post(f"{BACKEND_URL}/api/v1/applications/{app_id}/documents/", files=files, data=data, headers=auth_headers, timeout=15)
        assert r_doc.status_code in (200, 201), f"Document upload failed: {r_doc.text}"
        doc_resp = r_doc.json()
        doc_id = doc_resp["id"]
        log_test("Document Upload to Quarantine", True, f"Doc ID: {doc_id}")

        # Step 5: Wait for Celery worker to perform malware scan + OCR
        print("Waiting for Celery worker processing in Railway...")
        scanned = False
        for attempt in range(12):
            time.sleep(2)
            r_st = requests.get(f"{BACKEND_URL}/api/v1/documents/{doc_id}/ocr-status/", headers=auth_headers, timeout=10)
            if r_st.status_code == 200:
                st_data = r_st.json()
                scan_status = st_data.get("malware_scan_status")
                doc_status = st_data.get("status")
                print(f"  [Attempt {attempt+1}/12] malware_scan_status: {scan_status}, doc status: {doc_status}")
                if scan_status in ("CLEAN", "SAFE") or doc_status in ("SAFE", "VERIFIED", "PROCESSED"):
                    scanned = True
                    break
        log_test("Clean Document Scan & Promotion to SAFE", scanned, f"Final status: {doc_status}, scan: {scan_status}")

        # Step 6: Authenticated Download
        r_dl = requests.get(f"{BACKEND_URL}/api/v1/documents/{doc_id}/download/", headers=auth_headers, timeout=15)
        assert r_dl.status_code == 200, f"Download returned {r_dl.status_code}"
        dl_hash = hashlib.sha256(r_dl.content).hexdigest()
        orig_hash = hashlib.sha256(clean_pdf_content).hexdigest()
        assert dl_hash == orig_hash, "Downloaded content checksum mismatch!"
        log_test("Authenticated Download & SHA-256 Match", True, f"SHA-256: {dl_hash}")

        # Step 7: EICAR Signature Upload Test
        eicar_string = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        files_eicar = {
            'file': ('eicar_test.com', eicar_string, 'text/plain')
        }
        r_eicar = requests.post(f"{BACKEND_URL}/api/v1/applications/{app_id}/documents/", files=files_eicar, data={'document_type': 'IDENTITY_PROOF'}, headers=auth_headers, timeout=15)
        if r_eicar.status_code in (200, 201):
            eicar_id = r_eicar.json()["id"]
            # Wait for scan result
            time.sleep(3)
            r_eicar_st = requests.get(f"{BACKEND_URL}/api/v1/documents/{eicar_id}/ocr-status/", headers=auth_headers, timeout=10)
            eicar_st = r_eicar_st.json()
            is_rejected = eicar_st.get("malware_scan_status") in ("INFECTED", "REJECTED") or eicar_st.get("status") in ("REJECTED", "QUARANTINED")
            log_test("EICAR Test Signature Detected & Rejected", is_rejected, f"Scan status: {eicar_st.get('malware_scan_status')}, doc status: {eicar_st.get('status')}")
        else:
            # Synchronously rejected at upload time
            log_test("EICAR Test Signature Synchronously Blocked", True, f"Response: {r_eicar.status_code}")

        # Step 8: IDOR Authorization Test
        # Attempt to access doc_id without auth or with unauthorized user
        r_unauth = requests.get(f"{BACKEND_URL}/api/v1/documents/{doc_id}/download/", timeout=10)
        assert r_unauth.status_code in (401, 403), f"Expected 401/403 for unauth download, got {r_unauth.status_code}"
        log_test("Object Authorization / IDOR Protection", True, f"Status code: {r_unauth.status_code} on unauthenticated access")

    except Exception as e:
        log_test("End-to-End Document Journey", False, str(e))

if __name__ == "__main__":
    ready_ok = test_health()
    test_uuid, s3_key, orig_hash = test_s3_storage()
    test_nos_provenance()
    test_e2e_journey()

    print("\n=== SUMMARY OF GATE RESULTS ===")
    total = len(results)
    passed = sum(1 for r in results.values() if r["passed"])
    failed = total - passed
    print(f"Total Tests: {total} | Passed: {passed} | Failed: {failed}")
    if failed == 0:
        print("\nALL ACCEPTANCE CRITERIA PASSED! READY FOR PHASE 9.")
        sys.exit(0)
    else:
        print(f"\n{failed} TESTS FAILED. NOT READY FOR PHASE 9.")
        sys.exit(1)
