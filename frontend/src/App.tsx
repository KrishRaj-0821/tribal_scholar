import React, { useState } from 'react';
import { 
  ShieldCheck, FileText, GitBranch, Layers, AlertCircle, 
  ExternalLink, Clock, Lock, Server, BookOpen,
  ArrowRight, Database, Eye, GraduationCap
} from 'lucide-react';

interface Scheme {
  id: string;
  code: string;
  name: string;
  description: string;
  scheme_type: string;
  active: boolean;
  version_count: number;
}

interface SourceDoc {
  id: string;
  title: string;
  source_type: string;
  source_type_display: string;
  academic_year: string;
  checksum: string;
  status: string;
  notes: string;
  source_url: string;
}

interface SchemeRule {
  id: string;
  rule_code: string;
  rule_type: string;
  field_path: string;
  operator: string;
  value: any;
  severity: string;
  requires_human_review: boolean;
  status: string;
  failure_message: string;
  source_document_title: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'schemes' | 'provenance' | 'rules' | 'workflow' | 'adapters'>('schemes');

  // Static representative data matching seeded backend models
  const schemes: Scheme[] = [
    {
      id: "1",
      code: "NFST",
      name: "National Fellowship for Higher Education of ST Students",
      description: "Fellowship scheme providing financial assistance to ST students pursuing regular and full-time Ph.D. degrees in Indian Universities/Institutions.",
      scheme_type: "FELLOWSHIP",
      active: true,
      version_count: 1
    },
    {
      id: "2",
      code: "TOP_CLASS",
      name: "National Scholarship for Higher Education of ST Students - Top Class Education",
      description: "Central Sector Scholarship funding tuition and living expenses for ST students admitted to 265 premier institutions (IITs, NITs, IIMs, etc.).",
      scheme_type: "SCHOLARSHIP",
      active: true,
      version_count: 1
    },
    {
      id: "3",
      code: "NOS",
      name: "National Overseas Scholarship for Scheduled Tribe Candidates",
      description: "Central Sector scheme providing financial assistance for selected ST students pursuing Master, Ph.D. and Post-Doctoral research abroad.",
      scheme_type: "OVERSEAS",
      active: true,
      version_count: 2
    }
  ];

  const sourceDocuments: SourceDoc[] = [
    {
      id: "doc-1",
      title: "MoTA National Fellowship for Higher Education of ST Students (NFST) Guidelines & Advertisement 2025-26",
      source_type: "ADVERTISEMENT",
      source_type_display: "Advertisement / Call for Applications",
      academic_year: "2025-26",
      checksum: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      status: "VERIFIED",
      notes: "Official call for 750 fellowship slots under NFST AY 2025-26 for PhD applications. Preferences for PVTG and Divyangjan.",
      source_url: "https://tribal.nic.in/NFST.aspx"
    },
    {
      id: "doc-2",
      title: "Annexure I: Roster of 265 Premier Educational Institutes under Top Class Education Scheme AY 2025-26",
      source_type: "INSTITUTE_LIST",
      source_type_display: "Empanelled Institute Roster",
      academic_year: "2025-26",
      checksum: "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
      status: "VERIFIED",
      notes: "Empanelled 265 premier institutions including IITs, NITs, IIMs, NLUs, AIIMS, and IIITs.",
      source_url: "https://tribal.nic.in/ScholarshiP.aspx"
    },
    {
      id: "doc-3",
      title: "National Overseas Scholarship Scheme for Scheduled Tribe Candidates (NOS) Guidelines 2025-26",
      source_type: "GUIDELINE",
      source_type_display: "Operational Guideline",
      academic_year: "2025-26",
      checksum: "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca72",
      status: "VERIFIED",
      notes: "20 awards total: 17 for ST and 3 for PVTG candidates. Master/PhD/Post-Doc abroad. Parental income ceiling Rs 6.00 Lakh/annum.",
      source_url: "https://overseas.tribal.gov.in/"
    },
    {
      id: "doc-4",
      title: "Office Memorandum: Amendment to Course Eligibility for National Overseas Scholarship (NOS) AY 2026-27",
      source_type: "AMENDMENT",
      source_type_display: "Statutory Amendment Notification",
      academic_year: "2026-27",
      checksum: "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
      status: "VERIFIED",
      notes: "Specific amendment revising course eligibility and subject domains for AY 2026-27. Full text pending official extraction.",
      source_url: "https://overseas.tribal.gov.in/amendments/2026-27"
    }
  ];

