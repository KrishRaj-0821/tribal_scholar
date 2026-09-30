import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from '../common/TribalPattern';
import { 
  ShieldCheck, ArrowRight, ArrowLeft, CheckCircle2, 
  AlertCircle
} from 'lucide-react';

interface RegistrationViewProps {
  onBackToLogin: () => void;
  onRegistered: () => void;
}

export const RegistrationView: React.FC<RegistrationViewProps> = ({
  onBackToLogin,
  onRegistered
}) => {
  const { language } = useLanguage();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [fullName, setFullName] = useState('Rajeshwar Soren');
  const [aadhaarMasked] = useState('•••• •••• 4912');
  const [dob, setDob] = useState('2004-05-18');
  const [gender, setGender] = useState('MALE');
  const [stateDomicile, setStateDomicile] = useState('JHARKHAND');
  const [tribeName, setTribeName] = useState('Santhal');
  const [casteCertNo, setCasteCertNo] = useState('JH/ST/2022/883910');
  const [mobile, setMobile] = useState('9876543210');
  const [bankSeeded, setBankSeeded] = useState(true);

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    if (step < 3) {
      setStep((step + 1) as any);
    } else {
      onRegistered();
    }
  };

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Official MoTA Sovereign Header with Bilingual Logo */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="community" opacity={0.07} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="bg-white p-2 rounded shadow-sm flex items-center justify-center flex-shrink-0">
                <img 
                  src="/mota-logo.png" 
                  alt="Ministry of Tribal Affairs Logo" 
                  className="h-12 sm:h-13 w-auto object-contain"
                />
              </div>

              <div className="space-y-0.5">
                <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
                  <span>PERMANENT SCHOLARSHIP IDENTIFIER</span>
                  <span>•</span>
                  <span>OTR ONBOARDING</span>
                </div>
                <h1 className="text-xl sm:text-2xl font-bold font-serif text-white tracking-tight">
                  {language === 'hi' 
                    ? 'एकल पंजीकरण (OTR) — नया एसटी छात्र पंजीकरण' 
                    : 'One-Time Registration (OTR) — New ST Candidate Onboarding'}
                </h1>
                <p className="text-xs text-[#EBEAEA]/80">
                  Lifetime Central Government ST Scholarship Identifier under Article 342
                </p>
              </div>
            </div>

            <button
              onClick={onBackToLogin}
              className="text-xs text-white/90 hover:text-white underline font-semibold flex items-center gap-1.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'लॉगिन पर वापस' : 'Back to Login'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* 2. Public Service Stepper Ribbon */}
      <nav className="bg-white border-b border-[#CFD8DC] sticky top-12 z-30 shadow-xs">
        <div className="gov-container">
          <div className="grid grid-cols-3 divide-x divide-[#ECEFF1] text-xs font-bold text-center">
            <button
              type="button"
              onClick={() => setStep(1)}
              className={`py-3 px-2 transition-colors ${
                step === 1 
                  ? 'bg-[#1D0A69] text-white border-b-2 border-b-[#FFC107]' 
                  : step > 1 
                  ? 'text-[#198754] bg-[#E8F5E9]/50' 
                  : 'text-[#546E7A] bg-white'
              }`}
            >
              <span>1. Aadhaar e-KYC & Demographics</span>
              {step > 1 && <span className="ml-1 text-[10px]">✓</span>}
            </button>

            <button
              type="button"
              onClick={() => setStep(2)}
              className={`py-3 px-2 transition-colors ${
                step === 2 
                  ? 'bg-[#1D0A69] text-white border-b-2 border-b-[#FFC107]' 
                  : step > 2 
                  ? 'text-[#198754] bg-[#E8F5E9]/50' 
                  : 'text-[#546E7A] bg-white'
              }`}
            >
              <span>2. ST Community & Domicile</span>
              {step > 2 && <span className="ml-1 text-[10px]">✓</span>}
            </button>

            <button
              type="button"
              onClick={() => setStep(3)}
              className={`py-3 px-2 transition-colors ${
                step === 3 
                  ? 'bg-[#1D0A69] text-white border-b-2 border-b-[#FFC107]' 
                  : 'text-[#546E7A] bg-white'
              }`}
            >
              <span>3. NPCI Bank DBT & Consent</span>
            </button>
          </div>
        </div>
      </nav>

      {/* 3. Main Form Dossier Card (Document Surface) */}
      <main className="gov-container py-8">
        <div className="max-w-2xl mx-auto bg-white border border-[#CFD8DC] rounded-lg shadow-sm overflow-hidden">
          
          <div className="p-6 border-b border-[#ECEFF1] bg-[#F8F9FA]">
            <h2 className="text-base font-bold text-[#1D0A69] font-serif">
              {step === 1 && 'Step 1: UIDAI Aadhaar e-KYC Demographic Validation'}
              {step === 2 && 'Step 2: Scheduled Tribe (ST) Community & State Domicile'}
              {step === 3 && 'Step 3: NPCI Bank Mapping & Statutory Affirmation'}
            </h2>
            <p className="text-xs text-[#546E7A] mt-0.5">
              Credentials verified here will permanently seed your central MoTA student dossier.
            </p>
          </div>

          <form onSubmit={handleNext} className="p-6 sm:p-8 space-y-5 text-xs">
            
            {/* STEP 1 */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="bg-[#E8F5E9] border border-[#A5D6A7] p-3 rounded flex items-center gap-2 text-[#1B5E20]">
                  <ShieldCheck className="w-4 h-4 text-[#198754] flex-shrink-0" />
                  <span>Aadhaar e-KYC demographic verification active via UIDAI Vault.</span>
                </div>

                <div>
                  <label className="gov-label text-xs">
                    Full Name (as per Aadhaar Card) <span className="gov-req">*</span>
                  </label>
                  <input
                    type="text"
                    className="gov-input text-xs font-bold text-[#150202]"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="gov-label text-xs">
                      Masked Aadhaar Number <span className="gov-req">*</span>
                    </label>
                    <input
                      type="text"
                      className="gov-input text-xs font-mono font-bold bg-[#F4F6F8] text-[#1D0A69]"
                      value={aadhaarMasked}
                      readOnly
                    />
                  </div>
                  <div>
                    <label className="gov-label text-xs">
                      Date of Birth <span className="gov-req">*</span>
                    </label>
                    <input
                      type="date"
                      className="gov-input text-xs"
                      value={dob}
                      onChange={(e) => setDob(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="gov-label text-xs">Gender <span className="gov-req">*</span></label>
                    <select 
                      className="gov-select text-xs" 
                      value={gender} 
                      onChange={(e) => setGender(e.target.value)}
                    >
                      <option value="MALE">Male</option>
                      <option value="FEMALE">Female</option>
                      <option value="OTHER">Third Gender</option>
                    </select>
                  </div>
                  <div>
                    <label className="gov-label text-xs">Active Mobile (Linked with Aadhaar) <span className="gov-req">*</span></label>
                    <input
                      type="tel"
                      className="gov-input text-xs font-mono"
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2 */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="gov-label text-xs">State / UT of Domicile <span className="gov-req">*</span></label>
                    <select
                      className="gov-select text-xs font-bold text-[#1D0A69]"
                      value={stateDomicile}
                      onChange={(e) => setStateDomicile(e.target.value)}
                    >
                      <option value="JHARKHAND">Jharkhand</option>
                      <option value="ODISHA">Odisha</option>
                      <option value="CHHATTISGARH">Chhattisgarh</option>
                      <option value="MADHYA_PRADESH">Madhya Pradesh</option>
                      <option value="MAHARASHTRA">Maharashtra</option>
                      <option value="GUJARAT">Gujarat</option>
                      <option value="RAJASTHAN">Rajasthan</option>
                      <option value="ASSAM">Assam</option>
                    </select>
                  </div>
                  <div>
                    <label className="gov-label text-xs">Notified Scheduled Tribe (Article 342) <span className="gov-req">*</span></label>
                    <input
                      type="text"
                      className="gov-input text-xs font-bold"
                      value={tribeName}
                      onChange={(e) => setTribeName(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="gov-label text-xs">Revenue ST Caste Certificate Number <span className="gov-req">*</span></label>
                  <input
                    type="text"
                    className="gov-input text-xs font-mono font-bold text-[#1D0A69]"
                    value={casteCertNo}
                    onChange={(e) => setCasteCertNo(e.target.value)}
                    placeholder="e.g. JH/ST/2022/883910"
                    required
                  />
                  <span className="text-[11px] text-[#546E7A] mt-1 block">
                    Permanent certificate issued by SDO / Tehsildar / DC. Verified directly via State Revenue Portal.
                  </span>
                </div>
              </div>
            )}

            {/* STEP 3 */}
            {step === 3 && (
              <div className="space-y-4">
                <div className="bg-[#E8F5E9] border border-[#A5D6A7] p-4 rounded space-y-2 text-[#1B5E20]">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <ShieldCheck className="w-5 h-5 text-[#198754]" />
                    <span>NPCI Aadhaar Payment Bridge System (APBS) Ready</span>
                  </div>
                  <p className="text-xs leading-relaxed">
                    Your active Aadhaar is mapped to <strong>Bank of India (A/C ••••4912)</strong> on the NPCI gateway. Scholarship stipends will be directly deposited via PFMS DBT.
                  </p>
                </div>

                <div className="p-4 rounded border border-[#FFE082] bg-[#FFF9C4] text-[#5D4037] space-y-2">
                  <div className="flex items-center gap-2 font-bold text-xs text-[#7A5E00]">
                    <AlertCircle className="w-4 h-4 text-[#C85A17]" />
                    <span>Statutory Consent & Affirmation</span>
                  </div>
                  <label className="flex items-start gap-2.5 cursor-pointer text-xs">
                    <input
                      type="checkbox"
                      checked={bankSeeded}
                      onChange={(e) => setBankSeeded(e.target.checked)}
                      className="mt-0.5 rounded text-[#1D0A69]"
                      required
                    />
                    <span>
                      I hereby give my explicit consent under the Aadhaar Act 2016 for Ministry of Tribal Affairs to verify my identity and disburse scholarship funds to my active NPCI seeded account.
                    </span>
                  </label>
                </div>
              </div>
            )}

            {/* Form Actions */}
            <div className="pt-4 border-t border-[#ECEFF1] flex items-center justify-between">
              {step > 1 ? (
                <button
                  type="button"
                  onClick={() => setStep((step - 1) as any)}
                  className="gov-btn gov-btn-secondary text-xs flex items-center gap-1.5 font-bold"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
              ) : (
                <div></div>
              )}

              {step < 3 ? (
                <button
                  type="submit"
                  className="gov-btn gov-btn-primary text-xs font-bold px-6 py-2.5 flex items-center gap-2"
                >
                  <span>Continue to Step {step + 1}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              ) : (
                <button
                  type="submit"
                  className="bg-[#198754] hover:bg-[#157347] text-white font-bold text-xs px-8 py-3 rounded shadow-md flex items-center gap-2 transition-all"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Complete OTR & Generate Lifetime ID</span>
                </button>
              )}
            </div>

          </form>

        </div>
      </main>
    </div>
  );
};
