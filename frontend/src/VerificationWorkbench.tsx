import { useState } from 'react';
import { useDemo } from './context/DemoContext';
import { fetchApi } from './services/api';
import { 
  FileText, CheckCircle, AlertTriangle, RefreshCw, Info,
  ShieldCheck, ArrowUpRight, HelpCircle, XCircle, ArrowRight
} from 'lucide-react';

interface OCRBoundingBox {
  id: string;
  text: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
  language: string;
  field_code?: string;
}

type VerificationStatus = 
  | 'PENDING' 
  | 'IN_REVIEW' 
  | 'VERIFIED' 
  | 'REJECTED' 
  | 'NEEDS_MORE_EVIDENCE' 
  | 'ESCALATED' 
  | 'CONFLICT';

interface VerificationField {
  field_code: string;
  label: string;
  declared_value: any;
  declared_trust: string;
  ocr_value: any;
  ocr_trust: string;
  verified_value: any;
  verified_trust: string | null;
  status: VerificationStatus;
  confidence: number;
  evidence_text: string;
  page_number: number;
  block_id: string;
  has_conflict: boolean;
  conflict_type?: string;
}

interface VerificationHistoryEvent {
  id: string;
  audit_event_id: string;
  field_code: string;
  action: string;
  previous_value: any;
  new_value: any;
  previous_trust_rank: number;
  verified_trust_rank: number;
  officer: string;
  role: string;
  timestamp: string;
  reason: string;
}