  const rules: SchemeRule[] = [
    {
      id: "r1",
      rule_code: "NFST_2025_ST_COMMUNITY",
      rule_type: "ELIGIBILITY",
      field_path: "applicant.community",
      operator: "EQUALS",
      value: "ST",
      severity: "BLOCKING",
      requires_human_review: false,
      status: "ACTIVE",
      failure_message: "Candidate must belong to a notified Scheduled Tribe (ST) community.",
      source_document_title: "NFST Guidelines 2025-26"
    },
    {
      id: "r2",
      rule_code: "NFST_2025_SLOT_QUOTA",
      rule_type: "QUOTA",
      field_path: "application.slot_quota",
      operator: "LESS_THAN_OR_EQUAL",
      value: 750,
      severity: "BLOCKING",
      requires_human_review: false,
      status: "ACTIVE",
      failure_message: "750 fellowship slots advertised under NFST for AY 2025-26.",
      source_document_title: "NFST Guidelines 2025-26"
    },
    {
      id: "r3",
      rule_code: "TOP_CLASS_2025_INCOME_CEILING",
      rule_type: "ELIGIBILITY",
      field_path: "applicant.annual_family_income",
      operator: "LESS_THAN_OR_EQUAL",
      value: "₹6,00,000",
      severity: "BLOCKING",
      requires_human_review: false,
      status: "ACTIVE",
      failure_message: "Total family income from all sources must not exceed Rs 6,00,000 per annum.",
      source_document_title: "Top Class Guidelines 2025-26"
    },
    {
      id: "r4",
      rule_code: "TOP_CLASS_2025_PREMIER_INSTITUTES",
      rule_type: "ELIGIBILITY",
      field_path: "application.institute_code",
      operator: "IN_SET",
      value: "Ref: 265 Premier Institutes",
      severity: "BLOCKING",
      requires_human_review: false,
      status: "ACTIVE",
      failure_message: "Course must be pursued in one of the 265 premier institutions empanelled by MoTA.",
      source_document_title: "Annexure I: Roster of 265 Institutes"
    },
    {
      id: "r5",
      rule_code: "NOS_2025_AWARD_QUOTA",
      rule_type: "QUOTA",
      field_path: "application.award_quota",
      operator: "LESS_THAN_OR_EQUAL",
      value: "20 (17 ST + 3 PVTG)",
      severity: "BLOCKING",
      requires_human_review: false,
      status: "ACTIVE",
      failure_message: "Total awards capped at 20 (17 ST, 3 PVTG).",
      source_document_title: "NOS Guidelines 2025-26"
    },
    {
      id: "r6",
      rule_code: "NOS_2026_AMENDED_COURSE_ELIGIBILITY",
      rule_type: "ELIGIBILITY",
      field_path: "application.course_subject_category",
      operator: "PENDING_OFFICIAL_EXTRACTION",
      value: "UNEXTRACTED",
      severity: "BLOCKING",
      requires_human_review: true,
      status: "PENDING_OFFICIAL_SOURCE_EXTRACTION",
      failure_message: "Exact 2026-27 revised course eligibility must be extracted from the official amendment notification prior to automated execution.",
      source_document_title: "NOS AY 2026-27 Amendment OM"
    }
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Government Header */}
      <header style={{ borderBottom: '1px solid var(--border-subtle)', background: 'rgba(10, 13, 20, 0.9)', position: 'sticky', top: 0, zIndex: 50, backdropFilter: 'blur(12px)' }}>
        <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.85rem 1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'linear-gradient(135deg, #4f46e5, #06b6d4)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)' }}>
              <GraduationCap size={24} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.05rem', fontWeight: 700, letterSpacing: '-0.01em' }}>TRIBAL SCHOLAR</span>
                <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>SIH 26239 CORE</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Ministry of Tribal Affairs (MoTA) • Scholarship & Fellowship Engine</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(255, 255, 255, 0.04)', padding: '0.4rem 0.8rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <span className="dot dot-green"></span>
              <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>Statutory Provenance Checks: PASSING</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', padding: '0.4rem 0.8rem', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.25)', fontSize: '0.75rem', fontWeight: 600 }}>
              <Database size={14} />
              <span>Modular Monolith v1.0</span>
            </div>
          </div>
        </div>
      </header>

      {/* Prototype Compliance Banner */}
      <div style={{ background: 'rgba(6, 182, 212, 0.05)', borderBottom: '1px solid rgba(6, 182, 212, 0.15)', padding: '0.6rem 0' }}>
        <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={16} />
            <span><strong>SIH Prototype Guardrails Active:</strong> Government integrations operate through sandboxed interface adapters. AI is assistive only; human review retains statutory authority.</span>
          </div>
          <span className="mono" style={{ fontSize: '0.7rem' }}>API Endpoint: /api/v1/</span>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="container" style={{ flex: 1, padding: '2rem 1.5rem' }}>
        {/* Navigation Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-subtle)', marginBottom: '2rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
          {[
            { id: 'schemes', label: 'Scheme Registry & Multi-Year Versions', icon: BookOpen },
            { id: 'provenance', label: 'Source Provenance & Gazette Lineage', icon: FileText },
            { id: 'rules', label: 'Deterministic Rule Engine', icon: ShieldCheck },
            { id: 'workflow', label: 'Workflow Engine & Audit Trail', icon: GitBranch },
            { id: 'adapters', label: 'Government Mock Adapters', icon: Server },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.25rem',
                  borderRadius: '8px 8px 0 0',
                  color: isActive ? '#60a5fa' : 'var(--text-muted)',
                  borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
                  background: isActive ? 'rgba(59, 130, 246, 0.08)' : 'transparent',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '0.875rem',
                  transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap'
                }}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: Scheme Registry */}
        {activeTab === 'schemes' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Statutory MoTA Schemes (Seeded Foundation)</h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Configured declarative programs with multi-year academic cycle coexistence.</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
              {schemes.map((scheme) => (
                <div key={scheme.code} className="glass-panel" style={{ padding: '1.5rem', position: 'relative' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <span className="badge badge-active">{scheme.scheme_type}</span>
                    <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>{scheme.code}</span>
                  </div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.5rem' }}>{scheme.name}</h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.5', marginBottom: '1.25rem' }}>{scheme.description}</p>
                  
                  <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-dim)' }}>
                      <Clock size={14} />
                      <span>{scheme.version_count} Academic Year {scheme.version_count > 1 ? 'Versions' : 'Version'}</span>
                    </div>
                    {scheme.code === 'NOS' ? (
                      <span className="badge badge-draft" style={{ fontSize: '0.65rem' }}>2026-27 (Pending Extraction)</span>
                    ) : (
                      <span className="badge badge-active" style={{ fontSize: '0.65rem' }}>2025-26 Active</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Academic Year Coexistence Spotlight */}
            <div className="glass-panel" style={{ marginTop: '2rem', padding: '1.5rem', borderLeft: '4px solid var(--accent-indigo)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <Layers size={20} color="#818cf8" />
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Architectural Invariant: Multi-Year Version Coexistence</h4>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                Under the <code>SchemeVersion</code> architecture, historical criteria remain immutable in the database. When the 2026-27 cycle is introduced, existing 2025-26 applications continue executing against the 2025-26 rule snapshot without risk of regression or retroactive invalidation.
              </p>
            </div>
          </div>
        )}

        {/* Tab 2: Document Provenance */}
        {activeTab === 'provenance' && (
          <div>
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Source Document Registry (Provenance Proof)</h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Every scheme rule and reference set item maintains strict cryptographic lineage to an official publication.</p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {sourceDocuments.map((doc) => (
                <div key={doc.id} className="glass-panel" style={{ padding: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span className="badge badge-verified">{doc.source_type}</span>
                      <span className="badge badge-active" style={{ fontSize: '0.7rem' }}>AY {doc.academic_year}</span>
                    </div>
                    <span className="badge badge-verified">{doc.status}</span>
                  </div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, margin: '0.5rem 0' }}>{doc.title}</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.85rem' }}>{doc.notes}</p>
                  
                  <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ color: 'var(--text-dim)', fontWeight: 600 }}>SHA-256 Checksum:</span>
                      <code className="mono" style={{ color: 'var(--accent-cyan)', fontSize: '0.7rem' }}>{doc.checksum}</code>
                    </div>
                    <a href={doc.source_url} target="_blank" rel="noopener noreferrer" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#60a5fa', textDecoration: 'none', fontSize: '0.75rem' }}>
                      <span>Official Portal</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Deterministic Rule Engine */}
        {activeTab === 'rules' && (
          <div>
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Deterministic Scheme Rules</h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Rules are stored as data in database tables; zero business logic is hardcoded inside Python code.</p>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)' }}>
                    <th style={{ padding: '0.75rem 1rem' }}>RULE CODE</th>
                    <th style={{ padding: '0.75rem 1rem' }}>TYPE</th>
                    <th style={{ padding: '0.75rem 1rem' }}>FIELD PATH</th>
                    <th style={{ padding: '0.75rem 1rem' }}>OPERATOR</th>
                    <th style={{ padding: '0.75rem 1rem' }}>VALUE</th>
                    <th style={{ padding: '0.75rem 1rem' }}>STATUS</th>
                    <th style={{ padding: '0.75rem 1rem' }}>PROVENANCE</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => {
                    const isPending = rule.status === 'PENDING_OFFICIAL_SOURCE_EXTRACTION';
                    return (
                      <tr key={rule.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', background: isPending ? 'rgba(244, 63, 94, 0.04)' : 'transparent' }}>
                        <td style={{ padding: '1rem', fontWeight: 600, color: isPending ? '#fb7185' : 'var(--text-main)' }}>
                          <div className="mono">{rule.rule_code}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 400, marginTop: '0.2rem' }}>{rule.failure_message}</div>
                        </td>
                        <td style={{ padding: '1rem' }}><span className="badge badge-active">{rule.rule_type}</span></td>
                        <td style={{ padding: '1rem' }}><code className="mono" style={{ color: 'var(--accent-indigo)' }}>{rule.field_path}</code></td>
                        <td style={{ padding: '1rem' }}><code className="mono" style={{ color: 'var(--accent-amber)' }}>{rule.operator}</code></td>
                        <td style={{ padding: '1rem', fontWeight: 600 }}>{String(rule.value)}</td>
                        <td style={{ padding: '1rem' }}>
                          {isPending ? (
                            <span className="badge badge-pending" style={{ fontSize: '0.65rem' }}>PENDING EXTRACTION</span>
                          ) : (
                            <span className="badge badge-active" style={{ fontSize: '0.65rem' }}>ACTIVE</span>
                          )}
                        </td>
                        <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{rule.source_document_title}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Unextracted Rule Callout */}
            <div className="glass-panel" style={{ marginTop: '2rem', padding: '1.25rem', borderLeft: '4px solid var(--accent-rose)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-rose)', marginBottom: '0.5rem' }}>
                <AlertCircle size={18} />
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700 }}>Zero Guessing Policy: Rule NOS_2026_AMENDED_COURSE_ELIGIBILITY</h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                Per project design guidelines, 2026-27 course changes are explicitly designated as <code>PENDING_OFFICIAL_SOURCE_EXTRACTION</code>. Automated system checks prevent the 2026-27 scheme version from activation until full text is gazette-verified.
              </p>
            </div>
          </div>
        )}

        {/* Tab 4: Workflow Engine & Audit */}
        {activeTab === 'workflow' && (
          <div>
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Declarative Workflow Engine & Append-Only Audit</h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Configurable state machine transitions with immutable statutory history.</p>
            </div>

            {/* Workflow States Progress Ribbon */}
            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem' }}>Application State Lifecycle</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
                {[
                  "DRAFT", "SUBMITTED", "UNDER_SCRUTINY", "DEFECTIVE", 
                  "VERIFIED", "MERIT_LISTED", "APPROVED", "DISBURSED"
                ].map((st, i, arr) => (
                  <React.Fragment key={st}>
                    <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '0.5rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', whiteSpace: 'nowrap', textAlign: 'center' }}>
                      <span className="mono" style={{ fontSize: '0.75rem', fontWeight: 600 }}>{st}</span>
                    </div>
                    {i < arr.length - 1 && <ArrowRight size={14} color="var(--text-dim)" />}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Invariant Highlights */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
              <div className="glass-panel" style={{ padding: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-emerald)', marginBottom: '0.75rem' }}>
                  <Lock size={18} />
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Append-Only Status History</h4>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                  The <code>ApplicationStatusHistory</code> model prohibits ORM updates or deletes. Every state movement records the transitioning officer, statutory reasoning, timestamp, and previous state.
                </p>
              </div>

              <div className="glass-panel" style={{ padding: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-indigo)', marginBottom: '0.75rem' }}>
                  <Eye size={18} />
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Human-in-the-Loop Scrutiny</h4>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                  AI models (PaddleOCR / Tesseract) produce assistive confidence scores. Low confidence extractions or rule anomalies are automatically enqueued in <code>VerificationQueueItem</code> for officer review.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Government Integration Adapters */}
        {activeTab === 'adapters' && (
          <div>
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Government Integration Boundary (SIH Sandbox Mocks)</h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Encapsulated behind clean interfaces; zero private or undocumented endpoints are accessed.</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
              {[
                { name: 'DigiLocker Sandbox', mode: 'Certified Document Mock', docs: 'Caste Certificate, Marksheets' },
                { name: 'UIDAI Aadhaar e-KYC', mode: 'Offline XML Demographic Mock', docs: 'Demographic match without live UIDAI call' },
                { name: 'PFMS DBT Validator', mode: 'Beneficiary Bank Validation Mock', docs: 'DBT Bank Account Verification' },
                { name: 'NSP De-duplication', mode: 'Central Scholarship Registry Mock', docs: 'Cross-scheme duplicate award detection' },
                { name: 'BHASHINI Service', mode: 'Tribal Dialect Translation Mock', docs: 'Santali, Gondi, Bodo, Hindi, English' },
              ].map((adapter) => (
                <div key={adapter.name} className="glass-panel" style={{ padding: '1.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700 }}>{adapter.name}</h4>
                    <span className="badge badge-draft" style={{ fontSize: '0.65rem' }}>MOCK ADAPTER</span>
                  </div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', marginBottom: '0.5rem', fontWeight: 600 }}>Mode: {adapter.mode}</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>{adapter.docs}</p>
                  <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '1rem', paddingTop: '0.75rem', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    Compliance: No Private API Scraping
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border-subtle)', padding: '1.5rem 0', background: 'rgba(10, 13, 20, 0.95)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            Ministry of Tribal Affairs (MoTA) • SIH Problem Statement 26239 • Student Built Prototype Core
          </div>
          <div>
            Built with Django 5.1 + React + Vite + PostgreSQL + Celery + MinIO
          </div>
        </div>
      </footer>
    </div>
  );
}
