import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './context/AuthContext';
import { officerApi, fetchApi } from './services/api';
import { 
  FileText, CheckCircle, AlertTriangle, RefreshCw, Info,
  ShieldCheck, ArrowUpRight, HelpCircle, XCircle,
  RotateCcw, Clock, ArrowLeft, ChevronRight, UserCheck
} from 'lucide-react';

export interface VerificationWorkbenchProps {
  applicationId?: string;
  documentId?: string;
  queueItemId?: string;
  onBackToQueue?: () => void;
}

interface OCRBoundingBox {
  id: string;
  text: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
  language?: string;
  field_code?: string;
}

interface VerificationField {
  field_code: string;
  field_label: string;
  declared_value: any;
  ocr_value: any;
  verified_value: any;
  verification_status: 'PENDING' | 'IN_REVIEW' | 'VERIFIED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE' | 'ESCALATED' | 'CONFLICT';
  confidence: number;
  page_number?: number | null;
  bbox?: { x: number; y: number; width: number; height: number } | null;
  ocr_block_id?: string | null;
  has_conflict: boolean;
  trust_level?: string;
}

interface VerificationHistoryEvent {
  id: string;
  document_id?: string;
  audit_event_id: string;
  field_code: string;
  action: string;
  previous_value: any;
  verified_value: any;
  previous_trust_rank: number;
  verified_trust_rank: number;
  officer_name: string;
  officer_role?: string;
  verified_at: string;
  reason: string;
}

