import { useState } from 'react';
import { 
  FileText, CheckCircle, AlertTriangle, RefreshCw, Info
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

interface VerificationField {
  field_code: string;
  label: string;
  declared_value: any;
  ocr_value: any;
  verified_value: any;
  status: 'PENDING' | 'VERIFIED' | 'REJECTED' | 'CONFLICT' | 'NEEDS_REVIEW';
  confidence: number;
  evidence_text: string;
  page_number: number;
  block_id: string;
  has_conflict: boolean;
}

interface VerificationHistoryEvent {
  id: string;
  field_code: string;
  action: string;
  previous_value: any;
  new_value: any;
  officer: string;
  role: string;
  timestamp: string;
  reason: string;
}

export default function VerificationWorkbench() {
  const [selectedFieldCode, setSelectedFieldCode] = useState<string>('annual_family_income');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activeHistoryTab, setActiveHistoryTab] = useState<'fields' | 'history'>('fields');
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Sample document fields for ST Income Certificate review
  const [fields, setFields] = useState<VerificationField[]>([
    {
      field_code: 'annual_family_income',
      label: 'Annual Family Income',
      declared_value: 500000,
      ocr_value: 450000,
      verified_value: null,
      status: 'CONFLICT',
      confidence: 0.94,
      evidence_text: 'वार्षिक पारिवारिक आय: 450000 रुपये',
      page_number: 1,
      block_id: 'block-income-01',
      has_conflict: true,
    },
    {
      field_code: 'certificate_number',
      label: 'Certificate Number',
      declared_value: 'INC-2026-00124',
      ocr_value: 'INC-2026-00124',
      verified_value: 'INC-2026-00124',
      status: 'VERIFIED',
      confidence: 0.98,
      evidence_text: 'प्रमाण पत्र संख्या: INC-2026-00124',
      page_number: 1,
      block_id: 'block-cert-02',
      has_conflict: false,
    },
    {
      field_code: 'issuing_authority',
      label: 'Issuing Authority',
      declared_value: 'SDM Ranchi',
      ocr_value: 'कार्यालय अनुमंडल पदाधिकारी, रांची',
      verified_value: null,
      status: 'PENDING',
      confidence: 0.92,
      evidence_text: 'कार्यालय अनुमंडल पदाधिकारी, रांची (SDM Ranchi)',
      page_number: 1,
      block_id: 'block-auth-03',
      has_conflict: false,
    },
    {
      field_code: 'issue_date',
      label: 'Date of Issue',
      declared_value: '2026-01-15',
      ocr_value: '15/01/2026',
      verified_value: null,
      status: 'PENDING',
      confidence: 0.96,
      evidence_text: 'दिनांक: 15/01/2026',
      page_number: 1,
      block_id: 'block-date-04',
      has_conflict: false,
    }
  ]);

  const [history, setHistory] = useState<VerificationHistoryEvent[]>([
    {
      id: 'hist-01',
      field_code: 'certificate_number',
      action: 'FIELD_VERIFIED',
      previous_value: null,
      new_value: 'INC-2026-00124',
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: '2026-09-30 02:15:22 UTC',
      reason: 'Certificate number matches district portal QR verification hash.'
    },
    {
      id: 'hist-00',
      field_code: 'document_level',
      action: 'DOCUMENT_VERIFICATION_STARTED',
      previous_value: null,
      new_value: 'VERIFICATION_PENDING',
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: '2026-09-30 02:10:00 UTC',
      reason: 'Scrutiny session opened by authorized officer.'
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

  const handleVerify = (fieldCode: string, value: any, reason: string) => {
    setTimeout(() => {
      setFields(prev => prev.map(f => {
        if (f.field_code === fieldCode) {
          return { ...f, verified_value: value, status: 'VERIFIED', has_conflict: false };
        }
        return f;
      }));

      const newEvent: VerificationHistoryEvent = {
        id: `hist-${Date.now()}`,
        field_code: fieldCode,
        action: 'FIELD_VERIFIED',
        previous_value: fields.find(f => f.field_code === fieldCode)?.verified_value,
        new_value: value,
        officer: 'officer_sharma',
        role: 'SCRUTINY_OFFICER',
        timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
        reason: reason || 'Verified by officer based on document evidence.'
      };
      setHistory(prev => [newEvent, ...prev]);
      setActionSuccessMsg(`Field '${fieldCode}' verified as ₹${Number(value).toLocaleString('en-IN') || value}. Trust level promoted to OFFICER_VERIFIED (Rank 50).`);
      setTimeout(() => setActionSuccessMsg(null), 4000);
    }, 100);
  };

  const handleResolveConflict = (fieldCode: string, decision: 'USE_APPLICANT_DECLARATION' | 'USE_DOCUMENT_VALUE' | 'REQUEST_CORRECTION', reason: string) => {
    setTimeout(() => {
      const field = fields.find(f => f.field_code === fieldCode);
      if (!field) return;

      let chosenValue = field.ocr_value;
      let newStatus: VerificationField['status'] = 'VERIFIED';

      if (decision === 'USE_APPLICANT_DECLARATION') {
        chosenValue = field.declared_value;
      } else if (decision === 'REQUEST_CORRECTION') {
        chosenValue = null;
        newStatus = 'NEEDS_REVIEW';
      }

      setFields(prev => prev.map(f => {
        if (f.field_code === fieldCode) {
          return { ...f, verified_value: chosenValue, status: newStatus, has_conflict: false };
        }
        return f;
      }));

      const newEvent: VerificationHistoryEvent = {
        id: `hist-${Date.now()}`,
        field_code: fieldCode,
        action: 'FIELD_CONFLICT_RESOLVED',
        previous_value: `Declared: ${field.declared_value} vs OCR: ${field.ocr_value}`,
        new_value: `${decision} -> ${chosenValue}`,
        officer: 'officer_sharma',
        role: 'SCRUTINY_OFFICER',
        timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
        reason: reason || `Conflict resolved using ${decision}`
      };
      setHistory(prev => [newEvent, ...prev]);
      setActionSuccessMsg(`Conflict resolved: ${decision} chosen. Deterministic eligibility engine now receives authoritative evidence.`);
      setTimeout(() => setActionSuccessMsg(null), 4000);
    }, 100);
  };

  const handleReopen = () => {
    const reason = prompt("Enter justification reason for reopening verification session:");
    if (!reason) return;

    setFields(prev => prev.map(f => ({ ...f, status: 'NEEDS_REVIEW' })));
    const newEvent: VerificationHistoryEvent = {
      id: `hist-${Date.now()}`,
      field_code: 'document_level',
      action: 'DOCUMENT_VERIFICATION_REOPENED',
      previous_value: 'COMPLETED',
      new_value: 'NEEDS_REVIEW',
      officer: 'officer_sharma',
      role: 'SCRUTINY_OFFICER',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: reason
    };
    setHistory(prev => [newEvent, ...prev]);
    setActionSuccessMsg("Verification session reopened. All previous historical events remain preserved.");
    setTimeout(() => setActionSuccessMsg(null), 4000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header Bar */}
      <div className="gov-card flex flex-wrap justify-between items-center gap-4">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <span className="gov-badge gov-badge-info">PHASE 8 WORKBENCH</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Application #<strong>APP-2026-NFST-0881</strong></span>
            <span className="gov-badge gov-badge-success">SAFE STORAGE</span>
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#1D0A69' }}>Human-in-the-Loop Document Evidence Scrutiny</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
            Verifying Officer: <strong>officer_sharma (SCRUTINY_OFFICER)</strong> | Separation of Duties Enforced Server-Side
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button 
            onClick={handleReopen}
            className="gov-btn gov-btn-danger text-xs"
          >
            <RefreshCw size={14} /> Reopen Verification
          </button>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textAlign: 'right' }}>
            <div>Trust Rank: <strong>OFFICER (50)</strong></div>
            <div>Immutability: <strong>APPEND-ONLY</strong></div>
          </div>
        </div>
      </div>

      {/* Success Notification Alert */}
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

      {/* Core Principle Mandate Banner */}
      <div style={{
        background: '#FFF9C4', borderLeft: '4px solid #FFC107',
        borderTop: '1px solid #FFE082', borderRight: '1px solid #FFE082', borderBottom: '1px solid #FFE082',
        borderRadius: '4px', padding: '0.75rem 1rem', fontSize: '0.8rem', color: '#7A5E00',
        display: 'flex', alignItems: 'center', gap: '0.75rem'
      }}>
        <Info size={18} style={{ flexShrink: 0, color: '#C85A17' }} />
        <span>
          <strong>STATUTORY BOUNDARY:</strong> The verifying officer validates documentary evidence; the officer does NOT directly alter eligibility. 
          Eligibility decisions remain strictly evaluated by the deterministic scheme rule engine against verified evidence.
        </span>
      </div>

      {/* Main 2-Column Split: Document Viewer (Left) vs Verification Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: Document Evidence Viewer with OCR Bounding Box Overlay */}
        <div className="glass-panel lg:col-span-7" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={18} color="#60a5fa" />
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>Document Evidence Canvas</h3>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                ST Income Certificate (income_cert_2026.png) | Page 1 of 1
              </span>
            </div>
            
            {/* Zoom Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
              <button 
                onClick={() => setZoomLevel(prev => Math.max(80, prev - 10))}
                style={{ padding: '0.25rem 0.5rem', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)', color: 'var(--text-main)', cursor: 'pointer' }}
              >-</button>
              <span className="mono">{zoomLevel}%</span>
              <button 
                onClick={() => setZoomLevel(prev => Math.min(140, prev + 10))}
                style={{ padding: '0.25rem 0.5rem', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)', color: 'var(--text-main)', cursor: 'pointer' }}
              >+</button>
            </div>
          </div>

          {/* Interactive Document Image Container */}
          <div style={{ 
            position: 'relative', 
            background: '#0d1117', 
            borderRadius: '8px', 
            border: '1px solid #30363d',
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
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>कार्यालय अनुमंडल पदाधिकारी, रांची / Sub-Divisional Magistrate Office, Ranchi</div>
              </div>

              {/* Document Body Lines */}
              <div style={{ lineHeight: '2.2', fontSize: '0.85rem' }}>
                <div>प्रमाण पत्र संख्या / Certificate No: <strong>INC-2026-00124</strong></div>
                <div>आवेदक का नाम / Applicant Name: <strong>श्री अर्जुन मुंडा (Shri Arjun Munda)</strong></div>
                <div>पिता का नाम / Father's Name: <strong>श्री बिरसा मुंडा (Shri Birsa Munda)</strong></div>
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
                  <div style={{ fontStyle: 'italic', fontWeight: 600 }}>अनुमंडल पदाधिकारी / SDM</div>
                  <div>रांची, झारखंड (Ranchi, Jharkhand)</div>
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
                      stroke={isSelected ? '#2563eb' : 'rgba(234, 88, 12, 0.4)'}
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
                Active Field Focus
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{ width: 10, height: 10, border: '1px dashed #ea580c', display: 'inline-block', borderRadius: 2 }} />
                PaddleOCR Text Block
              </span>
            </div>
            <span className="mono">Decompression Safe (Lanczos Bounded)</span>
          </div>
        </div>

        {/* RIGHT COLUMN: Verification & Conflict Resolution Panel */}
        <div className="glass-panel lg:col-span-5" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* Panel Tab Navigation: Fields vs Audit Trail */}
          <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.5rem' }}>
            <button 
              onClick={() => setActiveHistoryTab('fields')}
              style={{
                background: activeHistoryTab === 'fields' ? '#E1F5FE' : 'transparent',
                color: activeHistoryTab === 'fields' ? '#01579B' : 'var(--text-muted)',
                border: activeHistoryTab === 'fields' ? '1px solid #B3E5FC' : '1px solid transparent',
                padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer'
              }}
            >
              Extracted Fields ({fields.length})
            </button>
            <button 
              onClick={() => setActiveHistoryTab('history')}
              style={{
                background: activeHistoryTab === 'history' ? '#E1F5FE' : 'transparent',
                color: activeHistoryTab === 'history' ? '#01579B' : 'var(--text-muted)',
                border: activeHistoryTab === 'history' ? '1px solid #B3E5FC' : '1px solid transparent',
                padding: '0.4rem 0.8rem', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer'
              }}
            >
              Immutable Audit History ({history.length})
            </button>
          </div>

          {activeHistoryTab === 'fields' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Field Cards */}
              {fields.map(field => {
                const isSelected = field.field_code === selectedFieldCode;
                const isConflict = field.status === 'CONFLICT' || field.has_conflict;
                const isVerified = field.status === 'VERIFIED';

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
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{field.field_code}</span>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: '#1D0A69' }}>{field.label}</h4>
                      </div>
                      
                      {isConflict && (
                        <span className="gov-badge gov-badge-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <AlertTriangle size={12} /> CONFLICT DETECTED
                        </span>
                      )}
                      {isVerified && (
                        <span className="gov-badge gov-badge-success" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <CheckCircle size={12} /> OFFICER VERIFIED
                        </span>
                      )}
                      {field.status === 'PENDING' && (
                        <span className="gov-badge gov-badge-warning">
                          PENDING REVIEW
                        </span>
                      )}
                      {field.status === 'NEEDS_REVIEW' && (
                        <span className="gov-badge gov-badge-info">
                          REOPENED / REVIEW
                        </span>
                      )}
                    </div>

                    {/* Comparison Grid: Declared vs OCR */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', background: '#F4F6F8', border: '1px solid #ECEFF1', padding: '0.6rem 0.75rem', borderRadius: '4px', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
                      <div>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Applicant Declared:</span>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                          {typeof field.declared_value === 'number' ? `₹${field.declared_value.toLocaleString('en-IN')}` : String(field.declared_value)}
                        </div>
                      </div>
                      <div>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>OCR Extracted (Prov):</span>
                        <div style={{ fontWeight: 600, color: isConflict ? '#A71D2A' : '#0288D1' }}>
                          {typeof field.ocr_value === 'number' ? `₹${field.ocr_value.toLocaleString('en-IN')}` : String(field.ocr_value)}
                        </div>
                      </div>
                    </div>

                    {/* Evidence Snippet & Confidence */}
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontStyle: 'italic', maxWidth: '75%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        Source: "{field.evidence_text}"
                      </span>
                      <span className="mono" style={{ color: '#34d399' }}>Conf: {(field.confidence * 100).toFixed(0)}%</span>
                    </div>

                    {/* Action Controls for Selected Field */}
                    {isSelected && (
                      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
                        {isConflict ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <div style={{ fontSize: '0.75rem', color: '#f87171', fontWeight: 600 }}>
                              Material Discrepancy: Declared ₹{Number(field.declared_value).toLocaleString('en-IN')} vs Certificate ₹{Number(field.ocr_value).toLocaleString('en-IN')}. Choose evidence-backed resolution:
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleResolveConflict(field.field_code, 'USE_DOCUMENT_VALUE', 'Certificate documentary value accepted by officer.'); }}
                                style={{ padding: '0.4rem 0.75rem', borderRadius: '5px', background: '#2563eb', color: '#fff', border: 'none', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                              >
                                Accept Document Value (₹{Number(field.ocr_value).toLocaleString('en-IN')})
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleResolveConflict(field.field_code, 'USE_APPLICANT_DECLARATION', 'Applicant self-declaration accepted per supplementary gazetted affidavit.'); }}
                                style={{ padding: '0.4rem 0.75rem', borderRadius: '5px', background: 'rgba(255,255,255,0.1)', color: 'var(--text-main)', border: '1px solid var(--border-subtle)', fontSize: '0.75rem', cursor: 'pointer' }}
                              >
                                Keep Declared (₹{Number(field.declared_value).toLocaleString('en-IN')})
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleResolveConflict(field.field_code, 'REQUEST_CORRECTION', 'Discrepancy exceeds tolerance threshold; clarification needed.'); }}
                                style={{ padding: '0.4rem 0.75rem', borderRadius: '5px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', fontSize: '0.75rem', cursor: 'pointer' }}
                              >
                                Request Correction
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              disabled={isVerified}
                              onClick={(e) => { e.stopPropagation(); handleVerify(field.field_code, field.ocr_value || field.declared_value, 'Document evidence inspected and found valid.'); }}
                              style={{ 
                                padding: '0.4rem 0.8rem', borderRadius: '5px', 
                                background: isVerified ? 'rgba(16, 185, 129, 0.2)' : '#10b981', 
                                color: isVerified ? '#34d399' : '#fff', border: 'none', 
                                fontSize: '0.75rem', fontWeight: 600, cursor: isVerified ? 'default' : 'pointer' 
                              }}
                            >
                              {isVerified ? 'Verified & Locked' : 'Verify Field Evidence'}
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const reason = prompt("Enter specific rejection justification:");
                                if (reason) {
                                  setFields(prev => prev.map(f => f.field_code === field.field_code ? { ...f, status: 'REJECTED' } : f));
                                  setActionSuccessMsg(`Field '${field.field_code}' rejected.`);
                                }
                              }}
                              style={{ padding: '0.4rem 0.8rem', borderRadius: '5px', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', fontSize: '0.75rem', cursor: 'pointer' }}
                            >
                              Reject Field
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
                    setActionSuccessMsg("Document verification session finalized! Verified fields committed to application dossier.");
                    setTimeout(() => setActionSuccessMsg(null), 4000);
                  }}
                  style={{
                    padding: '0.6rem 1.2rem',
                    borderRadius: '6px',
                    background: '#2563eb',
                    color: '#fff',
                    border: 'none',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  Complete Document Verification
                </button>
              </div>
            </div>
          ) : (
            /* Tab: Immutable Audit History */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '0.25rem' }}>
                Every verification, conflict resolution, or reopening action creates an immutable event in the statutory database audit trail.
              </div>

              {history.map(item => (
                <div key={item.id} style={{ padding: '0.75rem', borderRadius: '4px', background: '#F8F9FA', border: '1px solid #CFD8DC', fontSize: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span className="mono" style={{ color: '#0F4C81', fontWeight: 700 }}>{item.action}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{item.timestamp}</span>
                  </div>
                  <div style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    Field: <strong>{item.field_code}</strong> | Actor: <strong>{item.officer}</strong> ({item.role})
                  </div>
                  {item.new_value && (
                    <div style={{ color: '#198754', fontSize: '0.75rem', marginBottom: '0.25rem', fontWeight: 600 }}>
                      Value: {String(item.new_value)}
                    </div>
                  )}
                  <div style={{ fontSize: '0.75rem', fontStyle: 'italic', color: 'var(--text-dim)' }}>
                    Justification: "{item.reason}"
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
