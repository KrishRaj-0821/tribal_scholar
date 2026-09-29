# Source Provenance & Document Registry Specification
## MoTA SIH Problem Statement 26239

---

### 1. The Principle of Source Provenance
In public administration, any administrative requirement imposed on citizens must have legal authority rooted in an official publication (act, rules, gazette notification, scheme guideline, or sanctioned advertisement).

In the **Tribal Scholar Management System**, **every configuration entity must demonstrate proof of origin**. No officer, administrator, or AI agent can introduce a rule or update an eligible institute list without registering the corresponding official document.

---

### 2. Official Source Hierarchy & Priority
The source extraction registry admits **only** official Government of India publications following strict priority tiers:

* **TIER 1 (Primary Government Portal)**:
  * Official Ministry Portal: [https://tribal.nic.in/](https://tribal.nic.in/)
* **TIER 2 (Official MoTA Sub-Portals & Designated National Systems)**:
  * Fellowship Application Portal: [https://fellowship.tribal.gov.in/](https://fellowship.tribal.gov.in/)
  * Overseas Scholarship Portal: [https://overseas.tribal.gov.in/](https://overseas.tribal.gov.in/)
  * National Scholarship Portal (NSP): [https://scholarships.gov.in/](https://scholarships.gov.in/) (where MoTA identifies it as the official intake portal)
  * Direct Benefit Transfer Portal: [https://dbttribal.gov.in/](https://dbttribal.gov.in/)

> [!CAUTION]
> **Strict Prohibition on Unofficial Sources**:
> Blogs, coaching websites, news articles, commercial study portals, or unofficial internet summaries are **strictly prohibited** as authorities. Zero policy rules or reference items may cite secondary or unauthenticated web resources.

---

### 3. The SourceDocument Entity
The `SourceDocument` registry acts as the authoritative single source of truth for all scheme literature:

```python
class SourceDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, choices=SourceType.choices)
    source_url = models.CharField(max_length=500, blank=True)
    scheme = models.ForeignKey('schemes.Scheme', on_delete=models.SET_NULL, null=True, blank=True)
    academic_year = models.CharField(max_length=20)
    document_date = models.DateField(null=True, blank=True)
    retrieved_at = models.DateTimeField(default=timezone.now)
    checksum = models.CharField(max_length=64, help_text="SHA-256 hash of original binary/PDF")
    content_hash = models.CharField(max_length=64, help_text="SHA-256 hash of extracted text/table")
    status = models.CharField(max_length=30, default="VERIFIED")
    supersedes_source = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
```

---

### 3. Supported Source Types
1. **GUIDELINE**: Comprehensive operational guidelines released by MoTA.
2. **AMENDMENT**: Formal notification or circular modifying specific provisions of earlier guidelines.
3. **ADVERTISEMENT**: Public call for applications published in national dailies or MoTA portal.
4. **FAQ**: Official clarifications published to resolve common applicant queries.
5. **INSTRUCTION_MANUAL**: User guide for applicants or verifying authorities.
6. **SELECTION_CRITERIA**: Scoring rubric or committee parameters.
7. **INSTITUTE_LIST**: Official gazetted roster of empanelled premier institutions.
8. **RESULT**: Official list of shortlisted, selected, or waitlisted beneficiaries.
9. **OFFICIAL_WEBPAGE**: Archived snapshot of authentic public portals (e.g., tribal.nic.in, overseas.tribal.gov.in).
10. **DATASET**: Reference code lists (e.g., AISHE codes, state/district census codes).

---

### 4. Cryptographic Provenance & Lineage
* **Binary Checksum (`checksum`)**: SHA-256 hash of the uploaded authentic PDF/document to prevent silent bitrot or unauthorized replacement.
* **Content Hash (`content_hash`)**: SHA-256 hash of the extracted canonical text/data structure to guarantee reproducible rule interpretation.
* **Lineage & Supersession (`supersedes_source`)**: When an amendment is notified (e.g., modifying the NOS income ceiling or course eligibility), the new `SourceDocument` explicitly links to the prior guideline via `supersedes_source`, establishing an unbroken chain of custody.

---

### 5. Integrity Guarantees & Enforcement
The system enforces provenance through automated validation:
* **Orphan Rule Prohibition**: A `SchemeRule` without an associated `SourceDocument` cannot be saved or validated.
* **Orphan Reference Item Prohibition**: A `ReferenceSetItem` without an associated `SourceDocument` cannot be saved or validated.
* **Tamper-Evident Logs**: Updates to document provenance trigger automated `AuditLog` events.