export default function VerificationWorkbench({
  applicationId,
  documentId,
  queueItemId: propQueueItemId,
  onBackToQueue
}: VerificationWorkbenchProps) {
  const { user: authUser } = useAuth();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Authoritative server-persisted state
  const [queueItem, setQueueItem] = useState<any | null>(null);
  const [applicationInfo, setApplicationInfo] = useState<any | null>(null);
  const [applicantInfo, setApplicantInfo] = useState<any | null>(null);
  const [documentInfo, setDocumentInfo] = useState<any | null>(null);
  const [targetDocId, setTargetDocId] = useState<string | null>(documentId || null);
  const [activeQueueItemId, setActiveQueueItemId] = useState<string | null>(propQueueItemId || null);

  const [fields, setFields] = useState<VerificationField[]>([]);
  const [history, setHistory] = useState<VerificationHistoryEvent[]>([]);
  const [boundingBoxes, setBoundingBoxes] = useState<OCRBoundingBox[]>([]);
  const [ocrFullText, setOcrFullText] = useState<string>('');
  const [eligibilityImpact, setEligibilityImpact] = useState<any | null>(null);
  const [isDocumentVerified, setIsDocumentVerified] = useState<boolean>(false);

  // UI state
  const [selectedFieldCode, setSelectedFieldCode] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activeTab, setActiveTab] = useState<'fields' | 'history' | 'eligibility'>('fields');

  // Load authoritative backend state
  const loadAuthoritativeState = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let resolvedQueueItemId = activeQueueItemId || propQueueItemId || null;
      let resolvedDocId = targetDocId || documentId || null;

      // 1. Resolve queue item if not explicitly supplied
      if (!resolvedQueueItemId) {
        const queueRes = await officerApi.getQueue();
        const rawItems = Array.isArray(queueRes) ? queueRes : (queueRes?.results || []);
        if (rawItems && rawItems.length > 0) {
          if (applicationId) {
            const match = rawItems.find((it: any) => 
              it.application === applicationId || 
              it.application_number === applicationId ||
              it.id === applicationId
            );
            if (match) {
              resolvedQueueItemId = match.id;
              if (match.document) resolvedDocId = match.document;
            } else {
              resolvedQueueItemId = rawItems[0].id;
              if (rawItems[0].document) resolvedDocId = rawItems[0].document;
            }
          } else {
            resolvedQueueItemId = rawItems[0].id;
            if (rawItems[0].document) resolvedDocId = rawItems[0].document;
          }
        }
      }

      setActiveQueueItemId(resolvedQueueItemId);

      // 2. Fetch authoritative queue detail if queue item exists
      if (resolvedQueueItemId) {
        const detail = await officerApi.getQueueItem(resolvedQueueItemId);
        if (detail) {
          setQueueItem(detail.queue_item || null);
          setApplicationInfo(detail.application || null);
          setApplicantInfo(detail.applicant || null);
          setDocumentInfo(detail.documents?.[0] || null);

          const docId = detail.target_document_id || detail.documents?.[0]?.id || resolvedDocId;
          resolvedDocId = docId;
          setTargetDocId(docId);

          setOcrFullText(detail.ocr_extracted_text || '');
          setFields(detail.extracted_fields || []);
          if (detail.extracted_fields && detail.extracted_fields.length > 0 && !selectedFieldCode) {
            setSelectedFieldCode(detail.extracted_fields[0].field_code);
          }

          if (detail.verification_history) {
            setHistory(detail.verification_history.map((h: any) => ({
              id: h.id,
              document_id: h.document_id,
              audit_event_id: h.audit_event_id || h.id,
              field_code: h.field_code || 'document_level',
              action: h.decision_action || h.verification_status || 'FIELD_VERIFIED',
              previous_value: h.previous_value,
              verified_value: h.verified_value,
              previous_trust_rank: h.previous_trust_rank || 20,
              verified_trust_rank: h.verified_trust_rank || 60,
              officer_name: h.officer_name || 'Officer',
              officer_role: h.officer_role || 'SCRUTINY_OFFICER',
              verified_at: h.verified_at || '',
              reason: h.reason || ''
            })));
          }

          setEligibilityImpact(detail.eligibility_impact || null);
        }
      }

      // 3. Fetch authoritative OCR evidence and bounding boxes for the document
      if (resolvedDocId) {
        try {
          const evidenceRes = await officerApi.getDocumentEvidence(resolvedDocId);
          if (evidenceRes) {
            setIsDocumentVerified(Boolean(evidenceRes.is_verified));
            if (!documentInfo && evidenceRes) {
              setDocumentInfo(evidenceRes);
            }
            if (evidenceRes.latest_ocr_text && !ocrFullText) {
              setOcrFullText(evidenceRes.latest_ocr_text);
            }
            const boxes: OCRBoundingBox[] = [];
            if (Array.isArray(evidenceRes.pages)) {
              for (const p of evidenceRes.pages) {
                if (Array.isArray(p.blocks)) {
                  for (const b of p.blocks) {
                    boxes.push({
                      id: String(b.id),
                      text: b.extracted_text || '',
                      confidence: b.confidence || 0.9,
                      x: b.bbox_x || 0,
                      y: b.bbox_y || 0,
                      width: b.bbox_width || 100,
                      height: b.bbox_height || 20,
                      language: b.language || 'hi',
                      field_code: b.field_code
                    });
                  }
                }
              }
            }
            setBoundingBoxes(boxes);
          }
        } catch {
          // Document evidence endpoint may 404 if OCR has not completed yet
        }

        // Fetch independent document verification history if not loaded from detail
        try {
          const histRes = await officerApi.getHistory(resolvedDocId);
          const histArr = Array.isArray(histRes) ? histRes : (histRes?.results || []);
          if (histArr && histArr.length > 0) {
            setHistory(histArr.map((h: any) => ({
              id: h.id,
              document_id: h.document,
              audit_event_id: h.audit_event_id || h.id,
              field_code: h.field_code || 'document_level',
              action: h.decision_action || h.verification_status || 'FIELD_VERIFIED',
              previous_value: h.previous_value_json,
              verified_value: h.verified_value_json,
              previous_trust_rank: h.previous_trust_rank || 20,
              verified_trust_rank: h.verified_trust_rank || 60,
              officer_name: h.officer_name || 'Officer',
              officer_role: h.officer_role || 'SCRUTINY_OFFICER',
              verified_at: h.verified_at || '',
              reason: h.reason || ''
            })));
          }
        } catch {
          // Optional fallback
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load authoritative verification dossier from backend.');
    } finally {
      setLoading(false);
    }
  }, [activeQueueItemId, propQueueItemId, targetDocId, documentId, applicationId, selectedFieldCode]);

  useEffect(() => {
    loadAuthoritativeState();
  }, [loadAuthoritativeState]);

  // Action 1: Authoritative Field Verification
  const handleVerify = async (fieldCode: string, value: any, reason?: string) => {
    if (!targetDocId) {
      alert("No active document available for field verification.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await officerApi.verifyField(targetDocId, {
        field_code: fieldCode,
        verified_value: value,
        reason: reason || 'Verified by officer based on scrutinised document evidence.'
      });
      await loadAuthoritativeState();
      setActionSuccessMsg(`Field '${fieldCode}' verified in PostgreSQL. Trust rank promoted to OFFICER_VERIFIED (Rank 60).`);
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || `Failed to verify field '${fieldCode}'.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Action 2: Authoritative Conflict Resolution
  const handleResolveConflict = async (
    fieldCode: string,
    decision: 'USE_APPLICANT_DECLARATION' | 'USE_DOCUMENT_VALUE' | 'NEEDS_MORE_EVIDENCE',
    reason?: string
  ) => {
    if (!activeQueueItemId) {
      alert("No active queue item available for conflict resolution.");
      return;
    }
    const field = fields.find(f => f.field_code === fieldCode);
    let chosenValue = field?.ocr_value;
    if (decision === 'USE_APPLICANT_DECLARATION') {
      chosenValue = field?.declared_value;
    } else if (decision === 'NEEDS_MORE_EVIDENCE') {
      chosenValue = null;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await officerApi.resolveConflict(
        activeQueueItemId,
        decision,
        reason || `Conflict resolved using ${decision}`,
        chosenValue
      );
      await loadAuthoritativeState();
      setActionSuccessMsg(`Conflict resolved (${decision}) and persisted in PostgreSQL. Verification record committed.`);
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || `Failed to resolve conflict for '${fieldCode}'.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Action 3: Field Rejection
  const handleRejectField = async (fieldCode: string) => {
    if (!targetDocId) return;
    const justification = prompt("Enter statutory justification for field rejection:");
    if (!justification || !justification.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchApi(`/api/v1/verification/documents/${targetDocId}/reject-field/`, {
        method: 'POST',
        body: JSON.stringify({ field_code: fieldCode, reason: justification })
      });
      await loadAuthoritativeState();
      setActionSuccessMsg(`Field '${fieldCode}' marked REJECTED in PostgreSQL.`);
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Field rejection failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Action 4: Needs Clarification / Deficiency
  const handleNeedsMoreEvidence = async (fieldCode: string) => {
    if (!activeQueueItemId) return;
    const deficiency = prompt("Enter specific deficiency / clarification required from applicant:");
    if (!deficiency || !deficiency.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchApi(`/api/v1/verification/queue/${activeQueueItemId}/needs-more-evidence/`, {
        method: 'POST',
        body: JSON.stringify({ reason: deficiency })
      });
      await loadAuthoritativeState();
      setActionSuccessMsg(`Deficiency raised for '${fieldCode}'. Status updated in PostgreSQL.`);
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to raise deficiency.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Action 5: Escalation
  const handleEscalate = async (fieldCode?: string) => {
    if (!activeQueueItemId) return;
    const note = prompt(`Enter justification for escalating ${fieldCode ? `'${fieldCode}'` : 'dossier'} to Verifying Authority:`);
    if (!note || !note.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchApi(`/api/v1/verification/queue/${activeQueueItemId}/escalate/`, {
        method: 'POST',
        body: JSON.stringify({ reason: note })
      });
      await loadAuthoritativeState();
      setActionSuccessMsg(`Dossier escalated to District Nodal Authority in PostgreSQL.`);
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to escalate item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Action 6: Document Verification (SAFE != VERIFIED)
  const handleVerifyDocument = async () => {
    if (!targetDocId) return;
    const reason = prompt("Enter verification remarks for accepting this document as VERIFIED_DOCUMENT (Rank 40):", "Original documentary evidence scrutinised; digital authenticity confirmed.");
    if (!reason || !reason.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await officerApi.verifyDocument(targetDocId, {
        decision_action: 'APPROVE',
        notes: reason
      });
      await loadAuthoritativeState();
      setActionSuccessMsg("Document marked as VERIFIED_DOCUMENT in PostgreSQL. Evidentiary trust rank upgraded to 40.");
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Document verification failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Action 7: Reopen Verification
  const handleReopen = async () => {
    if (!targetDocId) return;
    const reason = prompt("Enter statutory justification reason for reopening verification session:");
    if (!reason || !reason.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchApi(`/api/v1/verification/documents/${targetDocId}/reopen/`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason })
      });
      await loadAuthoritativeState();
      setActionSuccessMsg("Verification session reopened in PostgreSQL. Previous audit records preserved.");
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to reopen verification.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const officerDisplayName = authUser?.username ? `${authUser.username} (${authUser.role || 'SCRUTINY_OFFICER'})` : (queueItem?.assigned_to || 'Shri S. K. Mahapatra (SCRUTINY_OFFICER)');
  const appNumber = applicationInfo?.application_number || applicationId || 'N/A';
  const schemeName = applicationInfo?.scheme_name || applicationInfo?.scheme_code || 'Statutory Scholarship Scheme';
  const applicantName = applicantInfo?.name || applicantInfo?.full_name || 'Applicant';
  const otrNo = applicantInfo?.otr_number || applicantInfo?.otrNo || 'OTR-LIVE';

  if (loading && !queueItem && fields.length === 0) {
    return (
      <div className="gov-card p-12 text-center space-y-3">
        <RefreshCw className="w-8 h-8 text-[#1D0A69] animate-spin mx-auto" />
        <h3 className="text-base font-bold text-[#1D0A69]">Connecting to Authoritative Verification Ledger...</h3>
        <p className="text-xs text-gray-500">Querying PostgreSQL verification queue, OCR evidence blocks, and audit trail.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 1. Official Government Header Bar */}
      <div className="bg-[#1D0A69] text-white py-3 px-4 shadow-sm select-none border-b-2 border-[#C85A17] rounded-t">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Left: Breadcrumbs & Back */}
          <div className="flex items-center gap-3">
            {onBackToQueue && (
              <button
                onClick={onBackToQueue}
                className="flex items-center gap-1.5 text-xs font-bold bg-[#0F4C81] hover:bg-[#15074D] px-3 py-1.5 rounded transition-colors text-white"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Queue (जांच सूची)</span>
              </button>
            )}

            <div className="flex items-center gap-1.5 text-xs text-[#CFD8DC]">
              <span>Scrutiny Queue</span>
              <ChevronRight className="w-3 h-3 text-[#90A4AE]" />
              <span className="font-mono text-[#FFC107] font-bold">{appNumber}</span>
              <ChevronRight className="w-3 h-3 text-[#90A4AE]" />
              <span className="text-white font-semibold">Evidence Scrutiny & OCR Audit</span>
            </div>
          </div>

          {/* Right: Authenticated Officer Context */}
          <div className="flex items-center gap-4 text-xs">
            <div className="text-right">
              <div className="font-bold text-white flex items-center gap-1.5 justify-end">
                <UserCheck className="w-3.5 h-3.5 text-[#81C784]" />
                <span>{officerDisplayName}</span>
              </div>
              <div className="text-[11px] text-[#CFD8DC]">Server-Side RBAC & Atomic Row Locking Enforced</div>
            </div>

            <button
              onClick={loadAuthoritativeState}
              disabled={loading || isSubmitting}
              className="flex items-center gap-1 bg-[#15074D] hover:bg-[#0F4C81] border border-[#546E7A] px-2.5 py-1 rounded text-white text-xs font-bold transition-all"
              title="Refresh authoritative state from PostgreSQL"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[#FFC107] ${loading ? 'animate-spin' : ''}`} />
              <span>Sync DB</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Candidate Context Summary Strip */}
      <div className="gov-card bg-[#F4F6F8] p-3 flex flex-wrap items-center justify-between gap-3 border-l-4 border-l-[#1D0A69]">
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div>
            <span className="text-[10px] text-[#546E7A] uppercase font-bold block">Candidate:</span>
            <strong className="text-[#150202] text-sm">{applicantName} ({otrNo})</strong>
          </div>

          <div className="border-l border-[#CFD8DC] pl-4">
            <span className="text-[10px] text-[#546E7A] uppercase font-bold block">Target Scheme:</span>
            <strong className="text-[#1D0A69]">{schemeName}</strong>
          </div>

          {documentInfo && (
            <div className="border-l border-[#CFD8DC] pl-4">
              <span className="text-[10px] text-[#546E7A] uppercase font-bold block">Document:</span>
              <strong className="text-[#150202]">
                {documentInfo.original_filename || documentInfo.file_name || documentInfo.document_type}
                {' '}({documentInfo.lifecycle_status || 'SAFE'})
              </strong>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isDocumentVerified ? (
            <span className="gov-badge gov-badge-success text-xs font-bold flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5 text-[#198754]" />
              <span>OFFICER VERIFIED (Rank 40)</span>
            </span>
          ) : (
            <span className="gov-badge gov-badge-warning text-xs font-bold flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-[#C85A17]" />
              <span>VERIFICATION PENDING</span>
            </span>
          )}

          {!isDocumentVerified ? (
            <button
              onClick={handleVerifyDocument}
              disabled={isSubmitting}
              className="bg-[#1D0A69] hover:bg-[#15074D] text-[#FFC107] text-xs font-bold px-3 py-1.5 rounded flex items-center gap-1 border border-[#C85A17] transition-all"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Accept Document Evidence</span>
            </button>
          ) : (
            <button
              onClick={handleReopen}
              disabled={isSubmitting}
              className="bg-[#C85A17] hover:bg-[#A8450D] text-white text-xs font-bold px-3 py-1.5 rounded flex items-center gap-1 transition-all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reopen Scrutiny</span>
            </button>
          )}
        </div>
      </div>

      {/* 3. Alerts: Success / Error Notifications */}
      {actionSuccessMsg && (
        <div className="bg-[#E8F5E9] border border-[#A5D6A7] text-[#1B5E20] px-4 py-2.5 rounded text-xs font-semibold flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-[#198754] flex-shrink-0" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {error && (
        <div className="bg-[#FFEBEE] border border-[#FFCDD2] text-[#B71C1C] px-4 py-2.5 rounded text-xs font-semibold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-[#B71C1C] flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 4. Statutory Trust Hierarchy Strip */}
      <div className="bg-[#FFF8E1] border-l-4 border-l-[#C85A17] border border-[#FFE082] rounded p-3 text-xs text-[#5D4037] space-y-1">
        <div className="flex items-center gap-1.5 font-bold text-[#C85A17]">
          <Info className="w-4 h-4" />
          <span>STATUTORY TRUST HIERARCHY & ARCHITECTURAL GUARANTEES:</span>
        </div>
        <div className="flex flex-wrap gap-2 items-center text-[11px] font-mono">
          <span className="bg-white px-2 py-0.5 rounded border border-[#C85A17] text-[#C85A17] font-bold">1. OFFICER_VERIFIED (60)</span>
          <span>&gt;</span>
          <span className="bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">2. OFFICIAL_INTEGRATION (50)</span>
          <span>&gt;</span>
          <span className="bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">3. VERIFIED_DOCUMENT (40)</span>
          <span>&gt;</span>
          <span className="bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">4. SYSTEM (30)</span>
          <span>&gt;</span>
          <span className="bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">5. APPLICANT_DECLARED (20)</span>
          <span>&gt;</span>
          <span className="bg-white px-2 py-0.5 rounded border border-amber-400 text-amber-800 font-bold">6. OCR_PROVISIONAL (10)</span>
        </div>
        <p className="text-[11px] leading-relaxed m-0 text-gray-600">
          <strong>Guarantees:</strong> (1) OCR confidence never equates to verification. (2) OCR never overwrites applicant data. 
          (3) Discrepancies create human review work items. (4) Security status (<code>SAFE</code>) is decoupled from evidentiary validity (<code>VERIFIED_DOCUMENT</code>). 
          (5) Officer validates evidence; eligibility is evaluated strictly by the deterministic engine.
        </p>
      </div>

      {/* 5. Main 2-Column Split: Document Evidence Canvas (Left) vs Verification Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* LEFT COLUMN: Document Canvas with OCR Bounding Box Overlay */}
        <div className="gov-card lg:col-span-7 p-4 space-y-3">
          <div className="flex justify-between items-center border-b border-[#CFD8DC] pb-2">
            <div>
              <div className="flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-[#C85A17]" />
                <h3 className="text-sm font-bold text-[#1D0A69]">Document Evidence Canvas</h3>
              </div>
              <span className="text-[11px] text-gray-500">
                {documentInfo?.original_filename || 'Evidence File'} | Antivirus Status: {documentInfo?.lifecycle_status || 'SAFE'}
              </span>
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center gap-2 text-xs">
              <button 
                onClick={() => setZoomLevel(prev => Math.max(80, prev - 10))}
                className="px-2 py-0.5 rounded bg-gray-100 hover:bg-gray-200 border border-gray-300"
              >-</button>
              <span className="font-mono text-xs">{zoomLevel}%</span>
              <button 
                onClick={() => setZoomLevel(prev => Math.min(140, prev + 10))}
                className="px-2 py-0.5 rounded bg-gray-100 hover:bg-gray-200 border border-gray-300"
              >+</button>
            </div>
          </div>

          {/* Interactive Document Image Container */}
          <div className="relative bg-[#1F2937] rounded border border-[#374151] p-4 overflow-auto min-h-[440px]" style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top left', transition: 'transform 0.15s ease' }}>
            <div className="bg-[#f8fafc] text-[#0f172a] rounded p-6 shadow-md relative min-h-[380px] font-sans text-xs">
              <div className="text-center border-b-2 border-slate-300 pb-2 mb-4">
                <div className="font-extrabold text-sm uppercase">भारत सरकार / Government of India</div>
                <div className="font-bold text-xs text-blue-900 uppercase">
                  {documentInfo?.document_type ? documentInfo.document_type.replace('_', ' ') : 'Evidentiary Document'}
                </div>
                <div className="text-[10px] text-slate-500">Official Scrutinised Copy — Authoritative Storage Ledger</div>
              </div>

              {/* Extracted Text Rendering */}
              {ocrFullText ? (
                <div className="space-y-2 text-xs leading-relaxed font-mono whitespace-pre-wrap bg-white p-3 rounded border border-slate-200">
                  {ocrFullText}
                </div>
              ) : fields.length > 0 ? (
                <div className="space-y-2 text-xs leading-relaxed">
                  {fields.map(f => (
                    <div 
                      key={f.field_code}
                      onClick={() => setSelectedFieldCode(f.field_code)}
                      className={`p-1.5 rounded cursor-pointer transition-all ${
                        selectedFieldCode === f.field_code
                          ? 'bg-yellow-100 border-2 border-yellow-500 font-bold'
                          : 'bg-blue-50 border border-dashed border-blue-300 hover:bg-blue-100'
                      }`}
                    >
                      <span className="text-[10px] text-gray-500 uppercase block">{f.field_label}:</span>
                      <span>{String(f.ocr_value ?? f.declared_value ?? '—')}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-16 text-gray-400 space-y-2">
                  <FileText className="w-8 h-8 mx-auto text-gray-300" />
                  <p>Document OCR extraction in progress or no text blocks detected.</p>
                </div>
              )}

              {/* SVG Bounding Box Overlay */}
              {boundingBoxes.length > 0 && (
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  {boundingBoxes.map(box => {
                    const isSelected = box.field_code === selectedFieldCode;
                    return (
                      <rect
                        key={box.id}
                        x={`${box.x}%`}
                        y={`${box.y}%`}
                        width={`${box.width}%`}
                        height={`${box.height}%`}
                        fill={isSelected ? 'rgba(59, 130, 246, 0.25)' : 'transparent'}
                        stroke={isSelected ? '#2563eb' : 'rgba(200, 90, 23, 0.4)'}
                        strokeWidth={isSelected ? 2 : 1}
                        strokeDasharray={isSelected ? 'none' : '3 2'}
                        rx={3}
                      />
                    );
                  })}
                </svg>
              )}
            </div>
          </div>

          <div className="text-[11px] text-gray-500 flex justify-between items-center">
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-blue-500/50 border border-blue-600 inline-block rounded-xs" />
              <span>Active Focus</span>
              <span className="w-2.5 h-2.5 border border-dashed border-[#C85A17] inline-block rounded-xs ml-2" />
              <span>PaddleOCR Provisional Block</span>
            </span>
            <span className="font-mono text-[10px] text-gray-400">PostgreSQL Authoritative</span>
          </div>
        </div>

        {/* RIGHT COLUMN: Verification, Conflict Resolution & Eligibility Panel */}
        <div className="gov-card lg:col-span-5 p-4 space-y-4">
          
          {/* Tabs */}
          <div className="flex gap-2 border-b border-[#CFD8DC] pb-2 text-xs">
            <button
              onClick={() => setActiveTab('fields')}
              className={`px-3 py-1.5 rounded font-bold transition-all ${
                activeTab === 'fields'
                  ? 'bg-[#E1F5FE] text-[#01579B] border border-[#B3E5FC]'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Extracted Fields ({fields.length})
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 py-1.5 rounded font-bold transition-all ${
                activeTab === 'history'
                  ? 'bg-[#E1F5FE] text-[#01579B] border border-[#B3E5FC]'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Audit Trail ({history.length})
            </button>
            <button
              onClick={() => setActiveTab('eligibility')}
              className={`px-3 py-1.5 rounded font-bold transition-all ${
                activeTab === 'eligibility'
                  ? 'bg-[#FFF3E0] text-[#E65100] border border-[#FFE0B2]'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Eligibility Impact
            </button>
          </div>

          {/* TAB 1: Fields & Conflict Resolution */}
          {activeTab === 'fields' && (
            <div className="space-y-3">
              {fields.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-xs">
                  <AlertTriangle className="w-6 h-6 text-amber-500 mx-auto mb-2" />
                  <p className="font-semibold">No extracted fields available in database for this document.</p>
                  <p className="text-[11px] text-gray-400 mt-1">Fields appear once PaddleOCR worker processes the upload.</p>
                </div>
              ) : (
                fields.map(field => {
                  const isSelected = field.field_code === selectedFieldCode;
                  const isConflict = field.verification_status === 'CONFLICT' || field.has_conflict;
                  const isVerified = field.verification_status === 'VERIFIED';
                  const isRejected = field.verification_status === 'REJECTED';
                  const isDeficient = field.verification_status === 'NEEDS_MORE_EVIDENCE';
                  const isEscalated = field.verification_status === 'ESCALATED';

                  return (
                    <div
                      key={field.field_code}
                      onClick={() => setSelectedFieldCode(field.field_code)}
                      className={`p-3 rounded border text-xs cursor-pointer transition-all ${
                        isSelected 
                          ? 'bg-[#F0F7FF] border-[#1D0A69] shadow-xs' 
                          : 'bg-white border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-mono">
                            {field.field_code}
                          </span>
                          <h4 className="text-xs font-bold text-[#1D0A69]">{field.field_label}</h4>
                        </div>

                        {isConflict && (
                          <span className="gov-badge gov-badge-danger text-[10px] font-bold flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-[#C85A17]" />
                            <span>MATERIAL CONFLICT</span>
                          </span>
                        )}
                        {isVerified && (
                          <span className="gov-badge gov-badge-success text-[10px] font-bold flex items-center gap-1">
                            <CheckCircle className="w-3 h-3 text-[#198754]" />
                            <span>OFFICER VERIFIED</span>
                          </span>
                        )}
                        {isRejected && (
                          <span className="gov-badge gov-badge-danger text-[10px] font-bold flex items-center gap-1">
                            <XCircle className="w-3 h-3 text-[#B71C1C]" />
                            <span>REJECTED</span>
                          </span>
                        )}
                        {isDeficient && (
                          <span className="gov-badge gov-badge-warning text-[10px] font-bold flex items-center gap-1">
                            <HelpCircle className="w-3 h-3 text-[#C85A17]" />
                            <span>NEEDS EVIDENCE</span>
                          </span>
                        )}
                        {isEscalated && (
                          <span className="gov-badge gov-badge-info text-[10px] font-bold flex items-center gap-1">
                            <ArrowUpRight className="w-3 h-3 text-[#0F4C81]" />
                            <span>ESCALATED</span>
                          </span>
                        )}
                        {!isConflict && !isVerified && !isRejected && !isDeficient && !isEscalated && (
                          <span className="gov-badge gov-badge-warning text-[10px] font-bold">
                            PENDING REVIEW
                          </span>
                        )}
                      </div>

                      {/* Comparison Grid: Declared vs OCR */}
                      <div className="grid grid-cols-2 gap-2 bg-[#F4F6F8] border border-[#ECEFF1] p-2 rounded text-xs mb-2">
                        <div>
                          <div className="text-[10px] text-gray-500 flex justify-between">
                            <span>Declared:</span>
                            <span className="font-mono text-[9px]">Rank 20</span>
                          </div>
                          <div className="font-semibold text-gray-800 mt-0.5">
                            {typeof field.declared_value === 'number' 
                              ? `₹${field.declared_value.toLocaleString('en-IN')}` 
                              : String(field.declared_value ?? '—')}
                          </div>
                        </div>

                        <div>
                          <div className="text-[10px] text-gray-500 flex justify-between">
                            <span>OCR Extracted:</span>
                            <span className="font-mono text-[9px] text-amber-700">Rank 10</span>
                          </div>
                          <div className={`font-semibold mt-0.5 ${isConflict ? 'text-[#C85A17]' : 'text-blue-800'}`}>
                            {typeof field.ocr_value === 'number'
                              ? `₹${field.ocr_value.toLocaleString('en-IN')}`
                              : String(field.ocr_value ?? '—')}
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-between items-center text-[10px] text-gray-500 mb-2">
                        <span className="font-mono">Confidence: {(field.confidence * 100).toFixed(0)}%</span>
                        {field.verified_value !== null && field.verified_value !== undefined && (
                          <span className="font-bold text-[#198754]">
                            Verified Value: {String(field.verified_value)}
                          </span>
                        )}
                      </div>

                      {/* Action Controls for Selected Field */}
                      {isSelected && (
                        <div className="border-t border-gray-200 pt-2.5 mt-2 space-y-2">
                          {isConflict ? (
                            <div className="space-y-1.5">
                              <p className="text-[11px] text-[#B71C1C] font-semibold">
                                Discrepancy detected between applicant declaration and certificate extraction. Choose authoritative resolution:
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                <button
                                  disabled={isSubmitting}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleResolveConflict(field.field_code, 'USE_DOCUMENT_VALUE', 'Documentary evidence accepted by scrutiny officer.');
                                  }}
                                  className="bg-[#1D0A69] hover:bg-[#15074D] text-white text-[11px] font-bold px-2.5 py-1.5 rounded transition-all"
                                >
                                  Accept Document Value ({String(field.ocr_value)})
                                </button>
                                <button
                                  disabled={isSubmitting}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleResolveConflict(field.field_code, 'USE_APPLICANT_DECLARATION', 'Applicant self-declaration accepted per supplementary affidavit.');
                                  }}
                                  className="bg-white hover:bg-gray-100 text-[#1D0A69] border border-[#1D0A69] text-[11px] font-bold px-2.5 py-1.5 rounded transition-all"
                                >
                                  Keep Declared ({String(field.declared_value)})
                                </button>
                                <button
                                  disabled={isSubmitting}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleNeedsMoreEvidence(field.field_code);
                                  }}
                                  className="bg-[#FFF3E0] hover:bg-[#FFE0B2] text-[#E65100] border border-[#FFE0B2] text-[11px] font-bold px-2.5 py-1.5 rounded transition-all"
                                >
                                  Raise Deficiency
                                </button>
                                <button
                                  disabled={isSubmitting}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleEscalate(field.field_code);
                                  }}
                                  className="bg-[#EDE7F6] hover:bg-[#D1C4E9] text-[#4A148C] border border-[#D1C4E9] text-[11px] font-bold px-2.5 py-1.5 rounded transition-all"
                                >
                                  Escalate
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex flex-wrap gap-1.5">
                              <button
                                disabled={isVerified || isSubmitting}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleVerify(field.field_code, field.ocr_value ?? field.declared_value, 'Document evidence inspected and verified by scrutiny officer.');
                                }}
                                className={`text-[11px] font-bold px-3 py-1.5 rounded transition-all ${
                                  isVerified
                                    ? 'bg-[#E8F5E9] text-[#2E7D32] border border-[#A5D6A7] cursor-default'
                                    : 'bg-[#198754] hover:bg-[#157347] text-white'
                                }`}
                              >
                                {isVerified ? '✓ Verified (Rank 60)' : 'Verify Field Evidence'}
                              </button>
                              <button
                                disabled={isSubmitting}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRejectField(field.field_code);
                                }}
                                className="bg-[#FFEBEE] hover:bg-[#FFCDD2] text-[#C62828] border border-[#FFCDD2] text-[11px] font-bold px-2.5 py-1.5 rounded transition-all"
                              >
                                Reject Field
                              </button>
                              <button
                                disabled={isSubmitting}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleNeedsMoreEvidence(field.field_code);
                                }}
                                className="bg-[#FFF3E0] hover:bg-[#FFE0B2] text-[#E65100] border border-[#FFE0B2] text-[11px] font-bold px-2.5 py-1.5 rounded transition-all"
                              >
                                Needs Clarification
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* TAB 2: Immutable Verification History */}
          {activeTab === 'history' && (
            <div className="space-y-2 text-xs">
              <p className="text-[11px] text-gray-500 mb-2">
                Every verification action creates an append-only immutable audit record in PostgreSQL. Client mutations and fake UUID generation are blocked.
              </p>

              {history.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  No verification actions recorded yet for this document.
                </div>
              ) : (
                history.map(item => (
                  <div key={item.id} className="p-2.5 rounded bg-[#F8F9FA] border border-[#CFD8DC] space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-mono font-bold text-[#0F4C81]">{item.action}</span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        {item.verified_at ? new Date(item.verified_at).toLocaleString() : 'Just now'}
                      </span>
                    </div>

                    <div className="text-[11px] text-gray-600">
                      Field: <strong>{item.field_code}</strong> | Actor: <strong>{item.officer_name}</strong>
                    </div>

                    <div className="text-[11px] text-[#1B5E20] font-semibold">
                      Verified Value: {String(item.verified_value)} (Trust Rank: {item.verified_trust_rank})
                    </div>

                    {item.reason && (
                      <div className="text-[10px] text-gray-500 italic">
                        "{item.reason}"
                      </div>
                    )}

                    <div className="text-[9px] font-mono text-gray-400">
                      Audit UUID: {item.audit_event_id}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* TAB 3: Deterministic Scheme Eligibility Impact */}
          {activeTab === 'eligibility' && (
            <div className="space-y-3 text-xs">
              <div className="bg-[#FFF8E1] border border-[#FFE082] p-2.5 rounded text-[11px] text-[#5D4037] leading-relaxed">
                <strong>Deterministic Boundary:</strong> Scrutiny officers verify evidentiary facts. 
                Scheme eligibility rules are evaluated exclusively by the server-side deterministic rule engine against verified facts.
              </div>

              {eligibilityImpact && eligibilityImpact.rule_evaluations ? (
                <div className="space-y-2">
                  {eligibilityImpact.rule_evaluations.map((rule: any, idx: number) => (
                    <div key={idx} className="border border-gray-200 rounded p-2.5 bg-white space-y-1">
                      <div className="flex justify-between items-center">
                        <strong className="text-xs text-[#1D0A69]">{rule.rule_name || rule.rule_code || `Rule ${idx + 1}`}</strong>
                        <span className={`gov-badge text-[10px] font-bold ${rule.passed ? 'gov-badge-success' : 'gov-badge-danger'}`}>
                          {rule.passed ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-600 m-0">
                        {rule.message || rule.description || `Evaluated threshold: ${rule.condition || 'Satisfied'}`}
                      </p>
                    </div>
                  ))}

                  <div className={`p-2.5 rounded font-bold text-xs ${
                    eligibilityImpact.is_eligible 
                      ? 'bg-[#E8F5E9] border border-[#A5D6A7] text-[#1B5E20]' 
                      : 'bg-[#FFEBEE] border border-[#FFCDD2] text-[#B71C1C]'
                  }`}>
                    Engine Outcome: {eligibilityImpact.is_eligible ? 'ELIGIBLE' : 'INELIGIBLE'} 
                    {eligibilityImpact.summary && ` (${eligibilityImpact.summary})`}
                  </div>
                </div>
              ) : (
                <div className="border border-gray-200 rounded p-4 text-center text-gray-500">
                  <p>Awaiting officer field verification to evaluate deterministic scheme rules.</p>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
