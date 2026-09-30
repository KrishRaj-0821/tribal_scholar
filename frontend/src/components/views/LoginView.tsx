import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from '../common/TribalPattern';
import { 
  Lock, RefreshCw, Volume2, 
  ArrowRight, ShieldAlert, CheckCircle2, UserCheck, KeyRound, 
  ShieldCheck
} from 'lucide-react';

interface LoginViewProps {
  onLoginSuccess: (role: 'applicant' | 'officer') => void;
  onNavigateRegister: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({
  onLoginSuccess,
  onNavigateRegister
}) => {
  const { language } = useLanguage();
  const [roleTab, setRoleTab] = useState<'applicant' | 'officer'>('applicant');
  const [authMode, setAuthMode] = useState<'otp' | 'password'>('otp');
  const [identifier, setIdentifier] = useState('OTR-2026-ST-884912');
  const [otpValue, setOtpValue] = useState('');
  const [captchaInput, setCaptchaInput] = useState('');
  const [captchaCode, setCaptchaCode] = useState('7W9XK2');
  const [affirmed, setAffirmed] = useState(true);

  const refreshCaptcha = () => {
    const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
    let res = '';
    for (let i = 0; i < 6; i++) {
      res += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setCaptchaCode(res);
  };

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (roleTab === 'applicant') {
      onLoginSuccess('applicant');
    } else {
      onLoginSuccess('officer');
    }
  };

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Sovereign Government Header & Official MoTA Logo Lockup */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="woven" opacity={0.07} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7 sm:py-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              {/* Official Bilingual MoTA Logo */}
              <div className="bg-white p-2.5 rounded shadow-sm flex items-center justify-center flex-shrink-0">
                <img 
                  src="/mota-logo.png" 
                  alt="Ministry of Tribal Affairs Logo" 
                  className="h-12 sm:h-14 w-auto object-contain"
                />
              </div>

              <div className="space-y-0.5">
                <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
                  <span>GOVERNMENT OF INDIA</span>
                  <span>•</span>
                  <span>DIGITAL IDENTITY GATEWAY</span>
                </div>
                <h1 className="text-xl sm:text-2xl font-bold font-serif text-white tracking-tight">
                  {language === 'hi' 
                    ? 'एकल राष्ट्रीय जनजातीय छात्रवृत्ति प्रवेश द्वार' 
                    : 'Unified Sovereign ST Scholarship & Fellowship Gateway'}
                </h1>
                <p className="text-xs text-[#EBEAEA]/80">
                  {language === 'hi'
                    ? 'जनजातीय कार्य मंत्रालय — सुरक्षित सिंगल साइन-ऑन (SSO) एवं एकल पंजीकरण (OTR)'
                    : 'Ministry of Tribal Affairs — Aadhaar e-KYC Single Sign-On (SSO) Portal'}
                </p>
              </div>
            </div>

            <div className="hidden lg:flex items-center gap-2 text-xs text-[#EBEAEA]/80 bg-white/10 px-3 py-2 rounded border border-white/20">
              <ShieldCheck className="w-4 h-4 text-[#81C784]" />
              <span>TLS 1.3 256-bit Encrypted Session</span>
            </div>
          </div>
        </div>
      </header>

      {/* 2. Public Service Role Selector Ribbon */}
      <nav className="bg-white border-b border-[#CFD8DC] sticky top-12 z-30 shadow-xs">
        <div className="gov-container flex items-center gap-1 text-xs font-bold">
          <button
            onClick={() => setRoleTab('applicant')}
            className={`flex items-center gap-2 py-3 px-5 border-b-2 transition-colors ${
              roleTab === 'applicant'
                ? 'border-[#1D0A69] text-[#1D0A69] bg-[#F4F6F8]'
                : 'border-transparent text-[#546E7A] hover:text-[#1D0A69] hover:bg-[#F8F9FA]'
            }`}
          >
            <UserCheck className="w-4 h-4" />
            <span>{language === 'hi' ? 'आवेदक / छात्र प्रवेश (Citizen Sign In)' : 'Applicant / Citizen Sign In'}</span>
          </button>

          <button
            onClick={() => setRoleTab('officer')}
            className={`flex items-center gap-2 py-3 px-5 border-b-2 transition-colors ${
              roleTab === 'officer'
                ? 'border-[#1D0A69] text-[#1D0A69] bg-[#F4F6F8]'
                : 'border-transparent text-[#546E7A] hover:text-[#1D0A69] hover:bg-[#F8F9FA]'
            }`}
          >
            <KeyRound className="w-4 h-4" />
            <span>{language === 'hi' ? 'नोडल अधिकारी / जांचकर्ता (Officer DSC)' : 'Nodal Scrutiny Officer (DSC)'}</span>
          </button>
        </div>
      </nav>

      {/* 3. Main Form Dossier Layout (Document Surface) */}
      <main className="gov-container py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left Column: Official Authentication Terminal (7 cols) */}
          <div className="lg:col-span-7 bg-white border border-[#CFD8DC] rounded-lg shadow-sm overflow-hidden">
            <div className="p-6 border-b border-[#ECEFF1] bg-[#F8F9FA]">
              <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                {roleTab === 'applicant'
                  ? (language === 'hi' ? 'छात्रवृत्ति आवेदक प्रमाणीकरण' : 'Citizen Sign In with One-Time Registration (OTR)')
                  : (language === 'hi' ? 'नोडल अधिकारी प्रवेश (डिजिटल हस्ताक्षर)' : 'Nodal Officer Verification Console (DSC Login)')}
              </h2>
              <p className="text-xs text-[#546E7A] mt-0.5">
                {roleTab === 'applicant'
                  ? 'Access your active scholarship dossier, resolve deficiencies & track PFMS DBT transfers.'
                  : 'Review institutional bonafide records and certify ST scholarship applications.'}
              </p>
            </div>

            <form onSubmit={handleLoginSubmit} className="p-6 sm:p-8 space-y-5 text-xs">
              
              {/* Auth Mode Toggle */}
              <div className="flex border border-[#CFD8DC] rounded p-1 bg-[#F4F6F8]">
                <button
                  type="button"
                  onClick={() => setAuthMode('otp')}
                  className={`flex-1 py-1.5 font-bold rounded transition-colors ${
                    authMode === 'otp' ? 'bg-[#1D0A69] text-white shadow-xs' : 'text-[#546E7A] hover:text-[#1D0A69]'
                  }`}
                >
                  {language === 'hi' ? 'ओटीआर / मोबाइल OTP' : 'OTR / Mobile OTP'}
                </button>
                <button
                  type="button"
                  onClick={() => setAuthMode('password')}
                  className={`flex-1 py-1.5 font-bold rounded transition-colors ${
                    authMode === 'password' ? 'bg-[#1D0A69] text-white shadow-xs' : 'text-[#546E7A] hover:text-[#1D0A69]'
                  }`}
                >
                  {language === 'hi' ? 'पासवर्ड द्वारा' : 'Password Sign In'}
                </button>
              </div>

              {/* Identifier Input */}
              <div>
                <label className="gov-label text-xs">
                  {roleTab === 'applicant'
                    ? (language === 'hi' ? 'एकल पंजीकरण संख्या (OTR No.) अथवा मोबाइल' : 'One-Time Registration (OTR) No. / Mobile')
                    : (language === 'hi' ? 'सरकारी ईमेल आईडी (gov.in / nic.in)' : 'Official Nodal Officer ID (NIC/Gov Email)')}
                  <span className="gov-req">*</span>
                </label>
                <input
                  type="text"
                  className="gov-input text-xs font-mono font-bold text-[#1D0A69]"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder={roleTab === 'applicant' ? 'OTR-2026-ST-884912' : 'sk.mahapatra@nic.in'}
                  required
                />
                <span className="text-[11px] text-[#546E7A] mt-1 block">
                  {roleTab === 'applicant' 
                    ? 'OTR is your permanent 14-character ST scholarship identifier generated via Aadhaar e-KYC.' 
                    : 'Institutional AISHE/UDISE nodal credentials issued by MoTA.'}
                </span>
              </div>

              {/* OTP or Password Field */}
              {authMode === 'otp' ? (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="gov-label text-xs mb-0">
                      {language === 'hi' ? '6-अंकीय ओटीपी (OTP)' : 'Enter 6-Digit OTP'}
                      <span className="gov-req">*</span>
                    </label>
                    <span className="text-[11px] text-[#198754] font-semibold">
                      OTP Sent to Registered Mobile (••••••4912)
                    </span>
                  </div>
                  <input
                    type="text"
                    maxLength={6}
                    placeholder="Enter 6-digit code"
                    className="gov-input text-xs font-mono tracking-widest text-center font-bold"
                    value={otpValue}
                    onChange={(e) => setOtpValue(e.target.value)}
                  />
                  <div className="flex items-center justify-between text-[11px] text-[#546E7A] mt-1">
                    <span>Resend OTP in <strong>01:42</strong></span>
                    <button type="button" className="text-[#0F4C81] hover:underline font-semibold">
                      Resend Code
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <label className="gov-label text-xs">
                    {language === 'hi' ? 'पासवर्ड (Password)' : 'Password'}
                    <span className="gov-req">*</span>
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••••••"
                    className="gov-input text-xs"
                    required
                  />
                </div>
              )}

              {/* Sovereign Security Captcha */}
              <div className="bg-[#F8F9FA] p-3 rounded border border-[#CFD8DC] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#150202]">
                    Security Verification Captcha:
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => alert(`Audio Captcha: ${captchaCode.split('').join(' ')}`)}
                      className="p-1 text-[#546E7A] hover:text-[#1D0A69]"
                      title="Audio Captcha for Accessibility"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={refreshCaptcha}
                      className="p-1 text-[#546E7A] hover:text-[#1D0A69]"
                      title="Refresh Captcha"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="bg-white border-2 border-dashed border-[#90A4AE] px-4 py-1.5 font-mono text-base font-extrabold tracking-widest select-none text-[#1D0A69] bg-[radial-gradient(#CFD8DC_1px,transparent_1px)] [background-size:8px_8px]">
                    {captchaCode}
                  </div>
                  <input
                    type="text"
                    className="gov-input text-xs font-mono uppercase font-bold"
                    placeholder="ENTER CAPTCHA"
                    value={captchaInput}
                    onChange={(e) => setCaptchaInput(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Affirmative Action Declaration */}
              {roleTab === 'applicant' && (
                <label className="flex items-start gap-2.5 cursor-pointer text-xs text-[#263238] pt-1">
                  <input
                    type="checkbox"
                    checked={affirmed}
                    onChange={(e) => setAffirmed(e.target.checked)}
                    className="mt-0.5 rounded text-[#1D0A69]"
                    required
                  />
                  <span>
                    {language === 'hi'
                      ? 'मैं प्रमाणित करता/करती हूँ कि मैं भारत के संविधान के अनुच्छेद 342 के तहत अधिसूचित अनुसूचित जनजाति (ST) का पात्र सदस्य हूँ।'
                      : 'I affirm that I am applying under Scheduled Tribe (ST) affirmative action provisions as per Article 342 of the Constitution of India.'}
                  </span>
                </label>
              )}

              {/* Sign In CTA */}
              <button
                type="submit"
                className="w-full bg-[#1D0A69] hover:bg-[#15074D] text-white font-bold py-3 px-4 rounded text-xs transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                <Lock className="w-4 h-4" />
                <span>
                  {roleTab === 'applicant'
                    ? (language === 'hi' ? 'छात्र पोर्टल में प्रवेश करें' : 'Sign In to Student Portal')
                    : (language === 'hi' ? 'अधिकारी कार्यक्षेत्र में प्रवेश' : 'Sign In to Scrutiny Workbench')}
                </span>
                <ArrowRight className="w-4 h-4" />
              </button>

              {/* First Time Student Banner */}
              {roleTab === 'applicant' && (
                <div className="bg-[#FFFDE7] border border-[#FFE082] p-4 rounded text-xs space-y-1.5">
                  <strong className="text-[#7A5E00] block font-bold">
                    {language === 'hi' ? 'पहली बार आवेदन कर रहे हैं? (New Student?)' : 'First Time ST Applicant?'}
                  </strong>
                  <p className="text-[#5D4037]">
                    Generate your lifetime One-Time Registration (OTR) with Aadhaar e-KYC to apply across all 5 MoTA schemes.
                  </p>
                  <button
                    type="button"
                    onClick={onNavigateRegister}
                    className="text-[#1D0A69] font-bold hover:underline inline-flex items-center gap-1 pt-1"
                  >
                    <span>Register New ST Candidate (नया पंजीकरण)</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

            </form>
          </div>

          {/* Right Column: Sovereign Guidelines & Trust Matrix (5 cols) */}
          <div className="lg:col-span-5 space-y-5 text-xs">
            
            {/* Pre-requisites Dossier */}
            <div className="bg-white border border-[#CFD8DC] rounded-lg p-5 space-y-3 shadow-xs">
              <h3 className="font-bold text-[#1D0A69] font-serif text-sm border-b border-[#ECEFF1] pb-2">
                Mandatory Prerequisites Before Sign In
              </h3>
              
              <ul className="space-y-3">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-[#198754] flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-[#150202]">Aadhaar-Linked Active Mobile:</strong>
                    <p className="text-[#546E7A]">Required for OTP delivery and cryptographic e-Sign under IT Act 2000.</p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-[#198754] flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-[#150202]">Revenue ST Caste Certificate:</strong>
                    <p className="text-[#546E7A]">Issued by authorized Tehsildar/SDO with permanent digital verification code.</p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-[#198754] flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-[#150202]">Active NPCI-Mapped Bank Account:</strong>
                    <p className="text-[#546E7A]">Direct Benefit Transfer (DBT) is credited solely via Aadhaar-seeded accounts.</p>
                  </div>
                </li>
              </ul>
            </div>

            {/* Legal Warning Notice */}
            <div className="p-4 bg-[#FFEBEE] border border-[#EF9A9A] rounded-lg text-[#B71C1C] space-y-2">
              <div className="flex items-center gap-2 font-bold text-xs">
                <ShieldAlert className="w-4 h-4 text-[#C62828] flex-shrink-0" />
                <span>Statutory Warning (Sections 43 & 66, IT Act 2000)</span>
              </div>
              <p className="text-[11px] leading-relaxed">
                Falsification of caste, income, or enrollment credentials on this sovereign portal is a non-bailable criminal offense. All IP addresses, DSC tokens, and evidentiary uploads are digitally fingerprinted with SHA-256 ledgers.
              </p>
            </div>

            {/* Support Desk */}
            <div className="bg-[#F8F9FA] border border-[#CFD8DC] rounded-lg p-4 text-[11px] text-[#546E7A] space-y-1">
              <strong className="text-[#150202] block">National Scholarship Helpdesk:</strong>
              <div>Toll-Free Helpline: <strong>1800-11-7788</strong> (Monday to Friday 09:30 - 18:00 IST)</div>
              <div>Technical Queries: <strong>mota-support@gov.in</strong></div>
            </div>

          </div>

        </div>
      </main>
    </div>
  );
};
