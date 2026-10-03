import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { useDemo } from '../../context/DemoContext';
import { StatusBadge } from '../common/StatusBadge';
import { TribalPattern } from '../common/TribalPattern';
import { 
  ArrowRight, ShieldCheck, Filter, Search, 
  Landmark
} from 'lucide-react';

interface OfficerDashboardViewProps {
  onOpenWorkbench: (appId: string) => void;
}

export const OfficerDashboardView: React.FC<OfficerDashboardViewProps> = ({
  onOpenWorkbench
}) => {
  const { language } = useLanguage();
  const { applicant, verification } = useDemo();
  const [filterScheme, setFilterScheme] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const isVerified = verification.status === 'VERIFIED';

  const scrutinyQueue = [
    {
      id: applicant.applicationId || 'APP-2026-001DB3',
      applicantName: applicant.name || 'Demo ST Applicant',
      otrNo: applicant.otrNo || 'OTR-2026-ST-884912',
      scheme: 'Top Class Education for ST Students',
      schemeCode: 'TOP-05',
      institution: applicant.institution || 'Synthetic Demo University (IIT Indore)',
      submissionDate: 'Today (Live Scenario)',
      status: isVerified ? ('VERIFIED' as const) : ('DEFICIENT' as const),
      statusLabel: isVerified 
        ? 'Officer Verified (₹4,50,000 Promoted)' 
        : 'Material Income Conflict (Pending Scrutiny)',
      casteStatus: 'VERIFIED',
      incomeStatus: isVerified ? 'VERIFIED' : 'MATERIAL_CONFLICT',
      bonafideStatus: 'VERIFIED',
      actionUrgency: 'HIGH',
      isDemoTarget: true
    },
    {
      id: 'MOTA/2026/TC/09841',
      applicantName: 'Rajeshwar Soren',
      otrNo: 'OTR-2026-ST-884912',
      scheme: 'Top Class Education for ST Students',
      schemeCode: 'TOP-05',
      institution: 'IIT Kharagpur (AISHE: U-0570)',
      submissionDate: '12-Sep-2026',
      status: 'DEFICIENT' as const,
      statusLabel: 'Deficiency Raised (Rule 4.2)',
      casteStatus: 'VERIFIED',
      incomeStatus: 'OUTDATED_FY',
      bonafideStatus: 'VERIFIED',
      actionUrgency: 'HIGH',
      isDemoTarget: false
    },
    {
      id: 'MOTA/2026/NFST/04112',
      applicantName: 'Sunita Marandi',
      otrNo: 'OTR-2026-ST-772190',
      scheme: 'National Fellowship for ST Students (NFST)',
      schemeCode: 'NFST-03',
      institution: 'Jawaharlal Nehru University (JNU)',
      submissionDate: '14-Sep-2026',
      status: 'UNDER_SCRUTINY' as const,
      statusLabel: 'Institutional Scrutiny Pending',
      casteStatus: 'VERIFIED',
      incomeStatus: 'VERIFIED',
      bonafideStatus: 'VERIFIED',
      actionUrgency: 'NORMAL',
      isDemoTarget: false
    },
    {
      id: 'MOTA/2026/PMS/88210',
      applicantName: 'Birsa Munda',
      otrNo: 'OTR-2026-ST-991204',
      scheme: 'Post-Matric Scholarship for ST Students',
      schemeCode: 'PMS-02',
      institution: 'Ranchi University College',
      submissionDate: '15-Sep-2026',
      status: 'VERIFIED' as const,
      statusLabel: 'Institutional Verified (Ready for DBT)',
      casteStatus: 'VERIFIED',
      incomeStatus: 'VERIFIED',
      bonafideStatus: 'VERIFIED',
      actionUrgency: 'COMPLETED',
      isDemoTarget: false
    },
    {
      id: 'MOTA/2026/NOS/00219',
      applicantName: 'Anjali Kerketta',
      otrNo: 'OTR-2026-ST-663812',
      scheme: 'National Overseas Scholarship (NOS)',
      schemeCode: 'NOS-04',
      institution: 'University of Oxford (UK)',
      submissionDate: '16-Sep-2026',
      status: 'UNDER_SCRUTINY' as const,
      statusLabel: 'Committee Evaluation in Progress',
      casteStatus: 'VERIFIED',
      incomeStatus: 'VERIFIED',
      bonafideStatus: 'VERIFIED',
      actionUrgency: 'NORMAL',
      isDemoTarget: false
    }
  ];

  const filteredQueue = scrutinyQueue.filter(item => {
    if (filterScheme !== 'ALL' && item.schemeCode !== filterScheme) return false;
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      return (
        item.id.toLowerCase().includes(q) ||
        item.applicantName.toLowerCase().includes(q) ||
        item.institution.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Sovereign Officer Authority Masthead */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="woven" opacity={0.07} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
                <span>DISTRICT NODAL SCRUTINY DESK</span>
                <span>•</span>
                <span>ZONE: RANCHI (JHARKHAND)</span>
              </div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold font-serif text-white tracking-tight">
                {language === 'hi' 
                  ? 'अधिकारी जांच कार्यपीठ एवं साक्ष्य सत्यापन कंसोल' 
                  : 'District Scrutiny Desk & Evidentiary Verification Console'}
              </h1>
              <p className="text-xs text-[#EBEAEA]/80">
                Designated Officer: <strong>Shri S. K. Mahapatra (District Scrutiny Officer, Ranchi)</strong>
              </p>
            </div>

            {/* DSC Token & Status */}
            <div className="flex items-center gap-3">
              <div className="bg-white/10 px-3 py-2 rounded border border-white/20 text-xs space-y-0.5">
                <div className="flex items-center gap-1.5 text-[#81C784] font-bold">
                  <ShieldCheck className="w-4 h-4" />
                  <span>eMudhra DSC Token Active</span>
                </div>
                <div className="text-[11px] text-[#EBEAEA]/70 font-mono">
                  Cert ID: DSC-MOTA-2026-JH-910
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 2. Public Service Ledger Stats Bar (Non-card, high-density) */}
      <section className="bg-white border-b border-[#CFD8DC]">
        <div className="gov-container">
          <div className="grid grid-cols-2 lg:grid-cols-4 divide-x divide-y lg:divide-y-0 divide-[#ECEFF1] text-xs">
            <div className="py-4 px-4 space-y-0.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#546E7A]">Scrutiny Queue</span>
              <div className="text-2xl font-bold font-serif text-[#1D0A69]">148 Dossiers</div>
              <span className="text-[11px] text-[#546E7A]">Awaiting institutional/district sign-off</span>
            </div>

            <div className="py-4 px-4 space-y-0.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#C85A17]">Active Deficiencies</span>
              <div className="text-2xl font-bold font-serif text-[#C85A17]">12 Rectifications</div>
              <span className="text-[11px] text-[#546E7A]">Awaiting applicant response (Rule 4.2)</span>
            </div>

            <div className="py-4 px-4 space-y-0.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#198754]">Cycle Verified</span>
              <div className="text-2xl font-bold font-serif text-[#198754]">412 Approved</div>
              <span className="text-[11px] text-[#546E7A]">Forwarded to MoTA for PFMS DBT batch</span>
            </div>

            <div className="py-4 px-4 space-y-0.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#0F4C81]">Avg Turnaround</span>
              <div className="text-2xl font-bold font-serif text-[#0F4C81]">2.8 Days</div>
              <span className="text-[11px] text-[#198754] font-semibold">Under 14-day statutory SLA</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Main Scrutiny Dossier Queue */}
      <main className="gov-container py-8 space-y-6">
        
        {/* Filter and Search Ribbon */}
        <div className="bg-white border border-[#CFD8DC] rounded-t-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-[#1D0A69] font-serif">
              Priority Institutional & District Scrutiny Queue
            </h2>
            <p className="text-xs text-[#546E7A]">
              Click <strong>'Inspect Evidence'</strong> to examine OCR extracted entities side-by-side with original government certificates.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#90A4AE]" />
              <input
                type="text"
                placeholder="Search App ID or Scholar..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="gov-input text-xs pl-8 py-1.5 w-56"
              />
            </div>

            {/* Scheme Filter */}
            <div className="flex items-center gap-1.5 text-xs">
              <Filter className="w-3.5 h-3.5 text-[#546E7A]" />
              <select
                className="gov-select text-xs py-1.5"
                value={filterScheme}
                onChange={(e) => setFilterScheme(e.target.value)}
              >
                <option value="ALL">All Statutory Schemes</option>
                <option value="TOP-05">Top Class Education (TOP-05)</option>
                <option value="NFST-03">National Fellowship (NFST-03)</option>
                <option value="PMS-02">Post-Matric (PMS-02)</option>
                <option value="NOS-04">Overseas Scholarship (NOS-04)</option>
              </select>
            </div>
          </div>
        </div>

        {/* High-Density Scrutiny Table */}
        <div className="border border-t-0 border-[#CFD8DC] rounded-b-lg overflow-x-auto bg-white shadow-sm">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#1D0A69] text-white">
              <tr>
                <th className="p-3 font-semibold">Application Ref / OTR</th>
                <th className="p-3 font-semibold">Scholar Name & Community</th>
                <th className="p-3 font-semibold">Target Scheme & Institution</th>
                <th className="p-3 font-semibold">Submission Date</th>
                <th className="p-3 font-semibold">Evidence Validation Status</th>
                <th className="p-3 font-semibold">Scrutiny State</th>
                <th className="p-3 font-semibold text-right">Workbench Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#CFD8DC]">
              {filteredQueue.map((item) => {
                const isTarget = (item as any).isDemoTarget;
                return (
                  <tr 
                    key={item.id} 
                    className={`transition-colors ${
                      isTarget 
                        ? 'bg-[#FFF9C4]/40 border-l-4 border-l-[#C85A17] hover:bg-[#FFF9C4]/70' 
                        : item.id === 'MOTA/2026/TC/09841' 
                        ? 'bg-[#FFFDE7]/50 hover:bg-[#F8F9FA]' 
                        : 'hover:bg-[#F8F9FA]'
                    }`}
                  >
                    <td className="p-3">
                      <div className="flex items-center gap-1.5">
                        <div className="font-mono font-bold text-[#1D0A69]">{item.id}</div>
                        {isTarget && (
                          <span className="bg-[#C85A17] text-white font-extrabold px-1.5 py-0.2 rounded text-[9px] uppercase">
                            HIGH PRIORITY
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[#546E7A] font-mono">{item.otrNo}</div>
                    </td>

                    <td className="p-3">
                      <div className="font-bold text-[#150202]">{item.applicantName}</div>
                      <div className="text-[11px] text-[#546E7A]">
                        {isTarget ? 'Scheduled Tribe • Mandla (MP)' : 'Santhal (ST) • Jharkhand'}
                      </div>
                    </td>

                    <td className="p-3">
                      <div className="font-semibold text-[#1D0A69]">{item.scheme}</div>
                      <div className="text-[11px] text-[#546E7A]">{item.institution}</div>
                    </td>

                    <td className="p-3 text-[#546E7A] whitespace-nowrap">
                      {item.submissionDate}
                    </td>

                    <td className="p-3">
                      <div className="space-y-0.5 text-[11px]">
                        <div>Caste: <span className="text-[#198754] font-bold">✓ Verified</span></div>
                        <div>
                          Income:{' '}
                          {item.incomeStatus === 'MATERIAL_CONFLICT' ? (
                            <span className="text-[#C85A17] font-bold bg-[#FFEBEE] px-1.5 py-0.5 rounded border border-[#FFCDD2]">
                              ⚠ Discrepancy (Declared ₹5L vs OCR ₹4.5L)
                            </span>
                          ) : item.incomeStatus === 'OUTDATED_FY' ? (
                            <span className="text-[#C85A17] font-bold">! Outdated FY (Rule 4.2)</span>
                          ) : (
                            <span className="text-[#198754] font-bold">✓ Verified Evidence</span>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="p-3">
                      <StatusBadge status={item.status} customLabel={item.statusLabel} />
                    </td>

                    <td className="p-3 text-right">
                      <button
                        onClick={() => onOpenWorkbench(item.id)}
                        className={`inline-flex items-center gap-1.5 text-xs font-bold py-1.5 px-3.5 rounded shadow-xs transition-colors ${
                          isTarget && !isVerified
                            ? 'bg-[#C85A17] hover:bg-[#A8450D] text-white animate-pulse'
                            : 'bg-[#1D0A69] hover:bg-[#15074D] text-white'
                        }`}
                      >
                        <span>{isTarget ? (isVerified ? 'View Verified Record' : 'Review Conflict →') : 'Inspect Evidence'}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Security & Audit Ledger Notice */}
        <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] flex items-start gap-3 text-xs text-[#546E7A]">
          <Landmark className="w-5 h-5 text-[#1D0A69] flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <strong className="text-[#150202] block">Statutory Scrutiny Standard (Section 4 IT Act 2000):</strong>
            <p>Every review, evidence overlay approval, or deficiency memo generated by an officer is cryptographically countersigned using Digital Signature Certificate (DSC) tokens and permanently appended to the national scholarship audit ledger.</p>
          </div>
        </div>

      </main>
    </div>
  );
};