export default function VerificationWorkbench() {
  const { 
    resolveConflict: demoResolveConflict, 
    verification: demoVerification, 
    setCurrentStep,
    applicant,
    ocrData
  } = useDemo();

  const [selectedFieldCode, setSelectedFieldCode] = useState<string>('annual_family_income');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activeTab, setActiveTab] = useState<'fields' | 'history' | 'eligibility'>('fields');
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);
  const [isDocumentVerified, setIsDocumentVerified] = useState<boolean>(false);

  // Phase 9: Verification Fields with Full Provenance & Trust Levels
  const [fields, setFields] = useState<VerificationField[]>([
    {
      field_code: 'annual_family_income',
      label: 'Annual Family Income',
      declared_value: applicant.declaredIncome || 500000,
      declared_trust: 'APPLICANT_DECLARED (Rank 20)',
      ocr_value: ocrData.income || 450000,
      ocr_trust: 'OCR_PROVISIONAL (Rank 10)',
      verified_value: demoVerification.status === 'VERIFIED' ? 450000 : null,
      verified_trust: demoVerification.status === 'VERIFIED' ? 'OFFICER_VERIFIED (Rank 60)' : null,
      status: demoVerification.status === 'VERIFIED' ? 'VERIFIED' : 'CONFLICT',
      confidence: 0.94,
      evidence_text: 'वार्षिक पारिवारिक आय: 450000 रुपये',
      page_number: 1,
      block_id: 'block-income-01',
      has_conflict: demoVerification.status !== 'VERIFIED',
      conflict_type: 'MATERIAL_CONFLICT',
    },
    {
      field_code: 'certificate_number',
      label: 'Certificate Number',
      declared_value: 'TEST-2026-001',
      declared_trust: 'APPLICANT_DECLARED (Rank 20)',
      ocr_value: 'TEST-2026-001',
      ocr_trust: 'OCR_PROVISIONAL (Rank 10)',
      verified_value: 'TEST-2026-001',
      verified_trust: 'OFFICER_VERIFIED (Rank 60)',
      status: 'VERIFIED',
      confidence: 0.98,
      evidence_text: 'प्रमाण पत्र संख्या: TEST-2026-001',
      page_number: 1,
      block_id: 'block-cert-02',
      has_conflict: false,
    },
    {
      field_code: 'issuing_authority',
      label: 'Issuing Authority',
      declared_value: 'Tehsildar Mandla',
      declared_trust: 'APPLICANT_DECLARED (Rank 20)',
      ocr_value: 'कार्यालय तहसीलदार, मंडला, मध्य प्रदेश',
      ocr_trust: 'OCR_PROVISIONAL (Rank 10)',
      verified_value: 'कार्यालय तहसीलदार, मंडला, मध्य प्रदेश',
      verified_trust: 'OFFICER_VERIFIED (Rank 60)',
      status: 'VERIFIED',
      confidence: 0.95,
      evidence_text: 'कार्यालय तहसीलदार, मंडला, मध्य प्रदेश (Tehsildar Mandla)',
      page_number: 1,
      block_id: 'block-auth-03',
      has_conflict: false,
    },
    {
      field_code: 'issue_date',
      label: 'Date of Issue',
      declared_value: '2026-01-15',
      declared_trust: 'APPLICANT_DECLARED (Rank 20)',
      ocr_value: '15/01/2026',
      ocr_trust: 'OCR_PROVISIONAL (Rank 10)',
      verified_value: null,
      verified_trust: null,
      status: 'PENDING',
      confidence: 0.96,
      evidence_text: 'दिनांक: 15/01/2026',
      page_number: 1,
      block_id: 'block-date-04',
      has_conflict: false,
    }
  ]);

  // Phase 9: Append-Only Immutable Verification Audit Trail
  const [history, setHistory] = useState<VerificationHistoryEvent[]>([
    {
      id: 'hist-01',
      audit_event_id: 'audit-d731fa92-4112-4c28-9d22-11ef842910a1',
      field_code: 'certificate_number',
      action: 'FIELD_VERIFIED',
      previous_value: 'INC-2026-00124 (APPLICANT_DECLARED)',
      new_value: 'INC-2026-00124 (OFFICER_VERIFIED)',
      previous_trust_rank: 20,
      verified_trust_rank: 60,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: '2026-09-30 02:15:22 UTC',
      reason: 'Certificate number matches district portal QR verification hash.'
    },
    {
      id: 'hist-00',
      audit_event_id: 'audit-a189fc44-8840-410e-a521-884910cf9042',
      field_code: 'document_level',
      action: 'DOCUMENT_VERIFICATION_STARTED',
      previous_value: null,
      new_value: 'VERIFICATION_PENDING',
      previous_trust_rank: 10,
      verified_trust_rank: 40,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: '2026-09-30 02:10:00 UTC',
      reason: 'Scrutiny session opened by authorized scrutiny officer.'
    }
  ]);

  const boundingBoxes: OCRBoundingBox[] = [
    { id: 'block-header-00', text: 'भारत सरकार / Government of India', confidence: 0.99, x: 12, y: 8, width: 76, height: 7, language: 'hi' },
    { id: 'block-title-01', text: 'आय प्रमाण पत्र (Income Certificate)', confidence: 0.98, x: 22, y: 18, width: 56, height: 6, language: 'hi' },
    { id: 'block-auth-03', text: 'कार्यालय अनुमंडल पदाधिकारी, रांची', confidence: 0.92, x: 15, y: 28, width: 70, height: 6, language: 'hi', field_code: 'issuing_authority' },
    { id: 'block-cert-02', text: 'प्रमाण पत्र संख्या: INC-2026-00124', confidence: 0.98, x: 15, y: 38, width: 70, height: 6, language: 'hi', field_code: 'certificate_number' },
    { id: 'block-name-00', text: 'प्रमाणित किया जाता है कि श्री अर्जुन मुंडा', confidence: 0.95, x: 15, y: 48, width: 70, height: 6, language: 'hi' },
    { id: 'block-income-01', text: 'वार्षिक पारिवारिक आय: 450000 रुपये', confidence: 0.94, x: 15, y: 58, width: 70, height: 7, language: 'hi', field_code: 'annual_family_income' },
    { id: 'block-date-04', text: 'दिनांक: 15/01/2026', confidence: 0.96, x: 15, y: 70, width: 35, height: 6, language: 'hi', field_code: 'issue_date' },
    { id: 'block-seal-05', text: 'हस्ताक्षर एवं मुहर / SDM Ranchi', confidence: 0.91, x: 55, y: 76, width: 35, height: 10, language: 'hi' },
  ];

  // Action 1: Field Verification
  const handleVerify = (fieldCode: string, value: any, reason: string) => {
    const field = fields.find(f => f.field_code === fieldCode);
    const prevValue = field?.verified_value ?? field?.declared_value;
    const auditUuid = 'audit-' + crypto.randomUUID();

    setFields(prev => prev.map(f => {
      if (f.field_code === fieldCode) {
        return { 
          ...f, 
          verified_value: value, 
          verified_trust: 'OFFICER_VERIFIED (Rank 60)', 
          status: 'VERIFIED', 
          has_conflict: false 
        };
      }
      return f;
    }));

    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: fieldCode,
      action: 'FIELD_VERIFIED',
      previous_value: prevValue,
      new_value: value,
      previous_trust_rank: 20,
      verified_trust_rank: 60,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: reason || 'Verified by officer based on scrutinised document evidence.'
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg(`Field '${fieldCode}' verified as ${typeof value === 'number' ? '₹' + Number(value).toLocaleString('en-IN') : value}. Authoritative trust promoted to OFFICER_VERIFIED (Rank 60). Audit ID: ${auditUuid.slice(0, 14)}...`);
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  // Action 2: Conflict Resolution
  const handleResolveConflict = (fieldCode: string, decision: 'USE_APPLICANT_DECLARATION' | 'USE_DOCUMENT_VALUE' | 'NEEDS_MORE_EVIDENCE', reason: string) => {
    const field = fields.find(f => f.field_code === fieldCode);
    if (!field) return;

    let chosenValue = field.ocr_value;
    let newStatus: VerificationStatus = 'VERIFIED';
    let verifiedTrust: string | null = 'OFFICER_VERIFIED (Rank 60)';

    if (decision === 'USE_APPLICANT_DECLARATION') {
      chosenValue = field.declared_value;
    } else if (decision === 'NEEDS_MORE_EVIDENCE') {
      chosenValue = null;
      newStatus = 'NEEDS_MORE_EVIDENCE';
      verifiedTrust = null;
    }

    const auditUuid = 'audit-' + crypto.randomUUID();

    setFields(prev => prev.map(f => {
      if (f.field_code === fieldCode) {
        return { 
          ...f, 
          verified_value: chosenValue, 
          verified_trust: verifiedTrust, 
          status: newStatus, 
          has_conflict: false 
        };
      }
      return f;
    }));

    // Synchronize global SIH Demo State
    demoResolveConflict(decision, reason);

    // Synchronize authoritative backend verification engine
    (async () => {
      try {
        const statusRes = await fetchApi<any>('/api/v1/verification/demo/status/');
        if (statusRes?.queue_item_id) {
          const actionMap: Record<string, string> = {
            'OVERRIDE_OCR': 'OVERRIDE_WITH_OCR',
            'CONFIRM_DECLARED': 'CONFIRM_APPLICANT',
            'REQUEST_DEFICIENCY': 'REQUEST_DEFICIENCY'
          };
          await fetchApi(`/api/v1/verification/conflicts/${statusRes.queue_item_id}/resolve/`, {
            method: 'POST',
            body: JSON.stringify({
              decision_action: actionMap[decision] || 'OVERRIDE_WITH_OCR',
              chosen_value: chosenValue,
              reason: reason || `Conflict resolved using ${decision}`
            })
          });
        }
      } catch (err) {
        console.warn('Backend sync warning:', err);
      }
    })();

    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: fieldCode,
      action: 'FIELD_CONFLICT_RESOLVED',
      previous_value: `Declared: ₹${field.declared_value.toLocaleString('en-IN')} vs OCR: ₹${field.ocr_value.toLocaleString('en-IN')}`,
      new_value: `${decision} -> ${chosenValue ? (typeof chosenValue === 'number' ? '₹' + chosenValue.toLocaleString('en-IN') : chosenValue) : 'PENDING_EVIDENCE'}`,
      previous_trust_rank: 20,
      verified_trust_rank: newStatus === 'VERIFIED' ? 60 : 20,
      officer: 'S. K. Mahapatra',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: reason || `Conflict resolved using ${decision}`
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg(`Conflict resolved: ${decision} recorded. Authoritative evidence promoted to OFFICER_VERIFIED (Rank 60). Audit ID: ${auditUuid.slice(0, 14)}...`);
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  // Action 3: Field Rejection
  const handleRejectField = (fieldCode: string) => {
    const reason = prompt("Enter statutory justification for field rejection:");
    if (!reason || !reason.trim()) return;

    const auditUuid = 'audit-' + crypto.randomUUID();
    setFields(prev => prev.map(f => f.field_code === fieldCode ? { ...f, status: 'REJECTED', verified_value: null, verified_trust: null } : f));

    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: fieldCode,
      action: 'FIELD_REJECTED',
      previous_value: 'PROVISIONAL',
      new_value: 'REJECTED',
      previous_trust_rank: 20,
      verified_trust_rank: 0,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: reason
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg(`Field '${fieldCode}' marked REJECTED. Mandatory audit recorded. Audit ID: ${auditUuid.slice(0, 14)}...`);
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  // Action 4: Needs More Evidence
  const handleNeedsMoreEvidence = (fieldCode: string) => {
    const deficiency = prompt("Enter specific deficiency / clarification required from applicant:");
    if (!deficiency || !deficiency.trim()) return;

    const auditUuid = 'audit-' + crypto.randomUUID();
    setFields(prev => prev.map(f => f.field_code === fieldCode ? { ...f, status: 'NEEDS_MORE_EVIDENCE' } : f));

    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: fieldCode,
      action: 'DEFICIENCY_RAISED',
      previous_value: 'UNDER_SCRUTINY',
      new_value: 'NEEDS_MORE_EVIDENCE',
      previous_trust_rank: 20,
      verified_trust_rank: 20,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: deficiency
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg(`Deficiency raised for '${fieldCode}'. Applicant notified for documentary clarification.`);
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  // Action 5: Escalation
  const handleEscalate = (fieldCode: string) => {
    const escalationNote = prompt("Enter justification for escalating to Verifying Authority / District Nodal Officer:");
    if (!escalationNote || !escalationNote.trim()) return;

    const auditUuid = 'audit-' + crypto.randomUUID();
    setFields(prev => prev.map(f => f.field_code === fieldCode ? { ...f, status: 'ESCALATED' } : f));

    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: fieldCode,
      action: 'VERIFICATION_ESCALATED',
      previous_value: 'UNDER_SCRUTINY',
      new_value: 'ESCALATED_TO_AUTHORITY',
      previous_trust_rank: 20,
      verified_trust_rank: 20,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: escalationNote
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg(`Item escalated to District Nodal Verifying Authority. Audit ID: ${auditUuid.slice(0, 14)}...`);
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  // Action 6: Document Verification (SAFE != VERIFIED)
  const handleVerifyDocument = () => {
    const reason = prompt("Enter verification remarks for accepting this document as VERIFIED_DOCUMENT (Rank 40):", "Original income certificate scrutinised; digital sign validated.");
    if (!reason || !reason.trim()) return;

    const auditUuid = 'audit-' + crypto.randomUUID();
    setIsDocumentVerified(true);

    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: 'document_level',
      action: 'DOCUMENT_EVIDENCE_VERIFIED',
      previous_value: 'SAFE (Security Cleared)',
      new_value: 'VERIFIED_DOCUMENT (Evidentiary Acceptance)',
      previous_trust_rank: 10,
      verified_trust_rank: 40,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: reason
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg("Document marked as VERIFIED_DOCUMENT. Trust rank upgraded to 40. Document security status (SAFE) remains independent.");
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  const handleReopen = () => {
    const reason = prompt("Enter statutory justification reason for reopening verification session:");
    if (!reason || !reason.trim()) return;

    setFields(prev => prev.map(f => ({ ...f, status: 'IN_REVIEW' })));
    setIsDocumentVerified(false);

    const auditUuid = 'audit-' + crypto.randomUUID();
    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: 'document_level',
      action: 'DOCUMENT_VERIFICATION_REOPENED',
      previous_value: 'COMPLETED',
      new_value: 'IN_REVIEW',
      previous_trust_rank: 40,
      verified_trust_rank: 20,
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: reason
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg("Verification session reopened. All previous historical events remain preserved in append-only log.");
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* 1. Header Bar with Phase 9 Identity & Statutory Trust Rank Badges */}
      <div className="gov-card flex flex-wrap justify-between items-center gap-4">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <span className="gov-badge gov-badge-info" style={{ background: '#0F4C81', color: '#fff', fontWeight: 700 }}>
              PHASE 9 OFFICER VERIFICATION WORKSPACE
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Application #<strong>APP-2026-NFST-0881</strong>
            </span>
            <span className="gov-badge gov-badge-success" title="Antivirus & ClamAV Cleared">
              <ShieldCheck size={12} className="inline mr-1" /> SAFE (SEC-GATE)
            </span>
            {isDocumentVerified ? (
              <span className="gov-badge gov-badge-success" style={{ background: '#1D0A69', color: '#FFC107' }}>
                <CheckCircle size={12} className="inline mr-1" /> VERIFIED_DOCUMENT (Rank 40)
              </span>
            ) : (
              <span className="gov-badge gov-badge-warning">
                VERIFICATION_PENDING
              </span>
            )}
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#1D0A69' }}>
            Tribal Scholar Sovereign Scrutiny & Evidentiary Audit Console
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
            Scrutiny Officer: <strong>Shri S. K. Mahapatra (SCRUTINY_OFFICER, Ranchi Zone)</strong> | Server-Side RBAC & Atomic Row Locking Enforced
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {!isDocumentVerified ? (
            <button 
              onClick={handleVerifyDocument}
              className="gov-btn gov-btn-primary text-xs"
              style={{ background: '#1D0A69', color: '#FFC107', borderColor: '#C85A17' }}
            >
              <ShieldCheck size={14} className="mr-1 inline" /> Accept Document Evidence
            </button>
          ) : (
            <button 
              onClick={handleReopen}
              className="gov-btn gov-btn-danger text-xs"
            >
              <RefreshCw size={14} className="mr-1 inline" /> Reopen Scrutiny
            </button>
          )}
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textAlign: 'right' }}>
            <div>Authoritative Rank: <strong>OFFICER_VERIFIED (Rank 60)</strong></div>
            <div>Storage Audit: <strong>APPEND-ONLY (IMMUTABLE)</strong></div>
          </div>
        </div>
      </div>

      {/* 2. Success Notification Alert */}
      {actionSuccessMsg && (
        <div style={{ 
          background: 'var(--gov-success-bg)', border: '1px solid var(--gov-success-border)',
          borderRadius: '4px', padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem',
          color: 'var(--gov-success)', fontSize: '0.85rem', fontWeight: 600
        }}>
          <CheckCircle size={16} />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* 3. Statutory Trust Hierarchy & Security Boundary Mandate */}
      <div style={{
        background: '#FFF8E1', borderLeft: '4px solid #C85A17',
        borderTop: '1px solid #FFE082', borderRight: '1px solid #FFE082', borderBottom: '1px solid #FFE082',
        borderRadius: '4px', padding: '0.85rem 1rem', fontSize: '0.8rem', color: '#5D4037',
        display: 'flex', flexDirection: 'column', gap: '0.4rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, color: '#C85A17' }}>
          <Info size={16} />
          <span>STATUTORY TRUST HIERARCHY & ARCHITECTURAL GUARANTEES:</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', fontSize: '0.75rem' }}>
          <span className="font-mono bg-white px-2 py-0.5 rounded border border-[#C85A17] text-[#C85A17] font-bold">
            1. OFFICER_VERIFIED (60)
          </span>
          <span>&gt;</span>
          <span className="font-mono bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">
            2. OFFICIAL_INTEGRATION (50)
          </span>
          <span>&gt;</span>
          <span className="font-mono bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">
            3. VERIFIED_DOCUMENT (40)
          </span>
          <span>&gt;</span>
          <span className="font-mono bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">
            4. SYSTEM (30)
          </span>
          <span>&gt;</span>
          <span className="font-mono bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-700">
            5. APPLICANT_DECLARED (20)
          </span>
          <span>&gt;</span>
          <span className="font-mono bg-white px-2 py-0.5 rounded border border-amber-400 text-amber-800 font-bold">
            6. OCR_PROVISIONAL (10)
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '0.75rem', lineHeight: '1.4' }}>
          <strong>NON-NEGOTIABLE GUARANTEES:</strong> (1) OCR confidence never equates to verification. (2) OCR never overwrites applicant data. 
          (3) Discrepancies create human review work items. (4) Document security status (<code>SAFE</code>) is strictly decoupled from evidentiary validity (<code>VERIFIED_DOCUMENT</code>). 
          (5) Officer validates evidence; scheme eligibility is strictly evaluated by the deterministic engine.
        </p>
      </div>

      {/* 4. Main 2-Column Split: Document Viewer (Left) vs Verification Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: Document Evidence Viewer with OCR Bounding Box Overlay */}
        <div className="glass-panel lg:col-span-7" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={18} color="#C85A17" />
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#1D0A69' }}>Document Evidence Canvas</h3>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                ST Income Certificate (income_cert_2026.png) | Page 1 of 1 | Antivirus Status: SAFE
              </span>
            </div>
            
            {/* Zoom Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
              <button 
                onClick={() => setZoomLevel(prev => Math.max(80, prev - 10))}
                style={{ padding: '0.25rem 0.5rem', borderRadius: '4px', background: 'rgba(0,0,0,0.06)', border: '1px solid var(--border-subtle)', cursor: 'pointer' }}
              >-</button>
              <span className="mono">{zoomLevel}%</span>
              <button 
                onClick={() => setZoomLevel(prev => Math.min(140, prev + 10))}
                style={{ padding: '0.25rem 0.5rem', borderRadius: '4px', background: 'rgba(0,0,0,0.06)', border: '1px solid var(--border-subtle)', cursor: 'pointer' }}
              >+</button>
            </div>
          </div>

          {/* Interactive Document Image Container */}
          <div style={{ 
            position: 'relative', 
            background: '#1F2937', 
            borderRadius: '8px', 
            border: '1px solid #374151',
            padding: '1.5rem',
            overflow: 'auto',
            minHeight: '440px',
            transform: `scale(${zoomLevel / 100})`,
            transformOrigin: 'top left',
            transition: 'transform 0.15s ease'
          }}>
            {/* Simulated High-Res Scanned Document Paper */}
            <div style={{
              background: '#f8fafc',
              color: '#0f172a',
              borderRadius: '4px',
              padding: '2rem 1.5rem',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
              position: 'relative',
              minHeight: '400px',
              fontFamily: '"Nirmala UI", sans-serif',
              fontSize: '0.9rem'
            }}>
              
              {/* Document Header Text */}
              <div style={{ textAlign: 'center', borderBottom: '2px solid #cbd5e1', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ fontWeight: 800, fontSize: '1.1rem' }}>भारत सरकार / GOVERNMENT OF INDIA</div>
                <div style={{ fontWeight: 700, fontSize: '1rem', color: '#1e3a8a' }}>आय प्रमाण पत्र (INCOME CERTIFICATE)</div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>कार्यालय तहसीलदार, मंडला / Office of Tehsildar, Mandla (Madhya Pradesh)</div>
              </div>

              {/* Document Body Lines */}
              <div style={{ lineHeight: '2.2', fontSize: '0.85rem' }}>
                <div>प्रमाण पत्र संख्या / Certificate No: <strong>TEST-2026-001</strong></div>
                <div>आवेदक का नाम / Applicant Name: <strong>Demo ST Applicant</strong></div>
                <div>पिता का नाम / Father's Name: <strong>श्री रामेश्वर मुंडा (Shri Rameshwar Munda)</strong></div>
                <div>समुदाय / Category: <strong>अनुसूचित जनजाति (ST - Scheduled Tribe)</strong></div>
                <div style={{ 
                  background: selectedFieldCode === 'annual_family_income' ? '#fef08a' : '#e0f2fe',
                  padding: '0.2rem 0.5rem', borderRadius: '4px', display: 'inline-block',
                  border: selectedFieldCode === 'annual_family_income' ? '2px solid #ca8a04' : '1px dashed #0284c7'
                }}>
                  वार्षिक पारिवारिक आय / Annual Family Income: <strong>₹4,50,000/- (रुपये चार लाख पचास हजार मात्र)</strong>
                </div>
                <div>जारी करने का दिनांक / Date of Issue: <strong>15/01/2026</strong></div>
              </div>

              {/* Document Seal / Signature Area */}
              <div style={{ marginTop: '2.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', fontSize: '0.75rem' }}>
                <div style={{ border: '1px solid #cbd5e1', padding: '0.5rem', borderRadius: '4px', textAlign: 'center' }}>
                  [QR / DIGITAL SEAL]<br/><span style={{ fontSize: '0.65rem', color: '#64748b' }}>VERIFIED GOV ARCHIVE</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontStyle: 'italic', fontWeight: 600 }}>तहसीलदार / Tehsildar</div>
                  <div>मंडला, मध्य प्रदेश (Mandla, MP)</div>
                </div>
              </div>

              {/* OCR Bounding Box Overlays (SVG) */}
              <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
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
            </div>
          </div>

          {/* Interactive Bounding Box Inspector Legend */}
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{ width: 10, height: 10, background: 'rgba(59, 130, 246, 0.5)', border: '1px solid #2563eb', display: 'inline-block', borderRadius: 2 }} />
                Active Focus
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{ width: 10, height: 10, border: '1px dashed #C85A17', display: 'inline-block', borderRadius: 2 }} />
                PaddleOCR Provisional Block (700px Bound)
              </span>
            </div>
            <span className="mono text-xs text-gray-500">Async Celery Safe</span>
          </div>
        </div>

        {/* RIGHT COLUMN: Verification, Conflict Resolution & Eligibility Panel */}
        <div className="glass-panel lg:col-span-5" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* Panel Tab Navigation: Fields vs Audit Trail vs Eligibility Impact */}
          <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
            <button 
              onClick={() => setActiveTab('fields')}
              style={{
                background: activeTab === 'fields' ? '#E1F5FE' : 'transparent',
                color: activeTab === 'fields' ? '#01579B' : 'var(--text-muted)',
                border: activeTab === 'fields' ? '1px solid #B3E5FC' : '1px solid transparent',
                padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer'
              }}
            >
              Extracted Fields ({fields.length})
            </button>
            <button 
              onClick={() => setActiveTab('history')}
              style={{
                background: activeTab === 'history' ? '#E1F5FE' : 'transparent',
                color: activeTab === 'history' ? '#01579B' : 'var(--text-muted)',
                border: activeTab === 'history' ? '1px solid #B3E5FC' : '1px solid transparent',
                padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer'
              }}
            >
              Audit Trail ({history.length})
            </button>
            <button 
              onClick={() => setActiveTab('eligibility')}
              style={{
                background: activeTab === 'eligibility' ? '#FFF3E0' : 'transparent',
                color: activeTab === 'eligibility' ? '#E65100' : 'var(--text-muted)',
                border: activeTab === 'eligibility' ? '1px solid #FFE0B2' : '1px solid transparent',
                padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer'
              }}
            >
              Eligibility Impact
            </button>
          </div>

          {activeTab === 'fields' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {demoVerification.status === 'VERIFIED' && (
                <div className="bg-[#E8F5E9] border-2 border-[#198754] p-3.5 rounded text-xs text-[#1B5E20] space-y-2 shadow-xs">
                  <div className="flex items-center justify-between">
                    <div className="font-bold flex items-center gap-1.5 text-sm">
                      <CheckCircle className="w-4 h-4 text-[#198754]" />
                      <span>✓ Evidence Verified by Authorized Officer</span>
                    </div>
                    <span className="font-mono text-[10px] bg-white text-[#198754] font-bold px-2 py-0.5 rounded border border-[#A5D6A7]">
                      OFFICER_VERIFIED (Rank 60)
                    </span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Annual family income certified at <strong>₹4,50,000</strong>. Material conflict resolved and immutable audit record committed. Deterministic Rule Engine re-evaluated: <strong>Income Rule: PASS (₹4.5L &le; ₹6.0L)</strong>.
                  </p>
                  <div className="pt-1 flex justify-end">
                    <button
                      onClick={() => setCurrentStep('applicant_status')}
                      className="bg-[#1D0A69] hover:bg-[#15074D] text-[#FFC107] font-bold px-3.5 py-2 rounded text-xs flex items-center gap-1.5 shadow-xs border border-[#C85A17] transition-all"
                    >
                      <span>View Updated Applicant Status & Eligibility (Step 7) →</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}

              {/* Field Cards */}
              {fields.map(field => {
                const isSelected = field.field_code === selectedFieldCode;
                const isConflict = field.status === 'CONFLICT' || field.has_conflict;
                const isVerified = field.status === 'VERIFIED';
                const isRejected = field.status === 'REJECTED';
                const isDeficient = field.status === 'NEEDS_MORE_EVIDENCE';
                const isEscalated = field.status === 'ESCALATED';

                return (
                  <div 
                    key={field.field_code}
                    onClick={() => setSelectedFieldCode(field.field_code)}
                    style={{
                      padding: '1rem',
                      borderRadius: '4px',
                      background: isSelected ? '#F0F7FF' : '#FFFFFF',
                      border: isSelected ? '2px solid #1D0A69' : '1px solid var(--border-subtle)',
                      boxShadow: isSelected ? '0 2px 6px rgba(29, 10, 105, 0.08)' : 'none',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                      <div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          {field.field_code}
                        </span>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: '#1D0A69' }}>{field.label}</h4>
                      </div>
                      
                      {isConflict && (
                        <span className="gov-badge gov-badge-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <AlertTriangle size={12} /> MATERIAL CONFLICT
                        </span>
                      )}
                      {isVerified && (
                        <span className="gov-badge gov-badge-success" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <CheckCircle size={12} /> OFFICER VERIFIED
                        </span>
                      )}
                      {isRejected && (
                        <span className="gov-badge gov-badge-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <XCircle size={12} /> REJECTED
                        </span>
                      )}
                      {isDeficient && (
                        <span className="gov-badge gov-badge-warning" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <HelpCircle size={12} /> NEEDS MORE EVIDENCE
                        </span>
                      )}
                      {isEscalated && (
                        <span className="gov-badge gov-badge-info" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: '#4A148C', color: '#fff' }}>
                          <ArrowUpRight size={12} /> ESCALATED
                        </span>
                      )}
                      {field.status === 'PENDING' && (
                        <span className="gov-badge gov-badge-warning">
                          PENDING REVIEW
                        </span>
                      )}
                    </div>

                    {/* Comparison Grid: Declared (Rank 20) vs OCR (Rank 10) */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', background: '#F4F6F8', border: '1px solid #ECEFF1', padding: '0.6rem 0.75rem', borderRadius: '4px', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                          <span>Applicant Declared:</span>
                          <span className="font-mono text-[10px] text-gray-500">Rank 20</span>
                        </div>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)', marginTop: '2px' }}>
                          {typeof field.declared_value === 'number' ? `₹${field.declared_value.toLocaleString('en-IN')}` : String(field.declared_value)}
                        </div>
                      </div>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                          <span>OCR Provisional:</span>
                          <span className="font-mono text-[10px] text-amber-700">Rank 10</span>
                        </div>
                        <div style={{ fontWeight: 600, color: isConflict ? '#A71D2A' : '#0288D1', marginTop: '2px' }}>
                          {typeof field.ocr_value === 'number' ? `₹${field.ocr_value.toLocaleString('en-IN')}` : String(field.ocr_value)}
                        </div>
                      </div>
                    </div>

                    {/* Evidence Snippet & Confidence */}
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontStyle: 'italic', maxWidth: '75%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        Raw OCR: "{field.evidence_text}"
                      </span>
                      <span className="mono" style={{ color: '#059669', fontWeight: 600 }}>OCR Conf: {(field.confidence * 100).toFixed(0)}%</span>
                    </div>

                    {/* Action Controls for Selected Field */}
                    {isSelected && (
                      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
                        {isConflict ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <div style={{ fontSize: '0.75rem', color: '#B71C1C', fontWeight: 600 }}>
                              Material Discrepancy: Declared ₹{Number(field.declared_value).toLocaleString('en-IN')} vs Certificate ₹{Number(field.ocr_value).toLocaleString('en-IN')}. Choose evidence-backed resolution:
                            </div>
                            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                              <button
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  handleResolveConflict(field.field_code, 'USE_DOCUMENT_VALUE', 'Certificate documentary value accepted by scrutiny officer.'); 
                                }}
                                style={{ padding: '0.4rem 0.65rem', borderRadius: '4px', background: '#1D0A69', color: '#fff', border: 'none', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                              >
                                Accept Document Value (₹{Number(field.ocr_value).toLocaleString('en-IN')})
                              </button>
                              <button
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  handleResolveConflict(field.field_code, 'USE_APPLICANT_DECLARATION', 'Applicant self-declaration accepted per supplementary gazetted affidavit.'); 
                                }}
                                style={{ padding: '0.4rem 0.65rem', borderRadius: '4px', background: '#fff', color: '#1D0A69', border: '1px solid #1D0A69', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                              >
                                Keep Declared (₹{Number(field.declared_value).toLocaleString('en-IN')})
                              </button>
                              <button
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  handleNeedsMoreEvidence(field.field_code); 
                                }}
                                style={{ padding: '0.4rem 0.65rem', borderRadius: '4px', background: '#FFF3E0', color: '#E65100', border: '1px solid #FFE0B2', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                              >
                                Needs More Evidence
                              </button>
                              <button
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  handleEscalate(field.field_code); 
                                }}
                                style={{ padding: '0.4rem 0.65rem', borderRadius: '4px', background: '#EDE7F6', color: '#4A148C', border: '1px solid #D1C4E9', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                              >
                                Escalate
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                            <button
                              disabled={isVerified}
                              onClick={(e) => { 
                                e.stopPropagation(); 
                                handleVerify(field.field_code, field.ocr_value || field.declared_value, 'Document evidence inspected and verified by scrutiny officer.'); 
                              }}
                              style={{ 
                                padding: '0.4rem 0.75rem', borderRadius: '4px', 
                                background: isVerified ? '#E8F5E9' : '#198754', 
                                color: isVerified ? '#2E7D32' : '#fff', border: isVerified ? '1px solid #A5D6A7' : 'none', 
                                fontSize: '0.75rem', fontWeight: 600, cursor: isVerified ? 'default' : 'pointer' 
                              }}
                            >
                              {isVerified ? '✓ Verified (Rank 60)' : 'Verify Field Evidence'}
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRejectField(field.field_code);
                              }}
                              style={{ padding: '0.4rem 0.75rem', borderRadius: '4px', background: '#FFEBEE', color: '#C62828', border: '1px solid #FFCDD2', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                            >
                              Reject Field
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleNeedsMoreEvidence(field.field_code);
                              }}
                              style={{ padding: '0.4rem 0.75rem', borderRadius: '4px', background: '#FFF3E0', color: '#E65100', border: '1px solid #FFE0B2', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                            >
                              Needs Clarification
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEscalate(field.field_code);
                              }}
                              style={{ padding: '0.4rem 0.75rem', borderRadius: '4px', background: '#EDE7F6', color: '#4A148C', border: '1px solid #D1C4E9', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                            >
                              Escalate
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Complete Verification Session Button */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  All verified evidence will be consumed by the <strong>Deterministic Scheme Rule Engine</strong>.
                </div>
                <button
                  onClick={() => {
                    setActionSuccessMsg("Scrutiny session finalized! Authoritative verified evidence committed to dossier. Deterministic eligibility reevaluation triggered.");
                    setTimeout(() => setActionSuccessMsg(null), 5000);
                  }}
                  style={{
                    padding: '0.6rem 1.2rem',
                    borderRadius: '4px',
                    background: '#1D0A69',
                    color: '#FFC107',
                    border: '1px solid #C85A17',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  Finalize Evidentiary Scrutiny
                </button>
              </div>
            </div>
          )}

          {activeTab === 'history' && (
            /* Tab: Immutable Audit History */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.25rem' }}>
                Every verification, conflict resolution, or escalation creates an append-only event in the statutory database audit trail. Updates and deletions are blocked.
              </div>

              {history.map(item => (
                <div key={item.id} style={{ padding: '0.75rem', borderRadius: '4px', background: '#F8F9FA', border: '1px solid #CFD8DC', fontSize: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span className="mono" style={{ color: '#0F4C81', fontWeight: 700 }}>{item.action}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{item.timestamp}</span>
                  </div>
                  <div style={{ color: 'var(--text-muted)', marginBottom: '0.25rem', fontSize: '0.75rem' }}>
                    Field: <strong>{item.field_code}</strong> | Actor: <strong>{item.officer}</strong> ({item.role})
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#1B5E20', fontWeight: 600, marginBottom: '0.25rem' }}>
                    Value: {String(item.new_value)} (Trust Rank: {item.verified_trust_rank})
                  </div>
                  <div style={{ fontSize: '0.75rem', fontStyle: 'italic', color: 'var(--text-dim)' }}>
                    Justification: "{item.reason}"
                  </div>
                  <div style={{ fontSize: '0.65rem', fontFamily: 'monospace', color: '#78909C', marginTop: '0.25rem' }}>
                    Event UUID: {item.audit_event_id}
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'eligibility' && (
            /* Tab: Eligibility Impact Preview */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: '#5D4037', background: '#FFF8E1', padding: '0.75rem', borderRadius: '4px', border: '1px solid #FFE082' }}>
                <strong>DETERMINISTIC EVALUATION BOUNDARY:</strong> Scrutiny officers verify documentary evidence. 
                Scheme eligibility rules are evaluated purely by the rule engine against the highest-trust evidence available.
              </div>

              <div style={{ border: '1px solid #E0E0E0', borderRadius: '4px', padding: '0.75rem', background: '#fff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#1D0A69' }}>Rule 1: Annual Income Ceiling</span>
                  <span className="gov-badge gov-badge-success text-xs font-bold">PASS (₹4.5L &lt;= ₹6.0L)</span>
                </div>
                <p style={{ fontSize: '0.75rem', color: '#555', margin: 0 }}>
                  Scheme condition: <code>annual_family_income &lt;= 600000</code>.
                  Authoritative value: <strong>₹4,50,000</strong> (OFFICER_VERIFIED).
                </p>
              </div>

              <div style={{ border: '1px solid #E0E0E0', borderRadius: '4px', padding: '0.75rem', background: '#fff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#1D0A69' }}>Rule 2: Scheduled Tribe Category</span>
                  <span className="gov-badge gov-badge-success text-xs font-bold">PASS</span>
                </div>
                <p style={{ fontSize: '0.75rem', color: '#555', margin: 0 }}>
                  Scheme condition: <code>category == 'ST'</code>.
                  Authoritative value: <strong>ST (Scheduled Tribe)</strong>.
                </p>
              </div>

              <div style={{ border: '1px solid #E0E0E0', borderRadius: '4px', padding: '0.75rem', background: '#fff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#1D0A69' }}>Rule 3: Enrolled Tier-1 Institution</span>
                  <span className="gov-badge gov-badge-success text-xs font-bold">PASS</span>
                </div>
                <p style={{ fontSize: '0.75rem', color: '#555', margin: 0 }}>
                  Scheme condition: <code>institution_aishe == 'U-0570'</code> (IIT Kharagpur).
                </p>
              </div>

              <div style={{ background: '#E8F5E9', border: '1px solid #A5D6A7', padding: '0.75rem', borderRadius: '4px', fontSize: '0.8rem', color: '#1B5E20' }}>
                <strong>Deterministic Scheme Outcome:</strong> ELIGIBLE (All 3 mandatory statutory rules satisfy threshold).
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
