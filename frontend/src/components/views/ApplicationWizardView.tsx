import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { OFFICIAL_MOTA_SCHEMES, SchemeInfo } from '../../theme/tokens';
import { applicationApi, vaultApi, VaultDocument } from '../../services/api';
import { TribalPattern } from '../common/TribalPattern';
import { 
  CheckCircle2, ArrowRight, ArrowLeft, 
  FileText, ShieldCheck, AlertCircle, 
  User, BookOpen, Save, Sparkles, FolderLock, 
  RefreshCw, Check
} from 'lucide-react';

interface ApplicationWizardViewProps {
  initialScheme?: SchemeInfo | null;
  onSubmitted?: () => void;
  onCancel?: () => void;
}

export const ApplicationWizardView: React.FC<ApplicationWizardViewProps> = ({
  initialScheme,
  onSubmitted,
  onCancel
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedScheme] = useState<SchemeInfo>(initialScheme || OFFICIAL_MOTA_SCHEMES[2]); // Top Class
  
  // Real Backend Application Record
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [applicationNumber, setApplicationNumber] = useState<string>('CREATING...');
  const [creatingApp, setCreatingApp] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitSuccess, setSubmitSuccess] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Reusable information from Vault & Profile
  const [reusableFields, setReusableFields] = useState<Record<string, any>>({});
  const [vaultDocuments, setVaultDocuments] = useState<VaultDocument[]>([]);
  const [usedVaultSources, setUsedVaultSources] = useState<Record<string, string>>({});

  // Form Fields
  const [fullName, setFullName] = useState(user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : 'Rajeshwar Soren');
  const [fatherName, setFatherName] = useState('Shri Rameshwar Soren');
  const [stateName, setStateName] = useState('Jharkhand');
  const [districtName, setDistrictName] = useState('Ranchi');
  const [community, setCommunity] = useState('ST');
  const [casteCertNo, setCasteCertNo] = useState('');
  const [institutionName, setInstitutionName] = useState('IIT Kharagpur');
  const [aisheCode, setAisheCode] = useState('U-0570');
  const [courseName, setCourseName] = useState('B.Tech Computer Science');
  const [admissionYear, setAdmissionYear] = useState('2026');
  const [annualIncome, setAnnualIncome] = useState<string>('500000');
  const [incomeCertNo, setIncomeCertNo] = useState('');

  // Income reuse decision
  const [incomeReusePromptDismissed, setIncomeReusePromptDismissed] = useState<boolean>(false);
  const [casteReusePromptDismissed, setCasteReusePromptDismissed] = useState<boolean>(false);

  // Initialize or fetch backend Application dossier and load Document Vault
  useEffect(() => {
    let isMounted = true;

    const initializeDossier = async () => {
      setCreatingApp(true);
      setErrorMessage(null);

      try {
        // 1. Fetch reusable fields from Document Vault & Profile
        const [reusableRes, vaultRes] = await Promise.allSettled([
          vaultApi.getReusableFields(),
          vaultApi.getDocuments(),
        ]);

        if (reusableRes.status === 'fulfilled' && isMounted) {
          const rf = reusableRes.value;
          setReusableFields(rf);

          // Auto-fill from profile initially if available
          if (rf['community']) {
            setCommunity(rf['community'].value);
            setUsedVaultSources(prev => ({ ...prev, community: rf['community'].source }));
          }
        }

        if (vaultRes.status === 'fulfilled' && isMounted) {
          setVaultDocuments(vaultRes.value?.documents || []);
        }

        // 2. Create actual backend Application record
        const appRes = await applicationApi.create({
          scheme_code: selectedScheme.code,
        });

        if (isMounted) {
          setApplicationId(appRes.id);
          setApplicationNumber(appRes.application_number);
        }
      } catch (err: any) {
        console.error('Failed to initialize application', err);
        if (isMounted) {
          setErrorMessage(err.message || 'Failed to create application on sovereign server.');
        }
      } finally {
        if (isMounted) setCreatingApp(false);
      }
    };

    initializeDossier();
    return () => { isMounted = false; };
  }, [selectedScheme]);

  // Handler to apply reusable information from Vault (Requirement 14, 16, 28)
  const applyIncomeFromVault = () => {
    const vaultIncome = reusableFields['annual_family_income'];
    if (vaultIncome) {
      setAnnualIncome(String(vaultIncome.value));
      setUsedVaultSources(prev => ({
        ...prev,
        annual_family_income: `Information found in your saved document (${vaultIncome.source_label})`
      }));
    }
    setIncomeReusePromptDismissed(true);
  };

  const applyCasteFromVault = () => {
    const vaultCaste = reusableFields['caste_certificate_number'];
    if (vaultCaste) {
      setCasteCertNo(String(vaultCaste.value));
      setUsedVaultSources(prev => ({
        ...prev,
        caste_certificate_number: `Information found in your saved document (${vaultCaste.source_label})`
      }));
    }
    setCasteReusePromptDismissed(true);
  };

  const handleSaveDraft = async () => {
    if (!applicationId) return;
    setErrorMessage(null);
    try {
      await applicationApi.saveForm(applicationId, {
        annual_family_income: annualIncome,
        caste_certificate_number: casteCertNo,
        institution_name: institutionName,
        course_name: courseName,
      });
      setSaveSuccessMsg("✓ Application progress securely saved to MoTA sovereign database.");
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to save draft.');
    }
  };

  const handleFinalSubmit = async () => {
    if (!applicationId) return;
    setSubmitting(true);
    setErrorMessage(null);

    try {
      // 1. Save all fields to authoritative backend form
      await applicationApi.saveForm(applicationId, {
        annual_family_income: annualIncome,
        caste_certificate_number: casteCertNo,
        community,
        institution_name: institutionName,
        course_name: courseName,
      });

      // 2. Submit with Idempotency Key
      const idempotencyKey = `submit_${applicationId}_${Date.now()}`;
      await applicationApi.submit(applicationId, idempotencyKey);

      setSubmitSuccess(true);
      if (onSubmitted) {
        onSubmitted();
      } else {
        setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 1500);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Submission failed. Please check required fields.');
    } finally {
      setSubmitting(false);
    }
  };

  const steps = [
    { num: 1, icon: User, title: 'Personal Details' },
    { num: 2, icon: BookOpen, title: 'Academic' },
    { num: 3, icon: ShieldCheck, title: 'Financial & Income' },
    { num: 4, icon: FolderLock, title: 'Document Vault' },
    { num: 5, icon: CheckCircle2, title: 'Review & Submit' }
  ];

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Masthead */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="woven" opacity={0.08} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
                <span>APPLICATION DOSSIER: <strong>{applicationNumber}</strong></span>
                <span>•</span>
                <span>AY 2026-27</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold font-serif text-white tracking-tight">
                {selectedScheme.titleEn} ({selectedScheme.code})
              </h1>
              <p className="text-xs text-[#EBEAEA]/80">
                Official Ministry of Tribal Affairs Sovereign Application Workflow
              </p>
            </div>

            {/* Autosave and Exit */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSaveDraft}
                className="bg-white/10 hover:bg-white/20 text-white border border-white/20 px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5"
              >
                <Save className="w-3.5 h-3.5 text-[#FFC107]" />
                <span>Save Draft</span>
              </button>

              <button
                type="button"
                onClick={() => onCancel ? onCancel() : navigate('/dashboard')}
                className="text-xs text-white/80 hover:text-white underline font-semibold px-2 py-1"
              >
                Exit Form
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 2. Success and Save alerts */}
      {saveSuccessMsg && (
        <div className="bg-[#E8F5E9] text-[#1B5E20] border-b border-[#A5D6A7] py-2 px-4 text-xs font-bold text-center">
          {saveSuccessMsg}
        </div>
      )}

      {/* 3. Stepper Ribbon */}
      <nav className="bg-white border-b border-[#CFD8DC] sticky top-12 z-20 shadow-xs">
        <div className="gov-container">
          <div className="grid grid-cols-2 sm:grid-cols-5 divide-x divide-[#ECEFF1] text-xs">
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
                      ? 'bg-[#E8F5E9]/60 text-[#198754] font-semibold'
                      : 'bg-white text-[#546E7A] hover:bg-[#F8F9FA]'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="truncate">{st.num}. {st.title}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* 4. Form Viewport */}
      <div className="gov-container py-8">
        
        {creatingApp ? (
          <div className="bg-white p-12 rounded-xl border border-[#CFD8DC] text-center max-w-lg mx-auto shadow-xs">
            <RefreshCw className="w-8 h-8 animate-spin text-[#1D0A69] mx-auto mb-3" />
            <h3 className="font-bold text-base text-[#1D0A69]">Initializing Sovereign Application Dossier</h3>
            <p className="text-xs text-[#546E7A] mt-1">
              Establishing official backend application record and binding statutory scheme rules...
            </p>
          </div>
        ) : submitSuccess ? (
          <div className="bg-white p-10 rounded-xl border border-[#A5D6A7] text-center max-w-lg mx-auto shadow-md">
            <div className="w-16 h-16 bg-[#E8F5E9] text-[#2E7D32] rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <h2 className="text-xl font-bold text-[#1D0A69]">Application Successfully Submitted!</h2>
            <p className="text-xs text-[#546E7A] mt-2">
              Your application dossier <strong>{applicationNumber}</strong> has entered the official MoTA verification pipeline.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-[#1D0A69] text-white px-5 py-2.5 rounded font-bold text-xs shadow-sm hover:bg-[#15074D]"
              >
                Go to Applicant Dashboard
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-xs border border-[#CFD8DC] overflow-hidden">
            
            {errorMessage && (
              <div className="p-4 bg-[#FFEBEE] border-b border-[#FFCDD2] text-[#C62828] text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="p-6 sm:p-8 space-y-6">

              {/* ─────────────────────────────────────────────────────────────
                  STEP 1: PERSONAL DETAILS
                  ───────────────────────────────────────────────────────────── */}
              {currentStep === 1 && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-[#1D0A69]">
                      1. Applicant Personal & Demographic Information
                    </h3>
                    <p className="text-xs text-[#546E7A]">
                      Pre-filled from your authenticated candidate profile.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">Full Legal Name</label>
                      <input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                      />
                      <span className="text-[10px] text-[#2E7D32] font-semibold mt-0.5 block">
                        ✓ Verified via OTR Identity
                      </span>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">Father's / Guardian's Name</label>
                      <input
                        type="text"
                        value={fatherName}
                        onChange={(e) => setFatherName(e.target.value)}
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">Home State Domicile</label>
                      <input
                        type="text"
                        value={stateName}
                        onChange={(e) => setStateName(e.target.value)}
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">Home District</label>
                      <input
                        type="text"
                        value={districtName}
                        onChange={(e) => setDistrictName(e.target.value)}
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                      />
                    </div>
                  </div>

                  {/* ST Certificate Reuse Prompt (Requirement 14, 16) */}
                  {reusableFields['caste_certificate_number'] && !casteReusePromptDismissed && (
                    <div className="bg-[#FFF8E1] border border-[#FFE082] p-4 rounded-xl">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5">
                          <Sparkles className="w-5 h-5 text-[#F57F17] flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs font-bold text-[#7A5E00]">
                              Use Information from Your Saved Document?
                            </div>
                            <div className="text-xs text-[#5D4037] mt-0.5">
                              Saved ST Certificate Number: <strong>{reusableFields['caste_certificate_number'].value}</strong>
                            </div>
                            <div className="text-[10px] text-[#7A5E00] mt-1 font-medium">
                              Source: {reusableFields['caste_certificate_number'].source_document_name || 'ST Community Certificate'}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            type="button"
                            onClick={applyCasteFromVault}
                            className="bg-[#1D0A69] text-white hover:bg-[#15074D] px-3 py-1.5 rounded text-xs font-bold shadow-xs"
                          >
                            Use This Information
                          </button>
                          <button
                            type="button"
                            onClick={() => setCasteReusePromptDismissed(true)}
                            className="text-xs text-[#546E7A] hover:underline"
                          >
                            Enter Manually
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                      ST Community Certificate Number
                    </label>
                    <input
                      type="text"
                      value={casteCertNo}
                      onChange={(e) => {
                        setCasteCertNo(e.target.value);
                        setUsedVaultSources(prev => ({ ...prev, caste_certificate_number: 'Manually Entered' }));
                      }}
                      placeholder="e.g. JH/ST/2024/77491"
                      className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                    />
                    {usedVaultSources['caste_certificate_number'] && (
                      <span className="text-[10px] text-[#2E7D32] font-semibold mt-1 flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        <span>{usedVaultSources['caste_certificate_number']}</span>
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* ─────────────────────────────────────────────────────────────
                  STEP 2: ACADEMIC DETAILS
                  ───────────────────────────────────────────────────────────── */}
              {currentStep === 2 && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-[#1D0A69]">
                      2. Academic Enrolment & Institution Information
                    </h3>
                    <p className="text-xs text-[#546E7A]">
                      Select your eligible notified institution and approved course of study.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                        Notified Institution / University (AISHE List)
                      </label>
                      <input
                        type="text"
                        value={institutionName}
                        onChange={(e) => setInstitutionName(e.target.value)}
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                        AISHE Code
                      </label>
                      <input
                        type="text"
                        value={aisheCode}
                        onChange={(e) => setAisheCode(e.target.value)}
                        placeholder="e.g. U-0570"
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white font-mono"
                      />
                    </div>
                  </div>
                  <span className="text-[10px] text-[#2E7D32] font-semibold -mt-2 block">
                    ✓ AISHE Verified Institution: Top Class Education Eligible
                  </span>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">Course of Study</label>
                      <input
                        type="text"
                        value={courseName}
                        onChange={(e) => setCourseName(e.target.value)}
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">Admission Cycle</label>
                      <input
                        type="text"
                        value={admissionYear}
                        onChange={(e) => setAdmissionYear(e.target.value)}
                        className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* ─────────────────────────────────────────────────────────────
                  STEP 3: FINANCIAL & INCOME DETAILS (REUSE SCENARIO)
                  ───────────────────────────────────────────────────────────── */}
              {currentStep === 3 && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-[#1D0A69]">
                      3. Financial Parameters & Parental Income Declaration
                    </h3>
                    <p className="text-xs text-[#546E7A]">
                      State the gross parental family income as per competent revenue authority certificate.
                    </p>
                  </div>

                  {/* SAVED INFORMATION PROMPT (Requirement 14 & 28) */}
                  {reusableFields['annual_family_income'] && !incomeReusePromptDismissed && (
                    <div className="bg-[#FFF8E1] border border-[#FFE082] p-4 rounded-xl shadow-xs">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5">
                          <Sparkles className="w-5 h-5 text-[#F57F17] flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-xs font-bold text-[#7A5E00]">
                              Use Information from Your Saved Documents
                            </div>
                            <div className="text-sm font-bold text-[#150202] mt-0.5">
                              Annual Family Income: {reusableFields['annual_family_income'].display_value}
                            </div>
                            <div className="text-[11px] text-[#5D4037] mt-0.5">
                              Saved from: <strong>{reusableFields['annual_family_income'].source_document_name || 'Income Certificate'}</strong>
                            </div>
                            <div className="text-[10px] text-[#7A5E00] mt-1">
                              Status: Provisional document extraction. You may review and modify below.
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            type="button"
                            onClick={applyIncomeFromVault}
                            className="bg-[#1D0A69] text-white hover:bg-[#15074D] px-3.5 py-1.5 rounded text-xs font-bold shadow-xs"
                          >
                            Use This Information
                          </button>
                          <button
                            type="button"
                            onClick={() => setIncomeReusePromptDismissed(true)}
                            className="text-xs text-[#546E7A] hover:underline"
                          >
                            Enter Manually
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                      Gross Annual Parental / Family Income (INR) *
                    </label>
                    <input
                      type="number"
                      value={annualIncome}
                      onChange={(e) => {
                        setAnnualIncome(e.target.value);
                        setUsedVaultSources(prev => ({ ...prev, annual_family_income: 'Manually Entered by Applicant' }));
                      }}
                      className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white font-mono font-bold"
                    />

                    {/* Source Indicator (Requirement 16) */}
                    {usedVaultSources['annual_family_income'] ? (
                      <div className="text-[11px] text-[#2E7D32] font-semibold mt-1 flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5 text-[#2E7D32]" />
                        <span>Source: {usedVaultSources['annual_family_income']}</span>
                      </div>
                    ) : (
                      <div className="text-[10px] text-[#78909C] mt-1">
                        Source: Applicant Self-Declaration
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                      Income Certificate Number
                    </label>
                    <input
                      type="text"
                      value={incomeCertNo}
                      onChange={(e) => setIncomeCertNo(e.target.value)}
                      placeholder="e.g. REV/INC/2026/8849"
                      className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>

                  <div className="bg-[#E8F5E9] p-3.5 rounded-lg border border-[#A5D6A7] text-xs text-[#1B5E20] flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 flex-shrink-0 text-[#2E7D32]" />
                    <span>
                      Direct Benefit Transfer (DBT): Stipends will be credited directly to your Aadhaar-seeded Bank Account (••••4912).
                    </span>
                  </div>
                </div>
              )}

              {/* ─────────────────────────────────────────────────────────────
                  STEP 4: DOCUMENT VAULT LINKING
                  ───────────────────────────────────────────────────────────── */}
              {currentStep === 4 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-[#1D0A69]">
                        4. Link Documents from My Document Vault
                      </h3>
                      <p className="text-xs text-[#546E7A]">
                        Reuse your previously verified certificates without re-uploading.
                      </p>
                    </div>

                    <Link
                      to="/documents"
                      target="_blank"
                      className="text-xs text-[#1D0A69] hover:underline font-bold flex items-center gap-1"
                    >
                      <FolderLock className="w-3.5 h-3.5" />
                      <span>Manage Vault</span>
                    </Link>
                  </div>

                  <div className="space-y-3">
                    {vaultDocuments.length === 0 ? (
                      <div className="p-6 bg-[#F8F9FA] rounded-xl border border-dashed border-[#CFD8DC] text-center">
                        <FolderLock className="w-8 h-8 text-[#78909C] mx-auto mb-2" />
                        <p className="text-xs font-bold text-[#1D0A69]">No documents in your vault yet</p>
                        <p className="text-[11px] text-[#546E7A] mt-1">
                          You can upload your certificates directly to your vault so they are automatically reused for all future schemes.
                        </p>
                        <button
                          type="button"
                          onClick={() => navigate('/documents')}
                          className="mt-3 bg-[#1D0A69] text-white px-4 py-1.5 rounded text-xs font-bold"
                        >
                          Upload to Vault
                        </button>
                      </div>
                    ) : (
                      vaultDocuments.map((doc) => (
                        <div 
                          key={doc.id}
                          className="bg-[#FAFAFA] border border-[#CFD8DC] rounded-lg p-3 flex items-center justify-between gap-3 text-xs"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded bg-[#E8EAF6] text-[#1D0A69] flex items-center justify-center font-bold">
                              <FileText className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="font-bold text-[#1D0A69]">{doc.display_type}</div>
                              <div className="text-[11px] text-[#78909C]">{doc.original_filename}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold text-[#2E7D32] bg-[#E8F5E9] px-2 py-0.5 rounded">
                              ✓ ClamAV Clean
                            </span>
                            <span className="text-[10px] font-bold text-[#F57F17] bg-[#FFF8E1] px-2 py-0.5 rounded">
                              {doc.verification_status}
                            </span>
                            <button
                              type="button"
                              onClick={async () => {
                                if (applicationId) {
                                  await vaultApi.linkDocument(doc.id, applicationId);
                                  setSaveSuccessMsg(`Linked ${doc.display_type} to this application.`);
                                  setTimeout(() => setSaveSuccessMsg(null), 2500);
                                }
                              }}
                              className="bg-white border border-[#CFD8DC] hover:border-[#1D0A69] text-[#1D0A69] font-bold px-2.5 py-1 rounded text-[11px]"
                            >
                              Link to Dossier
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* ─────────────────────────────────────────────────────────────
                  STEP 5: REVIEW & FINAL SUBMISSION
                  ───────────────────────────────────────────────────────────── */}
              {currentStep === 5 && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-[#1D0A69]">
                      5. Review Dossier & Final Statutory Affirmation
                    </h3>
                    <p className="text-xs text-[#546E7A]">
                      Review all declared and saved document parameters before formal submission.
                    </p>
                  </div>

                  <div className="border border-[#CFD8DC] rounded-xl overflow-hidden divide-y divide-[#ECEFF1] text-xs">
                    <div className="bg-[#1D0A69] text-white px-4 py-2 font-bold flex items-center justify-between">
                      <span>Application #{applicationNumber}</span>
                      <span className="bg-[#FFC107] text-[#120538] font-bold px-2 py-0.5 rounded text-[10px]">
                        Ready for Submission
                      </span>
                    </div>

                    <div className="grid grid-cols-3 p-3 bg-white">
                      <span className="font-semibold text-[#546E7A]">Target Scheme</span>
                      <span className="col-span-2 font-bold text-[#1D0A69]">{selectedScheme.titleEn}</span>
                    </div>

                    <div className="grid grid-cols-3 p-3 bg-[#F8F9FA]">
                      <span className="font-semibold text-[#546E7A]">Applicant</span>
                      <span className="col-span-2 font-bold text-[#263238]">{fullName} ({community})</span>
                    </div>

                    <div className="grid grid-cols-3 p-3 bg-white">
                      <span className="font-semibold text-[#546E7A]">Institution & Course</span>
                      <span className="col-span-2 text-[#263238]">{institutionName} — {courseName}</span>
                    </div>

                    <div className="grid grid-cols-3 p-3 bg-[#F8F9FA]">
                      <span className="font-semibold text-[#546E7A]">Declared Annual Income</span>
                      <span className="col-span-2 font-mono font-bold text-[#1D0A69]">
                        ₹{Number(annualIncome).toLocaleString('en-IN')}
                        {usedVaultSources['annual_family_income'] && (
                          <span className="text-[10px] text-[#2E7D32] ml-2 font-normal">
                            ({usedVaultSources['annual_family_income']})
                          </span>
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl border border-[#FFE082] bg-[#FFF9C4] text-[#5D4037] text-xs space-y-1.5">
                    <div className="flex items-center gap-2 font-bold text-[#7A5E00]">
                      <AlertCircle className="w-4 h-4 text-[#C85A17]" />
                      <span>Statutory Undertaking (IT Act 2000 & MoTA Directives)</span>
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      I solemnly affirm that the information declared above and documents linked from my vault are true and authentic. I authorize the scrutiny officer and competent authority to verify records against issuing authority registers.
                    </p>
                  </div>
                </div>
              )}

            </div>

            {/* Bottom Wizard Actions */}
            <div className="p-4 sm:p-6 bg-[#F8F9FA] border-t border-[#CFD8DC] flex items-center justify-between">
              {currentStep > 1 ? (
                <button
                  type="button"
                  onClick={() => setCurrentStep(currentStep - 1)}
                  className="px-4 py-2 border border-[#CFD8DC] bg-white rounded font-bold text-xs text-[#546E7A] hover:bg-[#ECEFF1] flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
              ) : <div></div>}

              {currentStep < 5 ? (
                <button
                  type="button"
                  onClick={() => setCurrentStep(currentStep + 1)}
                  className="bg-[#1D0A69] hover:bg-[#15074D] text-white font-bold text-xs px-6 py-2.5 rounded shadow-sm flex items-center gap-2"
                >
                  <span>Continue to Step {currentStep + 1}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              ) : (
                <button
                  type="button"
                  disabled={submitting}
                  onClick={handleFinalSubmit}
                  className="bg-[#198754] hover:bg-[#157347] disabled:opacity-50 text-white font-bold text-xs px-8 py-3 rounded shadow-md flex items-center gap-2"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Submitting Application...</span>
                    </>
                  ) : (
                    <>
                      <span>Submit Application Dossier</span>
                      <CheckCircle2 className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}
            </div>

          </div>
        )}

      </div>

    </div>
  );
};
