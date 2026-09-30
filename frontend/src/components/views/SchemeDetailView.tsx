import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { SchemeInfo } from '../../theme/tokens';
import { TribalPattern } from '../common/TribalPattern';
import { 
  ChevronRight, CheckCircle2, ArrowRight, ArrowLeft, 
  FileCheck2, Landmark, Award, 
  Clock, IndianRupee, BookOpen, ExternalLink, HelpCircle
} from 'lucide-react';

interface SchemeDetailViewProps {
  scheme: SchemeInfo;
  onBack: () => void;
  onApply: (scheme: SchemeInfo) => void;
}

// Map scheme codes to authentic cultural pattern families
const SCHEME_PATTERN_MAP: Record<string, { family: 'forest' | 'river' | 'woven' | 'earth' | 'mountain' | 'community'; regionEn: string; regionHi: string }> = {
  'PMS-02': { family: 'earth', regionEn: 'Central & Eastern Tribal Belt Tradition', regionHi: 'मध्य एवं पूर्वी जनजातीय क्षेत्र' },
  'TOP-05': { family: 'mountain', regionEn: 'Himalayan & Sub-Plateau Higher Education Motifs', regionHi: 'हिमालयी एवं उच्च पठारी क्षेत्र' },
  'NFST-03': { family: 'forest', regionEn: 'Forest Ecology & Research Knowledge Traditions', regionHi: 'अरण्य शोध एवं ज्ञान परम्परा' },
  'NOS-04': { family: 'river', regionEn: 'Maritime & Trans-Continental River Motifs', regionHi: 'नदी एवं सागर यात्रा परम्परा' },
  'EMRS-01': { family: 'community', regionEn: 'Village Community & Residential Learning Motifs', regionHi: 'सामुदायिक आवासीय विद्या परंपरा' }
};

