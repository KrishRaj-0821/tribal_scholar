import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { OFFICIAL_MOTA_SCHEMES, SchemeInfo } from '../../theme/tokens';
import { TribalPattern } from '../common/TribalPattern';
import { 
  CheckCircle2, ArrowRight, ArrowLeft, 
  FileText, ShieldCheck, UploadCloud, AlertCircle, 
  FileCheck2, User, BookOpen, Landmark
} from 'lucide-react';

interface ApplicationWizardViewProps {
  initialScheme?: SchemeInfo | null;
  onSubmitted: () => void;
  onCancel: () => void;
}

export const ApplicationWizardView: React.FC<ApplicationWizardViewProps> = ({
  initialScheme,
  onSubmitted,
  onCancel
}) => {
  const { language } = useLanguage();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedSchemeCode, setSelectedSchemeCode] = useState<string>(initialScheme?.code || 'TOP-05');
  
  // Demographic and Form fields
  const [fatherName, setFatherName] = useState('Shri Mangal Soren');
  const [motherName, setMotherName] = useState('Smt. Sita Soren');
  const [institutionName, setInstitutionName] = useState('Indian Institute of Technology, Kharagpur');
  const [aisheCode, setAisheCode] = useState('U-0570');
  const [courseName, setCourseName] = useState('B.Tech in Computer Science & Engineering');
  const [admissionYear, setAdmissionYear] = useState('2024');
  const [annualIncome, setAnnualIncome] = useState('240000');
  
  // Document Upload States
  const [incomeDocUploaded, setIncomeDocUploaded] = useState(true);
  const [feeDocUploaded, setFeeDocUploaded] = useState(false);
  const [uploadingField, setUploadingField] = useState<string | null>(null);

  const simulateUpload = (fieldName: string) => {
    setUploadingField(fieldName);
    setTimeout(() => {
      if (fieldName === 'fee') setFeeDocUploaded(true);
      if (fieldName === 'income') setIncomeDocUploaded(true);
      setUploadingField(null);
    }, 1400);
  };

  const steps = [
    { num: 1, icon: User, titleEn: '1. Demographics', titleHi: '1. व्यक्तिगत साख' },
    { num: 2, icon: BookOpen, titleEn: '2. Academic Record', titleHi: '2. शैक्षणिक विवरण' },
    { num: 3, icon: Landmark, titleEn: '3. Scheme Selection', titleHi: '3. योजना चयन' },
    { num: 4, icon: ShieldCheck, titleEn: '4. Bank DBT Mapping', titleHi: '4. बैंक डीबीटी' },
    { num: 5, icon: FileText, titleEn: '5. Document Pipeline', titleHi: '5. दस्तावेज़ एवं OCR' },
    { num: 6, icon: CheckCircle2, titleEn: '6. Review & Submit', titleHi: '6. समीक्षा एवं जमा' }
  ];

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Sovereign Application Masthead with Tribal Identity Ribbon */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="woven" opacity={0.08} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
                <span>FORM-MOTA-SCH-2026</span>
                <span>•</span>
                <span>OTR-2026-ST-884912</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold font-serif text-white tracking-tight">
                {language === 'hi' 
                  ? 'केंद्रीय अनुसूचित जनजाति छात्रवृत्ति ऑनलाइन आवेदन प्रपत्र' 
                  : 'Central ST Scholarship & Fellowship Application Portal'}
              </h1>
              <p className="text-xs text-[#EBEAEA]/80">
                Academic Year 2026-27 • Ministry of Tribal Affairs, Government of India
              </p>
            </div>

            {/* Autosave and Exit */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded border border-white/20 text-xs">
                <span className="w-2 h-2 rounded-full bg-[#198754] animate-pulse"></span>
                <span className="text-[#EBEAEA] font-medium">Autosaved to Secure Local Cache</span>
              </div>

              <button
                type="button"
                onClick={onCancel}
                className="text-xs text-white/80 hover:text-white underline hover:no-underline font-semibold px-2 py-1"
              >
                Exit Form
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 2. Public Service Stepper Ribbon (Non-Card) */}
      <nav className="bg-white border-b border-[#CFD8DC] sticky top-12 z-30 shadow-xs" aria-label="Application Progress">
        <div className="gov-container">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-x divide-[#ECEFF1] text-xs">
            {steps.map((st) => {
              const isCurrent = currentStep === st.num;
              const isCompleted = currentStep > st.num;
              const Icon = st.icon;

              return (
                <button
                  key={st.num}
                  type="button"
                  onClick={() => setCurrentStep(st.num)}
                  className={`py-3 px-2 flex items-center justify-center gap-1.5 text-center transition-all ${
                    isCurrent
                      ? 'bg-[#1D0A69] text-white font-bold border-b-2 border-b-[#FFC107]'
                      : isCompleted
                      ? 'bg-[#E8F5E9]/50 text-[#198754] font-semibold hover:bg-[#E8F5E9]'
                      : 'bg-white text-[#546E7A] hover:bg-[#F8F9FA]'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${isCurrent ? 'text-[#FFC107]' : isCompleted ? 'text-[#198754]' : 'text-[#90A4AE]'}`} />
                  <span className="truncate">{language === 'hi' ? st.titleHi : st.titleEn}</span>
                  {isCompleted && <span className="text-[10px] font-bold">✓</span>}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* 3. Main Form Dossier Layout (Document Surface) */}
      <main className="gov-container py-8">
        <div className="max-w-4xl mx-auto bg-white border border-[#CFD8DC] rounded-lg shadow-sm overflow-hidden">
          
          {/* Top Form Header with Document Watermark */}
          <div className="p-6 border-b border-[#ECEFF1] bg-[#F8F9FA] flex flex-wrap items-center justify-between gap-3">
            <div>
              <span className="text-[11px] font-bold text-[#1D0A69] uppercase tracking-wider block">
                Statutory Dossier Step {currentStep} of 6
              </span>
              <h2 className="text-lg font-bold text-[#150202] font-serif">
                {currentStep === 1 && 'Personal & Demographic Credentials (Aadhaar Seeded)'}
                {currentStep === 2 && 'Institutional Enrollment & Academic Records'}
                {currentStep === 3 && 'Select Targeted ST Scholarship / Fellowship Scheme'}
                {currentStep === 4 && 'Direct Benefit Transfer (DBT) & NPCI Account Mapping'}
                {currentStep === 5 && 'Evidentiary Document Ingestion & Integrity Pipeline'}
                {currentStep === 6 && 'Statutory Declaration & Final Submission Dossier'}
              </h2>
            </div>

            <div className="text-right text-xs">
              <span className="text-[#546E7A]">Applicant: </span>
              <strong className="text-[#1D0A69]">Rajeshwar Soren</strong>
            </div>
          </div>

          <div className="p-6 sm:p-8 space-y-6">
            
            {/* STEP 1: PERSONAL DETAILS */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div className="p-3 bg-[#E8F5E9] border border-[#A5D6A7] rounded text-xs text-[#1B5E20] flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#198754] flex-shrink-0" />
                  <span>Demographic credentials pre-filled from your verified UIDAI Aadhaar e-KYC record.</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
                  <div>
                    <label className="gov-label text-xs">Full Name as per Aadhaar Record</label>
                    <input 
                      type="text" 
                      className="gov-input text-xs bg-[#F4F6F8] font-bold text-[#150202]" 
                      value="Rajeshwar Soren" 
                      readOnly 
                    />
                  </div>
                  <div>
                    <label className="gov-label text-xs">One-Time Registration (OTR) ID</label>
                    <input 
                      type="text" 
                      className="gov-input text-xs font-mono bg-[#F4F6F8] font-bold text-[#1D0A69]" 
                      value="OTR-2026-ST-884912" 
                      readOnly 
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
                  <div>
                    <label className="gov-label text-xs">Father's Full Name <span className="gov-req">*</span></label>
                    <input 
                      type="text" 
                      className="gov-input text-xs" 
                      value={fatherName} 
                      onChange={(e) => setFatherName(e.target.value)} 
                      required 
                    />
                  </div>
                  <div>
                    <label className="gov-label text-xs">Mother's Full Name <span className="gov-req">*</span></label>
                    <input 
                      type="text" 
                      className="gov-input text-xs" 
                      value={motherName} 
                      onChange={(e) => setMotherName(e.target.value)} 
                      required 
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 text-xs">
                  <div>
                    <label className="gov-label text-xs">Scheduled Tribe (ST) Community</label>
                    <input 
                      type="text" 
                      className="gov-input text-xs bg-[#F4F6F8] font-semibold text-[#150202]" 
                      value="Santhal (Scheduled Tribe)" 
                      readOnly 
                    />
                  </div>
                  <div>
                    <label className="gov-label text-xs">State / UT of Domicile</label>
                    <input 
                      type="text" 
                      className="gov-input text-xs bg-[#F4F6F8] font-semibold text-[#150202]" 
                      value="Jharkhand" 
                      readOnly 
                    />
                  </div>
                  <div>
                    <label className="gov-label text-xs">Annual Family Income (₹) <span className="gov-req">*</span></label>
                    <input 
                      type="number" 
                      className="gov-input text-xs font-bold text-[#1D0A69]" 
                      value={annualIncome} 
                      onChange={(e) => setAnnualIncome(e.target.value)} 
                      required 
                    />
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: ACADEMIC DETAILS */}
            {currentStep === 2 && (
              <div className="space-y-6 text-xs">
                <div>
                  <label className="gov-label text-xs">Enrolled Educational Institution <span className="gov-req">*</span></label>
                  <input 
                    type="text" 
                    className="gov-input text-xs font-bold text-[#150202]" 
                    value={institutionName} 
                    onChange={(e) => setInstitutionName(e.target.value)} 
                    required 
                  />
                  <span className="text-[11px] text-[#546E7A] mt-1 block">
                    Must be in the official MoTA Notified Premier Institutes Gazette for AY 2026-27.
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="gov-label text-xs">AISHE / UDISE+ Institutional Code <span className="gov-req">*</span></label>
                    <input 
                      type="text" 
                      className="gov-input text-xs font-mono font-bold text-[#1D0A69]" 
                      value={aisheCode} 
                      onChange={(e) => setAisheCode(e.target.value)} 
                      required 
                    />
                  </div>
                  <div>
                    <label className="gov-label text-xs">Year of Formal Admission <span className="gov-req">*</span></label>
                    <input 
                      type="text" 
                      className="gov-input text-xs" 
                      value={admissionYear} 
                      onChange={(e) => setAdmissionYear(e.target.value)} 
                      required 
                    />
                  </div>
                </div>

                <div>
                  <label className="gov-label text-xs">Degree / Course Name <span className="gov-req">*</span></label>
                  <input 
                    type="text" 
                    className="gov-input text-xs" 
                    value={courseName} 
                    onChange={(e) => setCourseName(e.target.value)} 
                    required 
                  />
                </div>
              </div>
            )}

            {/* STEP 3: SCHEME SELECTION */}
            {currentStep === 3 && (
              <div className="space-y-4 text-xs">
                <div className="p-3 bg-[#F4F6F8] rounded border border-[#CFD8DC] text-[#546E7A]">
                  Select the statutory scheme corresponding to your academic level. Each scheme operates under distinct Gazette criteria and budget outlays.
                </div>

                <div className="space-y-3">
                  {OFFICIAL_MOTA_SCHEMES.map((scheme) => {
                    const isSelected = selectedSchemeCode === scheme.code;
                    return (
                      <label 
                        key={scheme.code} 
                        className={`block p-4 rounded-md border-2 cursor-pointer transition-all ${
                          isSelected 
                            ? 'border-[#1D0A69] bg-[#1D0A69]/5 shadow-sm' 
                            : 'border-[#CFD8DC] bg-white hover:border-[#90A4AE]'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <input
                            type="radio"
                            name="schemeSelect"
                            value={scheme.code}
                            checked={isSelected}
                            onChange={() => setSelectedSchemeCode(scheme.code)}
                            className="mt-1 text-[#1D0A69] focus:ring-[#1D0A69]"
                          />
                          <div className="flex-1">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="font-bold text-[#1D0A69] text-sm font-serif">
                                {language === 'hi' ? scheme.titleHi : scheme.titleEn}
                              </span>
                              <span className="text-xs font-mono font-bold bg-[#EBEAEA] text-[#1D0A69] px-2 py-0.5 rounded">
                                {scheme.officialCode}
                              </span>
                            </div>
                            <p className="text-[#546E7A] text-xs mt-1">
                              {scheme.targetGroupEn}
                            </p>
                            <div className="flex flex-wrap items-center gap-4 mt-2 text-[11px] text-[#263238] font-medium">
                              <span>Ceiling: <strong>{scheme.incomeCeilingEn}</strong></span>
                              <span>•</span>
                              <span>Allocation: <strong>₹{scheme.annualBudgetCr} Cr</strong></span>
                              <span>•</span>
                              <span className="text-[#198754]">Target: <strong>{scheme.totalBeneficiariesTarget} Scholars</strong></span>
                            </div>
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}

            {/* STEP 4: BANK & DBT */}
            {currentStep === 4 && (
              <div className="space-y-6 text-xs">
                <div className="bg-[#E8F5E9] border border-[#A5D6A7] p-4 rounded-md space-y-2 text-[#1B5E20]">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <ShieldCheck className="w-5 h-5 text-[#198754]" />
                    <span>NPCI Direct Benefit Transfer (DBT) Status: ACTIVE & VERIFIED</span>
                  </div>
                  <p className="text-xs leading-relaxed">
                    Under the direct mandate of the Ministry of Tribal Affairs, scholarship stipends and fee reimbursements are transferred solely to active Aadhaar-seeded accounts mapped on the NPCI gateway. Zero manual cheque or third-party transfers are permitted.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="gov-label text-xs">Seeded Bank Name</label>
                    <input type="text" className="gov-input text-xs bg-[#F4F6F8] font-bold text-[#150202]" value="Bank of India" readOnly />
                  </div>
                  <div>
                    <label className="gov-label text-xs">Masked Account Number (NPCI Mapped)</label>
                    <input type="text" className="gov-input text-xs font-mono bg-[#F4F6F8] font-bold text-[#1D0A69]" value="•••• •••• •••• 4912" readOnly />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="gov-label text-xs">Bank IFSC Code</label>
                    <input type="text" className="gov-input text-xs font-mono bg-[#F4F6F8]" value="BKID0004912" readOnly />
                  </div>
                  <div>
                    <label className="gov-label text-xs">PFMS Public Gateway Status</label>
                    <input type="text" className="gov-input text-xs text-[#198754] font-bold bg-[#F4F6F8]" value="VALIDATED (Beneficiary Matched)" readOnly />
                  </div>
                </div>
              </div>
            )}

            {/* STEP 5: DOCUMENT INGESTION & OCR PIPELINE */}
            {currentStep === 5 && (
              <div className="space-y-6 text-xs">
                <div className="border-b border-[#ECEFF1] pb-3">
                  <h3 className="text-base font-bold text-[#1D0A69] font-serif">
                    Evidentiary Documents & Real-Time Integrity Scan
                  </h3>
                  <p className="text-[#546E7A] text-xs mt-0.5">
                    Uploaded evidence is quarantined in memory, scanned via ClamAV, hashed with SHA-256, and provisionally extracted with PaddleOCR.
                  </p>
                </div>

                <div className="space-y-4">
                  {/* Document 1: ST Caste Certificate */}
                  <div className="p-4 border border-[#CFD8DC] rounded-md bg-white space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <FileCheck2 className="w-5 h-5 text-[#198754]" />
                        <strong className="text-xs text-[#150202]">1. Scheduled Tribe (ST) Community Certificate</strong>
                      </div>
                      <span className="bg-[#E8F5E9] text-[#198754] text-[11px] font-bold px-2 py-0.5 rounded border border-[#A5D6A7]">
                        ✓ OCR Extracted & Verified
                      </span>
                    </div>
                    <div className="text-[11px] text-[#546E7A] flex flex-wrap items-center justify-between gap-2 bg-[#F8F9FA] p-2 rounded">
                      <span>File: <code>JH_ST_CERT_SOREN.pdf</code> (SHA-256: <code>8f14b...091e</code>)</span>
                      <span className="text-[#198754] font-bold">ClamAV Clean</span>
                    </div>
                  </div>

                  {/* Document 2: Current FY Income Certificate */}
                  <div className="p-4 border border-[#CFD8DC] rounded-md bg-white space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <FileText className="w-5 h-5 text-[#1D0A69]" />
                        <strong className="text-xs text-[#150202]">2. Current FY Family Income Certificate (Rule 4.2)</strong>
                      </div>
                      {incomeDocUploaded ? (
                        <span className="bg-[#E8F5E9] text-[#198754] text-[11px] font-bold px-2 py-0.5 rounded border border-[#A5D6A7]">
                          ✓ Ingested & Scanned
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => simulateUpload('income')}
                          className="bg-[#1D0A69] hover:bg-[#15074D] text-white text-[11px] font-bold py-1 px-3 rounded flex items-center gap-1.5"
                        >
                          <UploadCloud className="w-3.5 h-3.5" />
                          <span>{uploadingField === 'income' ? 'Scanning (ClamAV)...' : 'Upload Certificate'}</span>
                        </button>
                      )}
                    </div>
                    <p className="text-[11px] text-[#546E7A]">
                      Issued on or after 01-April-2025 by Revenue Officer / Tehsildar (Max 2MB, PDF/JPEG).
                    </p>
                  </div>

                  {/* Document 3: Bonafide Certificate */}
                  <div className="p-4 border border-[#CFD8DC] rounded-md bg-white space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <FileCheck2 className="w-5 h-5 text-[#198754]" />
                        <strong className="text-xs text-[#150202]">3. Institution Bonafide Student Certificate</strong>
                      </div>
                      <span className="bg-[#E8F5E9] text-[#198754] text-[11px] font-bold px-2 py-0.5 rounded border border-[#A5D6A7]">
                        ✓ Institute Sealed
                      </span>
                    </div>
                    <p className="text-[11px] text-[#546E7A]">
                      Signed by Dean of Academic Affairs, IIT Kharagpur with AISHE Code U-0570.
                    </p>
                  </div>

                  {/* Document 4: Sanctioned Fee Structure */}
                  <div className="p-4 border border-[#CFD8DC] rounded-md bg-white space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <FileText className="w-5 h-5 text-[#1D0A69]" />
                        <strong className="text-xs text-[#150202]">4. Sanctioned Fee Structure & Semester Receipt</strong>
                      </div>
                      {feeDocUploaded ? (
                        <span className="bg-[#E8F5E9] text-[#198754] text-[11px] font-bold px-2 py-0.5 rounded border border-[#A5D6A7]">
                          ✓ Uploaded & Scanned
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled={uploadingField === 'fee'}
                          onClick={() => simulateUpload('fee')}
                          className="bg-[#0F4C81] hover:bg-[#0C3B66] text-white text-[11px] font-bold py-1 px-3 rounded flex items-center gap-1.5"
                        >
                          <UploadCloud className="w-3.5 h-3.5" />
                          <span>{uploadingField === 'fee' ? 'Scanning (ClamAV)...' : 'Upload Receipt'}</span>
                        </button>
                      )}
                    </div>
                    <p className="text-[11px] text-[#546E7A]">
                      Required for direct tuition fee reimbursement under Central Sector Top Class Education Scheme.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 6: REVIEW & STATUTORY SUBMISSION */}
            {currentStep === 6 && (
              <div className="space-y-6 text-xs">
                <div className="border border-[#CFD8DC] rounded-md overflow-hidden">
                  <div className="bg-[#1D0A69] text-white px-4 py-2 font-bold font-serif text-sm">
                    Final Application Dossier Summary
                  </div>
                  <div className="divide-y divide-[#ECEFF1] p-2 bg-[#FAFAFA]">
                    <div className="grid grid-cols-3 p-2.5">
                      <span className="text-[#546E7A] font-semibold">Applicant Name</span>
                      <span className="col-span-2 text-[#150202] font-bold">Rajeshwar Soren (OTR-2026-ST-884912)</span>
                    </div>
                    <div className="grid grid-cols-3 p-2.5">
                      <span className="text-[#546E7A] font-semibold">Target Scheme</span>
                      <span className="col-span-2 text-[#1D0A69] font-bold">Top Class Education for ST Students (TOP-05)</span>
                    </div>
                    <div className="grid grid-cols-3 p-2.5">
                      <span className="text-[#546E7A] font-semibold">Institution</span>
                      <span className="col-span-2 text-[#150202]">Indian Institute of Technology, Kharagpur (U-0570)</span>
                    </div>
                    <div className="grid grid-cols-3 p-2.5">
                      <span className="text-[#546E7A] font-semibold">Degree / Course</span>
                      <span className="col-span-2 text-[#150202]">B.Tech in Computer Science & Engineering</span>
                    </div>
                    <div className="grid grid-cols-3 p-2.5">
                      <span className="text-[#546E7A] font-semibold">Annual Family Income</span>
                      <span className="col-span-2 text-[#150202] font-mono font-bold">₹2,40,000 (Within Statutory Ceiling)</span>
                    </div>
                    <div className="grid grid-cols-3 p-2.5">
                      <span className="text-[#546E7A] font-semibold">DBT Remittance Bank</span>
                      <span className="col-span-2 text-[#198754] font-bold">Bank of India (Aadhaar Seeded ••••4912)</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded border border-[#FFE082] bg-[#FFF9C4] text-[#5D4037] space-y-2">
                  <div className="flex items-center gap-2 font-bold text-xs text-[#7A5E00]">
                    <AlertCircle className="w-4 h-4 text-[#C85A17]" />
                    <span>Statutory Legal Affirmation (IT Act 2000 & Article 342)</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    I solemnly declare that all particulars and documents submitted herein are genuine. I understand that misrepresentation of caste status or income parameters will lead to immediate cancellation of scholarship, recovery of disbursed funds with penal interest, and prosecution under Indian Penal Code provisions.
                  </p>
                </div>
              </div>
            )}

          </div>

          {/* Bottom Wizard Navigation Action Ribbon */}
          <div className="p-4 sm:p-6 bg-[#F8F9FA] border-t border-[#CFD8DC] flex items-center justify-between gap-4">
            {currentStep > 1 ? (
              <button
                type="button"
                onClick={() => setCurrentStep(currentStep - 1)}
                className="gov-btn gov-btn-secondary text-xs flex items-center gap-1.5 font-bold"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Previous Step</span>
              </button>
            ) : (
              <div></div>
            )}

            {currentStep < 6 ? (
              <button
                type="button"
                onClick={() => setCurrentStep(currentStep + 1)}
                className="gov-btn gov-btn-primary text-xs font-bold px-6 py-2.5 flex items-center gap-2"
              >
                <span>Save & Proceed to Step {currentStep + 1}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onSubmitted}
                className="bg-[#198754] hover:bg-[#157347] text-white font-bold text-xs px-8 py-3 rounded shadow-md flex items-center gap-2 transition-all"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Submit Application & Generate Sovereign Acknowledgement</span>
              </button>
            )}
          </div>

        </div>
      </main>
    </div>
  );
};
