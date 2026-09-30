import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from '../common/TribalPattern';
import { 
  ShieldCheck, AlertTriangle, ArrowRight, 
  CheckCircle2, Clock, Download 
} from 'lucide-react';

interface ApplicantDashboardViewProps {
  onResolveDeficiency: () => void;
  onNavigateTab?: (tab: string) => void;
}

export const ApplicantDashboardView: React.FC<ApplicantDashboardViewProps> = ({
  onResolveDeficiency
}) => {
  const { language } = useLanguage();

  return (
    <div className="space-y-6 pb-12">
      {/* ─────────────────────────────────────────────────────────────
          01. EDITORIAL DASHBOARD HERO WITH SUBTLE CULTURAL WATERMARK
          ───────────────────────────────────────────────────────────── */}
      <section className="relative bg-[#FFFFFF] border-b border-[#CFD8DC] py-8 sm:py-10 overflow-hidden">
        <TribalPattern variant="woven" asBackground opacity={0.06} color="#1D0A69" />

        <div className="gov-container relative z-10 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs text-[#546E7A] font-mono">
                <span>OTR: <strong>OTR-2026-ST-884912</strong></span>
                <span>•</span>
                <span>Jharkhand (Santhal ST)</span>
              </div>
              
              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#1D0A69] font-serif mt-1">
                {language === 'hi' 
                  ? 'नमस्ते, राजेश्वर सोरेन (Rajeshwar Soren)' 
                  : 'Good afternoon, Rajeshwar Soren'}
              </h1>
              
              <p className="text-xs sm:text-sm text-[#263238] mt-1 max-w-2xl">
                {language === 'hi'
                  ? 'आपका शीर्ष श्रेणी शिक्षा छात्रवृत्ति आवेदन (IIT खड़गपुर) वर्तमान में जांचाधीन है। 1 दस्तावेज़ विसंगति पर तत्काल कार्रवाई अपेक्षित है।'
                  : 'Your Top Class Education scholarship application (IIT Kharagpur) is currently under nodal scrutiny with 1 actionable deficiency memo.'}
              </p>
            </div>

            {/* NPCI DBT Direct Bank Status */}
            <div className="bg-[#E8F5E9] border border-[#A5D6A7] p-3 rounded text-xs flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-[#198754] flex-shrink-0" />
              <div>
                <div className="font-bold text-[#1B5E20]">Aadhaar-NPCI Bank Seeding Active</div>
                <div className="text-[11px] text-[#2E7D32]">Bank of India (••••4912) • 100% Direct DBT Ready</div>
              </div>
            </div>
          </div>

          {/* Large Authoritative Status Callout */}
          <div className="bg-[#FFF9C4] border-l-4 border-l-[#C85A17] p-4 border-t border-r border-b border-[#FFE082] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[#C85A17] flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-xs font-mono font-bold text-[#7A5E00] uppercase tracking-wider">
                  APPLICATION STATUS • MOTA/2026/TC/09841
                </div>
                <div className="text-base font-bold text-[#150202] font-serif mt-0.5">
                  UNDER SCRUTINY — ACTION REQUIRED (RULE 4.2 DEFICIENCY)
                </div>
                <p className="text-xs text-[#7A5E00] mt-1 max-w-2xl leading-relaxed">
                  The uploaded Income Certificate is dated <strong>14-Aug-2024</strong>. MoTA statutory directives require income certificates issued on or after <strong>01-April-2025</strong> for AY 2026-27.
                </p>
              </div>
            </div>

            <button
              onClick={onResolveDeficiency}
              className="gov-btn gov-btn-warning text-xs font-bold py-2.5 px-4 flex-shrink-0 shadow-sm"
            >
              <span>{language === 'hi' ? 'कमी का समाधान करें' : 'Resolve Deficiency Now'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          02. APPLICATION DOSSIER & VERIFIED EVIDENCE LEDGER
          ───────────────────────────────────────────────────────────── */}
      <section className="gov-container space-y-6">
        <div className="border-b border-[#CFD8DC] pb-3">
          <span className="text-[11px] font-bold text-[#C85A17] uppercase tracking-wider">
            DOSSIER EVIDENCE INSPECTION
          </span>
          <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
            {language === 'hi' ? 'प्रमाणपत्र एवं दस्तावेज़ सत्यापन स्थिति' : 'Documentary Evidence Verification Ledger'}
          </h2>
          <p className="text-xs text-[#546E7A]">
            {language === 'hi' ? 'डिजिटल प्रमाण पत्रों की सत्यापन प्रगति' : 'Multi-engine cryptographic and institutional verification records'}
          </p>
        </div>

        {/* Process Ledger Table (Clean & Authoritative) */}
        <div className="gov-table-wrapper">
          <table className="gov-table" aria-label="Evidence Verification Ledger">
            <thead>
              <tr>
                <th>Document Type</th>
                <th>Certificate Ref / Identifier</th>
                <th>Issuing Authority</th>
                <th>Security & OCR Status</th>
                <th>Statutory State</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <div className="font-bold text-[#1D0A69]">Caste Certificate (ST)</div>
                  <div className="text-[11px] text-[#546E7A]">Santhal Community</div>
                </td>
                <td className="font-mono text-xs">JH/ST/2022/883910</td>
                <td>Sub-Divisional Officer, Ranchi, Jharkhand</td>
                <td>
                  <span className="text-xs font-bold text-[#198754] flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> DigiLocker Certified (SHA-256 Valid)
                  </span>
                </td>
                <td>
                  <span className="gov-badge gov-badge-success">VERIFIED</span>
                </td>
                <td>
                  <button className="text-xs text-[#0F4C81] font-bold hover:underline flex items-center gap-1">
                    <Download className="w-3 h-3" /> View PDF
                  </button>
                </td>
              </tr>

              <tr className="bg-[#FFF9C4]/30">
                <td>
                  <div className="font-bold text-[#1D0A69]">Income Certificate</div>
                  <div className="text-[11px] text-[#546E7A]">Annual Family Income Declared: ₹2,40,000</div>
                </td>
                <td className="font-mono text-xs">INC/2024/09120</td>
                <td>Tehsildar / Circle Officer, Ranchi</td>
                <td>
                  <span className="text-xs font-bold text-[#C85A17] flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Outdated FY (Issued 14-Aug-2024)
                  </span>
                </td>
                <td>
                  <span className="gov-badge gov-badge-warning">DEFICIENCY</span>
                </td>
                <td>
                  <button 
                    onClick={onResolveDeficiency}
                    className="text-xs text-[#C85A17] font-bold hover:underline"
                  >
                    Re-upload →
                  </button>
                </td>
              </tr>

              <tr>
                <td>
                  <div className="font-bold text-[#1D0A69]">Institutional Bonafide Certificate</div>
                  <div className="text-[11px] text-[#546E7A]">IIT Kharagpur (AISHE: U-0570)</div>
                </td>
                <td className="font-mono text-xs">IITKGP/BONA/2026/881</td>
                <td>Dean of Academic Affairs, IIT Kharagpur</td>
                <td>
                  <span className="text-xs font-bold text-[#198754] flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Digital Seal Inspected
                  </span>
                </td>
                <td>
                  <span className="gov-badge gov-badge-success">INSTITUTE VERIFIED</span>
                </td>
                <td>
                  <button className="text-xs text-[#0F4C81] font-bold hover:underline flex items-center gap-1">
                    <Download className="w-3 h-3" /> View Certificate
                  </button>
                </td>
              </tr>

              <tr>
                <td>
                  <div className="font-bold text-[#1D0A69]">Fee Structure & Hostel Receipt</div>
                  <div className="text-[11px] text-[#546E7A]">Annual Tuition & Hostel Entitlement</div>
                </td>
                <td className="font-mono text-xs">FEE/2026/0091</td>
                <td>IIT Kharagpur Accounts Division</td>
                <td>
                  <span className="text-xs text-[#546E7A] flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Provisional OCR Extracted (₹2,45,000)
                  </span>
                </td>
                <td>
                  <span className="gov-badge gov-badge-info">PENDING DWO</span>
                </td>
                <td>
                  <button className="text-xs text-[#0F4C81] font-bold hover:underline flex items-center gap-1">
                    <Download className="w-3 h-3" /> Receipt
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            03. 5-STAGE VERIFICATION LIFECYCLE PROGRESS
            ───────────────────────────────────────────────────────────── */}
        <div className="bg-[#FFFFFF] border border-[#CFD8DC] p-6 space-y-4">
          <div className="border-b border-[#ECEFF1] pb-2">
            <h3 className="text-base font-bold text-[#1D0A69] font-serif">
              Application Lifecycle Progress
            </h3>
            <p className="text-xs text-[#546E7A]">
              Statutory verification checkpoints from student submission to PFMS credit
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-2">
            {[
              { num: '1', title: 'Submitted', date: '12-Sep-2026', status: 'done' },
              { num: '2', title: 'OCR & Virus Check', date: '12-Sep-2026', status: 'done' },
              { num: '3', title: 'Institutional Scrutiny', date: '14-Sep-2026', status: 'current' },
              { num: '4', title: 'DWO State Approval', date: 'Pending', status: 'pending' },
              { num: '5', title: 'PFMS DBT Disbursal', date: 'Pending', status: 'pending' }
            ].map((step) => (
              <div 
                key={step.num}
                className={`p-3 border-l-4 text-xs ${
                  step.status === 'done' 
                    ? 'border-l-[#198754] bg-[#E8F5E9]/50' 
                    : step.status === 'current'
                    ? 'border-l-[#FFC107] bg-[#FFF9C4]/40 font-bold'
                    : 'border-l-[#CFD8DC] bg-[#F4F6F8] opacity-75'
                }`}
              >
                <div className="text-[10px] uppercase font-bold text-[#546E7A]">STAGE {step.num}</div>
                <div className="font-bold text-[#150202] mt-0.5">{step.title}</div>
                <div className="text-[10px] text-[#546E7A] mt-1">{step.date}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            04. FINANCIAL ENTITLEMENT & SANCTION SUMMARY
            ───────────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[#FFFFFF] border border-[#CFD8DC] p-5">
            <span className="text-[11px] font-bold text-[#546E7A] uppercase">Approved Tuition Outlay</span>
            <div className="text-2xl font-bold text-[#1D0A69] font-serif mt-1">₹2,00,000</div>
            <p className="text-xs text-[#546E7A] mt-1">100% Non-refundable tuition fees reimbursed to institution.</p>
          </div>

          <div className="bg-[#FFFFFF] border border-[#CFD8DC] p-5">
            <span className="text-[11px] font-bold text-[#546E7A] uppercase">Living & Books Allowance</span>
            <div className="text-2xl font-bold text-[#198754] font-serif mt-1">₹45,000</div>
            <p className="text-xs text-[#546E7A] mt-1">Direct DBT allowance to student Bank of India account.</p>
          </div>

          <div className="bg-[#FFFFFF] border border-[#CFD8DC] p-5">
            <span className="text-[11px] font-bold text-[#546E7A] uppercase">Computer Grant Entitlement</span>
            <div className="text-2xl font-bold text-[#0F4C81] font-serif mt-1">₹45,000</div>
            <p className="text-xs text-[#546E7A] mt-1">One-time laptop/computer grant upon first-year enrollment.</p>
          </div>
        </div>
      </section>
    </div>
  );
};
