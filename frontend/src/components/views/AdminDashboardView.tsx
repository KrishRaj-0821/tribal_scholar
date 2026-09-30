import React, { useState } from 'react';
import { OFFICIAL_MOTA_SCHEMES } from '../../theme/tokens';
import { TribalPattern } from '../common/TribalPattern';
import { 
  ShieldCheck, Download, Settings, 
  Landmark, AlertCircle, CheckCircle2, Save, 
  Calendar, Building, Database
} from 'lucide-react';

export const AdminDashboardView: React.FC = () => {
  const [activeAdminTab, setActiveAdminTab] = useState<'schemes' | 'cycles' | 'rules' | 'institutes' | 'audit'>('schemes');
  const [rule42Active, setRule42Active] = useState(true);
  const [cutoffDate, setCutoffDate] = useState('2025-04-01');
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSaveRule = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const auditLogs = [
    {
      timestamp: '15-Sep-2026 11:42:09 IST',
      ip: '10.14.92.112 (NIC-MoTA-HQ)',
      officer: 'Dr. Vinod Minz (Joint Secretary, MoTA)',
      action: 'RULE_UPDATE',
      resource: 'Rule 4.2 Income Validity Window updated to AY 2026-27 (Cutoff 01-Apr-2025)',
      hash: 'a9f8e431...2e901f',
      dscStatus: 'PASSED (DSC Validated)'
    },
    {
      timestamp: '15-Sep-2026 09:15:33 IST',
      ip: '10.14.92.45 (NIC Cloud Node)',
      officer: 'Automated Daemon (PFMS-BOT)',
      action: 'SYNC_INST',
      resource: '265 Notified Institutes AISHE Data Verified with MoE',
      hash: '7f9b8c34...a312e9',
      dscStatus: 'COMPLETED (Zero Anomalies)'
    },
    {
      timestamp: '14-Sep-2026 17:30:00 IST',
      ip: '10.14.92.112 (NIC-MoTA-HQ)',
      officer: 'Dr. Vinod Minz (Joint Secretary, MoTA)',
      action: 'QUOTA_REALLOC',
      resource: 'NOS State-wise indicative quota revision gazette published',
      hash: 'e42b1088...902fa3',
      dscStatus: 'PUBLISHED (Gazette Ref: MoTA/2026/GZ-88)'
    },
    {
      timestamp: '14-Sep-2026 14:10:19 IST',
      ip: '14.139.58.2 (IIT Kharagpur)',
      officer: 'Prof. S.K. Mahato (Dean Academic Affairs)',
      action: 'BONAFIDE_BULK',
      resource: '42 Bonafide Certificates uploaded for AY 2026-27 candidates',
      hash: 'f8182240...009a12',
      dscStatus: 'VERIFIED'
    }
  ];

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Sovereign Central Admin Masthead */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="community" opacity={0.07} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
                <span>NATIONAL SCHOLARSHIPS GOVERNANCE DIVISION</span>
                <span>•</span>
                <span>CENTRAL LEVEL-4 CLEARANCE</span>
              </div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold font-serif text-white tracking-tight">
                Ministry of Tribal Affairs — Central Governance Console
              </h1>
              <p className="text-xs text-[#EBEAEA]/80">
                Authorized Executive: <strong>Dr. Vinod Minz, Joint Secretary (Scholarships & Higher Education)</strong>
              </p>
            </div>

            {/* DSC Token & SIH Prototype Badge */}
            <div className="flex items-center gap-3">
              <div className="bg-white/10 px-3 py-2 rounded border border-white/20 text-xs space-y-0.5">
                <div className="flex items-center gap-1.5 text-[#81C784] font-bold">
                  <ShieldCheck className="w-4 h-4" />
                  <span>eMudhra Class-3 DSC Active</span>
                </div>
                <div className="text-[11px] text-[#EBEAEA]/70 font-mono">
                  Cert ID: NIC-GOV-MOTA-JS-01
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 2. Admin Navigation Dossier Ribbon */}
      <nav className="bg-white border-b border-[#CFD8DC] sticky top-12 z-30 shadow-xs">
        <div className="gov-container flex items-center gap-1 overflow-x-auto text-xs font-bold">
          {[
            { id: 'schemes', icon: Landmark, label: '1. Statutory Schemes Master' },
            { id: 'cycles', icon: Calendar, label: '2. Academic Cycles & Cutoffs' },
            { id: 'rules', icon: Settings, label: '3. Scheme Rule 4.2 Engine' },
            { id: 'institutes', icon: Building, label: '4. Notified Institutes (265 AISHE)' },
            { id: 'audit', icon: Database, label: '5. Section 4 IT Act Cryptographic Audit' }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeAdminTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveAdminTab(tab.id as any)}
                className={`flex items-center gap-2 py-3 px-4 border-b-2 whitespace-nowrap transition-colors ${
                  isActive
                    ? 'border-[#1D0A69] text-[#1D0A69] bg-[#F4F6F8]'
                    : 'border-transparent text-[#546E7A] hover:text-[#1D0A69] hover:bg-[#F8F9FA]'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#1D0A69]' : 'text-[#90A4AE]'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* 3. Main Admin Work Area */}
      <main className="gov-container py-8 space-y-6">
        
        {/* TAB 1: SCHEMES MASTER */}
        {activeAdminTab === 'schemes' && (
          <div className="bg-white border border-[#CFD8DC] rounded-lg shadow-sm overflow-hidden">
            <div className="p-4 sm:p-6 border-b border-[#ECEFF1] flex flex-wrap items-center justify-between gap-4 bg-[#F8F9FA]">
              <div>
                <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                  Statutory ST Scholarship Schemes Master Repository (AY 2026-27)
                </h2>
                <p className="text-xs text-[#546E7A] mt-0.5">
                  Central Sector & Centrally Sponsored affirmative action schemes governed directly by MoTA.
                </p>
              </div>
              <div className="text-right text-xs">
                <span className="text-[#546E7A] block">Total Annual Allocation:</span>
                <strong className="text-base font-bold text-[#198754] font-serif">₹2,815.00 Crore</strong>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#1D0A69] text-white">
                  <tr>
                    <th className="p-3">Official Code</th>
                    <th className="p-3">Scheme Title</th>
                    <th className="p-3">Target Beneficiaries</th>
                    <th className="p-3">Budget Allocation</th>
                    <th className="p-3">Income Ceiling</th>
                    <th className="p-3">Application Deadline</th>
                    <th className="p-3 text-right">State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#CFD8DC]">
                  {OFFICIAL_MOTA_SCHEMES.map((scheme) => (
                    <tr key={scheme.code} className="hover:bg-[#F8F9FA]">
                      <td className="p-3 font-mono font-bold text-[#1D0A69]">{scheme.officialCode}</td>
                      <td className="p-3">
                        <strong className="text-[#150202] block">{scheme.titleEn}</strong>
                        <span className="text-[11px] text-[#546E7A]">{scheme.gazetteRef}</span>
                      </td>
                      <td className="p-3 text-[#198754] font-bold">{scheme.totalBeneficiariesTarget}</td>
                      <td className="p-3 font-bold text-[#150202]">₹{scheme.annualBudgetCr}.00 Cr</td>
                      <td className="p-3 text-[#546E7A]">{scheme.incomeCeilingEn}</td>
                      <td className="p-3 font-mono text-[#C85A17] font-semibold">{scheme.deadline}</td>
                      <td className="p-3 text-right">
                        <span className="bg-[#E8F5E9] text-[#198754] text-[10px] font-bold px-2 py-0.5 rounded border border-[#A5D6A7]">
                          ACTIVE
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: CYCLES */}
        {activeAdminTab === 'cycles' && (
          <div className="bg-white border border-[#CFD8DC] rounded-lg shadow-sm p-6 space-y-6">
            <div className="border-b border-[#ECEFF1] pb-3">
              <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                Academic Cycle 2026-27 & Statutory Cutoff Dates
              </h2>
              <p className="text-xs text-[#546E7A]">
                Controls the live application ingestion window, deficiency resolution periods, and PFMS DBT clearance runs.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                <span className="text-[11px] font-bold text-[#546E7A] uppercase">Cycle Start Date</span>
                <div className="text-lg font-bold text-[#1D0A69] font-serif">01-July-2026</div>
                <p className="text-[#546E7A]">National Portal open for ST student registration & OTR generation.</p>
              </div>

              <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                <span className="text-[11px] font-bold text-[#C85A17] uppercase">Student Ingestion Cutoff</span>
                <div className="text-lg font-bold text-[#C85A17] font-serif">31-October-2026</div>
                <p className="text-[#546E7A]">Final date for fresh application submission across all 5 schemes.</p>
              </div>

              <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                <span className="text-[11px] font-bold text-[#198754] uppercase">Deficiency Rectification Cutoff</span>
                <div className="text-lg font-bold text-[#198754] font-serif">15-November-2026</div>
                <p className="text-[#546E7A]">Strict statutory deadline for uploading replacement income documents.</p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: RULE 4.2 ENGINE */}
        {activeAdminTab === 'rules' && (
          <div className="bg-white border border-[#CFD8DC] rounded-lg shadow-sm p-6 space-y-6">
            <div className="border-b border-[#ECEFF1] pb-3">
              <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                Statutory Rule 4.2 Engine — Family Income Certificate Validity Parameters
              </h2>
              <p className="text-xs text-[#546E7A]">
                Configures the automated rule engine that flags outdated revenue certificates during AI OCR document ingestion.
              </p>
            </div>

            <div className="space-y-4 max-w-xl text-xs">
              <div className="p-4 bg-[#FFFDE7] border border-[#FFE082] rounded space-y-2 text-[#5D4037]">
                <div className="flex items-center gap-2 font-bold text-[#150202]">
                  <AlertCircle className="w-4 h-4 text-[#C85A17]" />
                  <span>Rule 4.2 Statutory Enforcement: Active</span>
                </div>
                <p className="leading-relaxed">
                  "For Academic Year 2026-27, any Income Certificate issued prior to 01-April-2025 will be automatically rejected with a DEFICIENCY notice requesting a valid current financial year revenue certificate."
                </p>
              </div>

              <div>
                <label className="gov-label text-xs">Minimum Allowable Issuance Cutoff Date</label>
                <input
                  type="date"
                  value={cutoffDate}
                  onChange={(e) => setCutoffDate(e.target.value)}
                  className="gov-input text-xs font-mono font-bold"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="rule-active"
                  checked={rule42Active}
                  onChange={(e) => setRule42Active(e.target.checked)}
                  className="rounded text-[#1D0A69]"
                />
                <label htmlFor="rule-active" className="font-semibold text-[#150202]">
                  Enforce strict Rule 4.2 rejection in automated PaddleOCR ingestion pipeline
                </label>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleSaveRule}
                  className="gov-btn gov-btn-primary text-xs font-bold px-6 py-2.5 flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  <span>Sign & Deploy Rule with DSC Certificate</span>
                </button>
              </div>

              {saveSuccess && (
                <div className="p-3 bg-[#E8F5E9] border border-[#A5D6A7] rounded text-xs text-[#198754] font-bold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Rule parameters cryptographically countersigned and deployed to verification nodes.</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: INSTITUTES */}
        {activeAdminTab === 'institutes' && (
          <div className="bg-white border border-[#CFD8DC] rounded-lg shadow-sm overflow-hidden">
            <div className="p-4 sm:p-6 border-b border-[#ECEFF1] flex items-center justify-between gap-4 bg-[#F8F9FA]">
              <div>
                <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                  Notified Premier Higher Education Institutes (265 AISHE Nodes)
                </h2>
                <p className="text-xs text-[#546E7A]">
                  Central statutory repository of IITs, NITs, IIMs, AIIMS, NLUs, and Central Universities eligible under Top Class Scheme.
                </p>
              </div>
              <span className="text-xs font-bold text-[#198754] bg-[#E8F5E9] px-3 py-1 rounded border border-[#A5D6A7]">
                265 Institutes Live
              </span>
            </div>

            <div className="p-4 text-xs space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 bg-[#F4F6F8] rounded border border-[#CFD8DC]">
                  <strong className="block text-[#1D0A69]">IITs (Indian Inst of Tech)</strong>
                  <span className="text-xs text-[#546E7A]">23 Institutions (AISHE Verified)</span>
                </div>
                <div className="p-3 bg-[#F4F6F8] rounded border border-[#CFD8DC]">
                  <strong className="block text-[#1D0A69]">NITs & IIEST</strong>
                  <span className="text-xs text-[#546E7A]">32 Institutions (AISHE Verified)</span>
                </div>
                <div className="p-3 bg-[#F4F6F8] rounded border border-[#CFD8DC]">
                  <strong className="block text-[#1D0A69]">IIMs (Management)</strong>
                  <span className="text-xs text-[#546E7A]">21 Institutions (AISHE Verified)</span>
                </div>
                <div className="p-3 bg-[#F4F6F8] rounded border border-[#CFD8DC]">
                  <strong className="block text-[#1D0A69]">AIIMS & Medical Premier</strong>
                  <span className="text-xs text-[#546E7A]">25 Institutions (AISHE Verified)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: CRYPTOGRAPHIC AUDIT TRAIL */}
        {activeAdminTab === 'audit' && (
          <div className="bg-white border border-[#CFD8DC] rounded-lg shadow-sm overflow-hidden">
            <div className="p-4 sm:p-6 border-b border-[#ECEFF1] flex items-center justify-between gap-4 bg-[#F8F9FA]">
              <div>
                <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                  Section 4 IT Act Cryptographic Audit Trail
                </h2>
                <p className="text-xs text-[#546E7A]">
                  Immutable ledger recording administrative policy updates, quota reallocations, and digital signature verifications.
                </p>
              </div>
              <button
                type="button"
                onClick={() => alert("Downloading official IT Act Section 4 cryptographic audit ledger (CSV/PDF)...")}
                className="gov-btn gov-btn-secondary text-xs flex items-center gap-1.5 font-bold"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Audit CSV</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#1D0A69] text-white">
                  <tr>
                    <th className="p-3">Timestamp (IST)</th>
                    <th className="p-3">IP / Node</th>
                    <th className="p-3">Authorized Officer</th>
                    <th className="p-3">Action & Resource Description</th>
                    <th className="p-3">SHA-256 Digest</th>
                    <th className="p-3 text-right">DSC State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#CFD8DC]">
                  {auditLogs.map((log, idx) => (
                    <tr key={idx} className="hover:bg-[#F8F9FA]">
                      <td className="p-3 font-mono text-[#546E7A] whitespace-nowrap">{log.timestamp}</td>
                      <td className="p-3 font-mono text-[11px] text-[#546E7A]">{log.ip}</td>
                      <td className="p-3 font-semibold text-[#150202]">{log.officer}</td>
                      <td className="p-3 text-[#263238] max-w-md">{log.resource}</td>
                      <td className="p-3 font-mono text-[11px] text-[#1D0A69]">{log.hash}</td>
                      <td className="p-3 text-right">
                        <span className="text-[#198754] font-bold text-[11px]">
                          {log.dscStatus}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>
    </div>
  );
};