export const SchemeDetailView: React.FC<SchemeDetailViewProps> = ({
  scheme,
  onBack,
  onApply
}) => {
  const { language } = useLanguage();
  const [activeTab, setActiveTab] = useState<'overview' | 'eligibility' | 'documents' | 'benefits' | 'process'>('overview');

  const patternMeta = SCHEME_PATTERN_MAP[scheme.code] || {
    family: 'woven' as const,
    regionEn: 'Pan-Indian Tribal Woven Motif',
    regionHi: 'अखिल भारतीय जनजातीय बुनाई'
  };

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-16">
      {/* 1. Sovereign Breadcrumb & Statutory Authority Ribbon */}
      <div className="bg-white border-b border-[#CFD8DC]">
        <div className="gov-container py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <nav className="text-[#546E7A] flex items-center gap-1.5" aria-label="Breadcrumb">
            <button 
              onClick={onBack} 
              className="hover:underline text-[#1D0A69] font-bold flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'योजना निर्देशिका' : 'All MoTA Schemes'}</span>
            </button>
            <ChevronRight className="w-3 h-3 text-[#90A4AE]" />
            <span className="font-mono text-[#546E7A]">{scheme.officialCode}</span>
            <ChevronRight className="w-3 h-3 text-[#90A4AE]" />
            <span className="text-[#150202] font-semibold truncate max-w-[200px] sm:max-w-md">
              {language === 'hi' ? scheme.titleHi : scheme.titleEn}
            </span>
          </nav>

          <div className="flex items-center gap-2 text-[11px] text-[#546E7A]">
            <span className="inline-block w-2 h-2 rounded-full bg-[#198754]"></span>
            <span>AY 2026-27 Active Cycle</span>
            <span className="text-[#CFD8DC]">|</span>
            <span className="font-mono">{scheme.gazetteRef}</span>
          </div>
        </div>
      </div>

      {/* 2. Editorial Scheme Masthead with Regional Cultural Watermark */}
      <section className="relative bg-[#1D0A69] text-white border-b-4 border-[#FFC107] overflow-hidden">
        {/* Authentic Tribal Pattern Background */}
        <TribalPattern 
          family={patternMeta.family} 
          opacity={0.09} 
          color="#FFC107"
          className="absolute inset-0 pointer-events-none"
        />

        <div className="gov-container relative py-8 sm:py-10">
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
            <div className="space-y-3 max-w-3xl">
              {/* Badges & Gazette Meta */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="bg-[#FFC107] text-[#150202] text-xs font-mono font-extrabold px-2.5 py-0.5 rounded tracking-wide">
                  {scheme.officialCode}
                </span>
                <span className="bg-white/10 text-white/90 text-xs px-2.5 py-0.5 rounded border border-white/20">
                  {language === 'hi' ? 'केंद्रीय क्षेत्र योजना' : 'Central Sector Affirmative Scheme'}
                </span>
                <span className="text-xs text-[#EBEAEA]/80 font-mono">
                  {language === 'hi' ? patternMeta.regionHi : patternMeta.regionEn}
                </span>
              </div>

              {/* Authoritative Title */}
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold font-serif leading-tight text-white tracking-tight">
                {language === 'hi' ? scheme.titleHi : scheme.titleEn}
              </h1>

              {/* Subtitle / Target Mandate */}
              <p className="text-sm sm:text-base text-[#EBEAEA] leading-relaxed max-w-2xl font-sans">
                {language === 'hi' ? scheme.targetGroupHi : scheme.targetGroupEn}
              </p>
            </div>

            {/* Quick Action & Budget Snapshot */}
            <div className="flex-shrink-0 bg-white/10 backdrop-blur-sm p-4 rounded border border-white/20 space-y-3 min-w-[280px]">
              <div className="grid grid-cols-2 gap-2 text-center border-b border-white/20 pb-3">
                <div>
                  <div className="text-[10px] text-[#EBEAEA] uppercase tracking-wider">Annual Allocation</div>
                  <div className="text-lg font-bold font-serif text-[#FFC107]">₹{scheme.annualBudgetCr}.00 Cr</div>
                </div>
                <div>
                  <div className="text-[10px] text-[#EBEAEA] uppercase tracking-wider">Annual Target</div>
                  <div className="text-lg font-bold font-serif text-[#81C784]">{scheme.totalBeneficiariesTarget}</div>
                </div>
              </div>

              <button
                onClick={() => onApply(scheme)}
                className="w-full bg-[#FFC107] hover:bg-[#FFB300] text-[#150202] font-bold py-3 px-4 rounded text-sm transition-all shadow-md flex items-center justify-center gap-2"
              >
                <span>{language === 'hi' ? 'ऑनलाइन आवेदन प्रपत्र भरें' : 'Proceed to Apply Online'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="text-center text-[11px] text-[#EBEAEA]/80 flex items-center justify-center gap-1">
                <Clock className="w-3 h-3 text-[#FFC107]" />
                <span>Cutoff: <strong>{scheme.deadline}</strong> (23:59 IST)</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Tribal Pattern Section Divider */}
      <TribalPattern family={patternMeta.family} height={14} color="#1D0A69" className="opacity-80" />

      {/* 4. Tab Navigation Ribbon */}
      <div className="bg-white border-b border-[#CFD8DC] sticky top-12 z-30 shadow-xs">
        <div className="gov-container flex items-center gap-1 overflow-x-auto text-xs font-bold">
          {[
            { id: 'overview', icon: BookOpen, labelEn: '1. Overview & Mandate', labelHi: '1. विवरण एवं राजपत्र' },
            { id: 'eligibility', icon: Award, labelEn: '2. Statutory Eligibility', labelHi: '2. वैधानिक पात्रता' },
            { id: 'documents', icon: FileCheck2, labelEn: '3. Evidentiary Documents', labelHi: '3. अनिवार्य दस्तावेज़' },
            { id: 'benefits', icon: IndianRupee, labelEn: '4. Financial Assistance', labelHi: '4. वित्तीय लाभ एवं भत्ते' },
            { id: 'process', icon: Landmark, labelEn: '5. Scrutiny Workflow', labelHi: '5. जांच एवं डीबीटी प्रक्रिया' }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 py-3 px-4 border-b-2 whitespace-nowrap transition-colors ${
                  isActive
                    ? 'border-[#1D0A69] text-[#1D0A69] bg-[#F4F6F8]'
                    : 'border-transparent text-[#546E7A] hover:text-[#1D0A69] hover:bg-[#F8F9FA]'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#1D0A69]' : 'text-[#90A4AE]'}`} />
                <span>{language === 'hi' ? tab.labelHi : tab.labelEn}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 5. Main Content Area */}
      <main className="gov-container py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Main Dossier (8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* TAB 1: OVERVIEW */}
            {activeTab === 'overview' && (
              <section className="bg-white border border-[#CFD8DC] rounded p-6 space-y-6 shadow-xs relative">
                <div className="border-b border-[#ECEFF1] pb-3">
                  <span className="text-[11px] font-bold text-[#546E7A] uppercase tracking-wider">
                    Statutory Scheme Charter
                  </span>
                  <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
                    {language === 'hi' ? 'योजना का प्रशासनिक उद्देश्य एवं रूपरेखा' : 'Administrative Purpose & Statutory Scheme Charter'}
                  </h2>
                </div>

                <div className="prose text-xs text-[#263238] leading-relaxed space-y-3 font-sans">
                  <p>
                    {language === 'hi'
                      ? `यह योजना भारत सरकार के जनजातीय कार्य मंत्रालय (MoTA) द्वारा अनुसूचित जनजाति (ST) के मेधावी विद्यार्थियों को सामाजिक-आर्थिक बाधाओं से मुक्त कर देश के शीर्ष संस्थानों एवं विश्वविद्यालयों में उच्च तकनीकी तथा व्यावसायिक शिक्षा उपलब्ध कराने हेतु संचालित की जा रही है।`
                      : `Administered directly by the Ministry of Tribal Affairs (MoTA), Government of India, this flagship affirmative action scheme eliminates socio-economic barriers for Scheduled Tribe (ST) scholars. It provides full fiscal coverage for undergraduate, postgraduate, and doctoral degrees at premier national institutions notified by the Central Government.`}
                  </p>
                  <p>
                    {language === 'hi'
                      ? `सभी स्वीकृतियां एवं छात्रवृत्ति हस्तांतरण प्रत्यक्ष लाभ अंतरण (DBT) के अंतर्गत सार्वजनिक वित्तीय प्रबंधन प्रणाली (PFMS) और भारतीय राष्ट्रीय भुगतान निगम (NPCI) आधार-सीडेड बैंक खातों के माध्यम से शत-प्रतिशत सीधे छात्र के खाते में जमा किए जाते हैं।`
                      : `All sanctions and disbursements operate under the Direct Benefit Transfer (DBT) mission. Funds are remitted through the Public Financial Management System (PFMS) directly into the student's active Aadhaar-seeded bank account validated on the NPCI mapper, with zero third-party intermediaries.`}
                  </p>
                </div>

                {/* Key Metrics Ledger Table */}
                <div className="border border-[#CFD8DC] rounded overflow-hidden">
                  <div className="bg-[#F4F6F8] px-4 py-2 border-b border-[#CFD8DC] text-xs font-bold text-[#1D0A69]">
                    Scheme Operational Parameters (AY 2026-27)
                  </div>
                  <div className="divide-y divide-[#ECEFF1] text-xs">
                    <div className="grid grid-cols-3 p-3">
                      <span className="text-[#546E7A] font-semibold">Nodal Division</span>
                      <span className="col-span-2 text-[#150202] font-medium">Scholarship Division, Ministry of Tribal Affairs, Shastri Bhawan, New Delhi</span>
                    </div>
                    <div className="grid grid-cols-3 p-3 bg-[#FAFAFA]">
                      <span className="text-[#546E7A] font-semibold">Statutory Reference</span>
                      <span className="col-span-2 font-mono text-[#1D0A69] font-bold">{scheme.gazetteRef}</span>
                    </div>
                    <div className="grid grid-cols-3 p-3">
                      <span className="text-[#546E7A] font-semibold">Annual Fiscal Outlay</span>
                      <span className="col-span-2 text-[#150202] font-bold">₹{scheme.annualBudgetCr}.00 Crore (100% Central Sector Grant)</span>
                    </div>
                    <div className="grid grid-cols-3 p-3 bg-[#FAFAFA]">
                      <span className="text-[#546E7A] font-semibold">Target Coverage</span>
                      <span className="col-span-2 text-[#198754] font-bold">{scheme.totalBeneficiariesTarget} Scholars</span>
                    </div>
                    <div className="grid grid-cols-3 p-3">
                      <span className="text-[#546E7A] font-semibold">Disbursal Frequency</span>
                      <span className="col-span-2 text-[#150202]">Annual Tuition Remittance + Bi-annual Maintenance DBT</span>
                    </div>
                  </div>
                </div>

                {/* Official Gazette Disclaimer */}
                <div className="p-3.5 bg-[#F4F6F8] rounded border border-[#CFD8DC] flex items-start gap-3 text-xs text-[#546E7A]">
                  <Landmark className="w-5 h-5 text-[#1D0A69] flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-[#150202] block mb-0.5">Constitution of India Mandate (Article 342)</strong>
                    <span>
                      Applicants must be bona fide members of communities notified as Scheduled Tribes under Presidential Orders. Benefits under this scheme are governed by guidelines revised in Gazette Notification 2026/MoTA-SCH-01.
                    </span>
                  </div>
                </div>
              </section>
            )}

            {/* TAB 2: ELIGIBILITY */}
            {activeTab === 'eligibility' && (
              <section className="bg-white border border-[#CFD8DC] rounded p-6 space-y-6 shadow-xs">
                <div className="border-b border-[#ECEFF1] pb-3">
                  <span className="text-[11px] font-bold text-[#546E7A] uppercase tracking-wider">
                    Statutory Conditions
                  </span>
                  <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
                    {language === 'hi' ? 'वैधानिक एवं शैक्षणिक पात्रता मानदंड' : 'Mandatory Statutory & Academic Eligibility Criteria'}
                  </h2>
                </div>

                <div className="space-y-4 text-xs">
                  {/* Criterion 1: Community */}
                  <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#198754] flex-shrink-0" />
                      <strong className="text-sm text-[#1D0A69]">
                        1. Scheduled Tribe (ST) Community Membership
                      </strong>
                    </div>
                    <p className="text-[#263238] pl-7 leading-relaxed">
                      {language === 'hi'
                        ? 'आवेदक को भारत के संविधान के अनुच्छेद 342 के तहत अधिसूचित किसी अनुसूचित जनजाति (ST) का सदस्य होना अनिवार्य है। इसके प्रमाण हेतु सक्षम राजस्व प्राधिकारी द्वारा निर्गत वैध स्थायी जाति प्रमाण पत्र प्रस्तुत करना होगा।'
                        : 'The applicant must belong to a Scheduled Tribe (ST) notified under Article 342 of the Constitution of India in relation to their State/UT of domicile. Self-declaration is invalid; an authorized digital revenue certificate is mandatory.'}
                    </p>
                  </div>

                  {/* Criterion 2: Income Ceiling with Rule 4.2 */}
                  <div className="p-4 bg-[#FFFDE7] rounded border border-[#FFE082] space-y-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#C85A17] flex-shrink-0" />
                      <strong className="text-sm text-[#150202]">
                        2. Annual Family Income Ceiling: {scheme.incomeCeilingEn}
                      </strong>
                    </div>
                    <p className="text-[#5D4037] pl-7 leading-relaxed">
                      Total composite annual income of the parents/guardians from all sources must not exceed {scheme.incomeCeilingEn}. 
                      <strong className="block mt-1 text-[#C85A17]">
                        Statutory Rule 4.2 Notice: Under MoTA guidelines for AY 2026-27, the income certificate must be issued by a competent Revenue Authority (Tehsildar/Circle Officer/SDO) on or after 01-April-2025.
                      </strong>
                    </p>
                  </div>

                  {/* Criterion 3: Academic Admission */}
                  <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#198754] flex-shrink-0" />
                      <strong className="text-sm text-[#1D0A69]">
                        3. Admission in Notified Premier Institution
                      </strong>
                    </div>
                    <p className="text-[#263238] pl-7 leading-relaxed">
                      Candidate must have secured confirmed regular, full-time admission into a notified premier higher education institution (IITs, NITs, IIMs, AIIMS, NLUs, Central Universities, etc.) verified via AISHE portal codes.
                    </p>
                  </div>

                  {/* Criterion 4: Bank Account & NPCI Seeding */}
                  <div className="p-4 bg-[#E8F5E9] rounded border border-[#A5D6A7] space-y-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-[#198754] flex-shrink-0" />
                      <strong className="text-sm text-[#1B5E20]">
                        4. Active NPCI Aadhaar-Seeded Bank Account
                      </strong>
                    </div>
                    <p className="text-[#1B5E20] pl-7 leading-relaxed">
                      The candidate must hold an active savings bank account in their own name seeded on the NPCI mapper for Aadhaar-based Direct Benefit Transfer. Joint or dormant accounts will be rejected by PFMS.
                    </p>
                  </div>
                </div>
              </section>
            )}

            {/* TAB 3: DOCUMENTS */}
            {activeTab === 'documents' && (
              <section className="bg-white border border-[#CFD8DC] rounded p-6 space-y-6 shadow-xs">
                <div className="border-b border-[#ECEFF1] pb-3">
                  <span className="text-[11px] font-bold text-[#546E7A] uppercase tracking-wider">
                    Evidentiary Requirements
                  </span>
                  <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
                    {language === 'hi' ? 'अनिवार्य दस्तावेज़ एवं साक्ष्य सूची' : 'Required Evidentiary Documents & Verification Standards'}
                  </h2>
                </div>

                <div className="overflow-x-auto border border-[#CFD8DC] rounded">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#1D0A69] text-white">
                      <tr>
                        <th className="p-3 w-10 text-center">#</th>
                        <th className="p-3">Document Type</th>
                        <th className="p-3">Competent Issuing Authority</th>
                        <th className="p-3">Validity & Pipeline Rules</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#CFD8DC]">
                      <tr className="hover:bg-[#F8F9FA]">
                        <td className="p-3 text-center font-bold text-[#1D0A69]">1</td>
                        <td className="p-3">
                          <strong className="text-[#1D0A69] block">ST Caste Certificate</strong>
                          <span className="text-[11px] text-[#546E7A]">Permanent Affirmative Proof</span>
                        </td>
                        <td className="p-3 text-[#263238]">Tehsildar / SDO / District Magistrate / Deputy Commissioner</td>
                        <td className="p-3">
                          <span className="text-[#198754] font-semibold">Permanent validity.</span> DigiLocker push or scanned PDF with verifiable QR/Barcode.
                        </td>
                      </tr>
                      <tr className="hover:bg-[#F8F9FA] bg-[#FFFDE7]/40">
                        <td className="p-3 text-center font-bold text-[#1D0A69]">2</td>
                        <td className="p-3">
                          <strong className="text-[#1D0A69] block">Current FY Income Certificate</strong>
                          <span className="text-[11px] text-[#C85A17] font-semibold">Strict Rule 4.2 Enforced</span>
                        </td>
                        <td className="p-3 text-[#263238]">Revenue Officer / Circle Officer / Tehsildar</td>
                        <td className="p-3">
                          <span className="text-[#C85A17] font-bold">Issued on or after 01-April-2025.</span> Must reflect total composite family income.
                        </td>
                      </tr>
                      <tr className="hover:bg-[#F8F9FA]">
                        <td className="p-3 text-center font-bold text-[#1D0A69]">3</td>
                        <td className="p-3">
                          <strong className="text-[#1D0A69] block">Bonafide Student Certificate</strong>
                          <span className="text-[11px] text-[#546E7A]">Current Academic Enrollment</span>
                        </td>
                        <td className="p-3 text-[#263238]">Dean / Principal / Registrar of Notified Institute</td>
                        <td className="p-3">
                          Must state current AY 2026-27 enrollment, course name, roll number, and hostel residence status.
                        </td>
                      </tr>
                      <tr className="hover:bg-[#F8F9FA]">
                        <td className="p-3 text-center font-bold text-[#1D0A69]">4</td>
                        <td className="p-3">
                          <strong className="text-[#1D0A69] block">Official Fee Structure & Receipt</strong>
                          <span className="text-[11px] text-[#546E7A]">Tuition Reimbursement</span>
                        </td>
                        <td className="p-3 text-[#263238]">Finance Officer / Bursar of Institution</td>
                        <td className="p-3">
                          Itemized non-refundable compulsory institutional fees receipt for current semester/year.
                        </td>
                      </tr>
                      <tr className="hover:bg-[#F8F9FA]">
                        <td className="p-3 text-center font-bold text-[#1D0A69]">5</td>
                        <td className="p-3">
                          <strong className="text-[#1D0A69] block">Aadhaar e-KYC Verification</strong>
                          <span className="text-[11px] text-[#546E7A]">Biometric Proof</span>
                        </td>
                        <td className="p-3 text-[#263238]">UIDAI (Direct API Integration)</td>
                        <td className="p-3">
                          Instant OTP/Fingerprint e-KYC validation. No physical document copy needed.
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="p-3 bg-[#F4F6F8] rounded border border-[#CFD8DC] text-[11px] text-[#546E7A] space-y-1">
                  <strong className="text-[#150202] block">Ingestion Pipeline Security:</strong>
                  <p>All uploaded documents undergo in-memory ClamAV antivirus quarantine, SHA-256 cryptographic hashing for integrity, and provisional text extraction via PaddleOCR v4 before reaching the Scrutiny Officer.</p>
                </div>
              </section>
            )}

            {/* TAB 4: BENEFITS */}
            {activeTab === 'benefits' && (
              <section className="bg-white border border-[#CFD8DC] rounded p-6 space-y-6 shadow-xs">
                <div className="border-b border-[#ECEFF1] pb-3">
                  <span className="text-[11px] font-bold text-[#546E7A] uppercase tracking-wider">
                    Fiscal Entitlements
                  </span>
                  <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
                    {language === 'hi' ? 'स्वीकृत वित्तीय सहायता विवरण' : 'Sanctioned Financial Assistance & DBT Entitlements'}
                  </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">Component 1</div>
                    <div className="text-base font-bold text-[#1D0A69] font-serif">Full Non-Refundable Tuition Fee</div>
                    <p className="text-[#263238] leading-relaxed">
                      Actual tuition fee and other compulsory non-refundable fees charged by the notified institution are reimbursed in full up to statutory ceilings.
                    </p>
                  </div>

                  <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">Component 2</div>
                    <div className="text-base font-bold text-[#198754] font-serif">Monthly Living Maintenance Allowance</div>
                    <p className="text-[#263238] leading-relaxed">
                      Hosteller scholars receive ₹3,000/month (₹36,000/annum) and Day Scholars receive ₹1,500/month disbursed directly via PFMS DBT.
                    </p>
                  </div>

                  <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">Component 3</div>
                    <div className="text-base font-bold text-[#C85A17] font-serif">Books & Stationery Allowance</div>
                    <p className="text-[#263238] leading-relaxed">
                      Annual grant of ₹5,000 credited to scholar account for academic textbooks, reference journals, and course equipment.
                    </p>
                  </div>

                  <div className="p-4 bg-[#F8F9FA] rounded border border-[#CFD8DC] space-y-2">
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">Component 4</div>
                    <div className="text-base font-bold text-[#0F4C81] font-serif">Computer / Laptop One-Time Aid</div>
                    <p className="text-[#263238] leading-relaxed">
                      One-time assistance up to ₹45,000 for acquiring a computing device / laptop during the entire course duration.
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-[#E8F5E9] rounded border border-[#A5D6A7] text-xs text-[#1B5E20]">
                  <strong className="block text-sm font-bold mb-1">Direct DBT Assurance:</strong>
                  <p>All approved financial disbursements are routed via Reserve Bank of India (RBI) / PFMS payment gateways directly to the scholar's account. No deductions or cash disbursements are permissible under central statutory rules.</p>
                </div>
              </section>
            )}

            {/* TAB 5: PROCESS */}
            {activeTab === 'process' && (
              <section className="bg-white border border-[#CFD8DC] rounded p-6 space-y-6 shadow-xs">
                <div className="border-b border-[#ECEFF1] pb-3">
                  <span className="text-[11px] font-bold text-[#546E7A] uppercase tracking-wider">
                    Sovereign Governance Lifecycle
                  </span>
                  <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
                    {language === 'hi' ? 'जांच एवं डीबीटी स्वीकृति प्रक्रिया' : 'Application Scrutiny & Direct Benefit Transfer Lifecycle'}
                  </h2>
                </div>

                {/* Vertical Process Timeline */}
                <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#CFD8DC]">
                  
                  {/* Step 1 */}
                  <div className="relative">
                    <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#1D0A69] text-white flex items-center justify-center text-[10px] font-bold ring-4 ring-white">
                      1
                    </span>
                    <div className="text-xs space-y-1">
                      <strong className="text-sm text-[#1D0A69] block">Step 1: OTR Registration & Online Submission</strong>
                      <p className="text-[#546E7A]">
                        Student creates their permanent One-Time Registration (OTR) with Aadhaar e-KYC, fills scheme application, and uploads digital documents.
                      </p>
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className="relative">
                    <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#1D0A69] text-white flex items-center justify-center text-[10px] font-bold ring-4 ring-white">
                      2
                    </span>
                    <div className="text-xs space-y-1">
                      <strong className="text-sm text-[#1D0A69] block">Step 2: Automated Pipeline Ingestion Scan</strong>
                      <p className="text-[#546E7A]">
                        Document hash generated (SHA-256), ClamAV virus scan executes, and PaddleOCR performs provisional entity extraction.
                      </p>
                    </div>
                  </div>

                  {/* Step 3 */}
                  <div className="relative">
                    <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#1D0A69] text-white flex items-center justify-center text-[10px] font-bold ring-4 ring-white">
                      3
                    </span>
                    <div className="text-xs space-y-1">
                      <strong className="text-sm text-[#1D0A69] block">Step 3: Institutional Nodal Officer Scrutiny</strong>
                      <p className="text-[#546E7A]">
                        Dean/Principal verifies bonafide admission, course fee structure, and academic standing using the Officer Scrutiny Workbench.
                      </p>
                    </div>
                  </div>

                  {/* Step 4 */}
                  <div className="relative">
                    <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#1D0A69] text-white flex items-center justify-center text-[10px] font-bold ring-4 ring-white">
                      4
                    </span>
                    <div className="text-xs space-y-1">
                      <strong className="text-sm text-[#1D0A69] block">Step 4: District/State Level Affirmative Verification</strong>
                      <p className="text-[#546E7A]">
                        District Welfare Officer confirms revenue caste certificate authenticity and adherence to Rule 4.2 family income ceiling.
                      </p>
                    </div>
                  </div>

                  {/* Step 5 */}
                  <div className="relative">
                    <span className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#198754] text-white flex items-center justify-center text-[10px] font-bold ring-4 ring-white">
                      5
                    </span>
                    <div className="text-xs space-y-1">
                      <strong className="text-sm text-[#198754] block">Step 5: Ministry Sanction Order & Direct DBT Remittance</strong>
                      <p className="text-[#546E7A]">
                        Central Ministry generates digital sanction order and dispatches payment batch to PFMS. Funds land in student's Aadhaar-seeded bank account.
                      </p>
                    </div>
                  </div>

                </div>
              </section>
            )}

          </div>

          {/* Right Sidebar: Public Authority & Guidance (4 cols) */}
          <div className="lg:col-span-4 space-y-6">
            
            {/* Quick Action Panel */}
            <div className="bg-white border-2 border-[#1D0A69] rounded p-5 space-y-4 shadow-sm">
              <div className="border-b border-[#ECEFF1] pb-3">
                <span className="text-[10px] font-bold text-[#198754] uppercase tracking-wider block">
                  Application Portal Active
                </span>
                <div className="text-base font-bold text-[#1D0A69] font-serif">
                  Ready to apply?
                </div>
              </div>

              <div className="space-y-2 text-xs text-[#546E7A]">
                <div className="flex items-center justify-between">
                  <span>Current AY:</span>
                  <strong className="text-[#150202]">2026-2027</strong>
                </div>
                <div className="flex items-center justify-between">
                  <span>Application Deadline:</span>
                  <strong className="text-[#C85A17]">{scheme.deadline}</strong>
                </div>
                <div className="flex items-center justify-between">
                  <span>Est. Scrutiny Turnaround:</span>
                  <strong className="text-[#198754]">14 Working Days</strong>
                </div>
              </div>

              <button
                onClick={() => onApply(scheme)}
                className="w-full bg-[#1D0A69] hover:bg-[#15074D] text-white font-bold py-2.5 px-4 rounded text-xs transition-colors flex items-center justify-center gap-2"
              >
                <span>{language === 'hi' ? 'आवेदन शुरू करें' : 'Start Online Application'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={onBack}
                className="w-full bg-transparent hover:bg-[#F4F6F8] text-[#546E7A] font-bold py-2 px-4 rounded text-xs border border-[#CFD8DC] transition-colors"
              >
                {language === 'hi' ? 'अन्य योजनाएं देखें' : 'View Other ST Schemes'}
              </button>
            </div>

            {/* Statutory Gazette Downloads */}
            <div className="bg-white border border-[#CFD8DC] rounded p-4 space-y-3 text-xs">
              <div className="font-bold text-[#1D0A69] flex items-center gap-2 border-b border-[#ECEFF1] pb-2">
                <BookOpen className="w-4 h-4 text-[#0F4C81]" />
                <span>Statutory Guidelines & Downloads</span>
              </div>
              <ul className="space-y-2 text-[11px]">
                <li>
                  <a 
                    href="#download-guidelines" 
                    onClick={(e) => { e.preventDefault(); alert("Official MoTA Gazette Guidelines (PDF) will download in production environment."); }}
                    className="text-[#0F4C81] hover:underline flex items-center justify-between font-medium"
                  >
                    <span>Scheme Detailed Guidelines (PDF, 420 KB)</span>
                    <ExternalLink className="w-3 h-3 text-[#90A4AE]" />
                  </a>
                </li>
                <li>
                  <a 
                    href="#income-format" 
                    onClick={(e) => { e.preventDefault(); alert("Annexure-A Income Certificate Proforma (PDF) will download."); }}
                    className="text-[#0F4C81] hover:underline flex items-center justify-between font-medium"
                  >
                    <span>Income Certificate Proforma (Annexure A)</span>
                    <ExternalLink className="w-3 h-3 text-[#90A4AE]" />
                  </a>
                </li>
                <li>
                  <a 
                    href="#institutes-list" 
                    onClick={(e) => { e.preventDefault(); alert("List of 265 Notified Premier Institutes (PDF) will download."); }}
                    className="text-[#0F4C81] hover:underline flex items-center justify-between font-medium"
                  >
                    <span>List of 265 Notified Institutes (AISHE)</span>
                    <ExternalLink className="w-3 h-3 text-[#90A4AE]" />
                  </a>
                </li>
              </ul>
            </div>

            {/* Student Helpline & Support Desk */}
            <div className="bg-[#F4F6F8] border border-[#CFD8DC] rounded p-4 space-y-2 text-xs">
              <div className="font-bold text-[#150202] flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-[#1D0A69]" />
                <span>Need Guidance with this Scheme?</span>
              </div>
              <p className="text-[11px] text-[#546E7A] leading-relaxed">
                Contact the Ministry of Tribal Affairs Scholarship Helpdesk or your Institutional Nodal Officer:
              </p>
              <div className="text-[11px] font-mono bg-white p-2 rounded border border-[#CFD8DC] space-y-1">
                <div>Toll Free: <strong>1800-11-7788</strong> (09:30 - 18:00)</div>
                <div>Email: <strong>scholarship-tribal@nic.in</strong></div>
              </div>
            </div>

          </div>

        </div>
      </main>

      {/* 6. Sticky Bottom Public Service Action Ribbon for Mobile / Fast Scroll */}
      <div className="fixed bottom-14 md:bottom-0 left-0 right-0 bg-white/95 backdrop-blur-md border-t-2 border-[#1D0A69] py-3 px-4 shadow-lg z-30">
        <div className="gov-container flex items-center justify-between gap-4">
          <div className="hidden sm:block">
            <span className="text-[10px] text-[#546E7A] uppercase font-bold block">{scheme.officialCode}</span>
            <span className="text-xs font-bold text-[#150202] font-serif truncate max-w-sm block">
              {language === 'hi' ? scheme.titleHi : scheme.titleEn}
            </span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <button
              onClick={onBack}
              className="text-xs text-[#546E7A] hover:text-[#1D0A69] font-bold px-3 py-2 border border-[#CFD8DC] rounded"
            >
              {language === 'hi' ? 'वापस' : 'Back'}
            </button>
            <button
              onClick={() => onApply(scheme)}
              className="flex-1 sm:flex-initial bg-[#1D0A69] hover:bg-[#15074D] text-white text-xs font-bold px-6 py-2.5 rounded shadow-sm flex items-center justify-center gap-2"
            >
              <span>{language === 'hi' ? 'ऑनलाइन आवेदन प्रपत्र भरें' : 'Apply Online for this Scheme'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
