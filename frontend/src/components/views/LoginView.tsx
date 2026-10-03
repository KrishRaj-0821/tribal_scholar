import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { authApi } from '../../services/api';
import { TribalPattern } from '../common/TribalPattern';
import { 
  Lock, RefreshCw, ArrowRight, KeyRound, 
  ShieldCheck, Eye, EyeOff, User, AlertCircle,
  Smartphone, CheckCircle2
} from 'lucide-react';

export const LoginView: React.FC = () => {
  const { language } = useLanguage();
  const { login, loginWithOTP } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Get redirect param from URL if visitor clicked 'Apply' while logged out
  const searchParams = new URLSearchParams(location.search);
  const redirectTarget = searchParams.get('redirect');

  const [loginTab, setLoginTab] = useState<'PASSWORD' | 'OTP'>('PASSWORD');

  // Password Login state
  const [identifier, setIdentifier] = useState('demo_applicant');
  const [password, setPassword] = useState('Tribal@2026');
  const [showPassword, setShowPassword] = useState(false);
  const [captchaInput, setCaptchaInput] = useState('');
  const [captchaCode, setCaptchaCode] = useState('7W9XK2');
  const [affirmed, setAffirmed] = useState(true);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Mobile OTP Login state
  const [mobile, setMobile] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpCooldown, setOtpCooldown] = useState(0);
  const [otpSending, setOtpSending] = useState(false);
  const [otpVerifying, setOtpVerifying] = useState(false);
  const [otpMessage, setOtpMessage] = useState<string | null>(null);
  const [otpError, setOtpError] = useState<string | null>(null);

  useEffect(() => {
    let timer: any = null;
    if (otpCooldown > 0) {
      timer = setInterval(() => {
        setOtpCooldown(prev => prev - 1);
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [otpCooldown]);

  const refreshCaptcha = () => {
    const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
    let res = '';
    for (let i = 0; i < 6; i++) {
      res += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setCaptchaCode(res);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password.trim()) {
      setErrorMessage('Please enter both your identifier and password.');
      return;
    }

    if (captchaInput.trim().toUpperCase() !== captchaCode) {
      setErrorMessage('Invalid security CAPTCHA code. Please re-enter.');
      refreshCaptcha();
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const { destination, role } = await login(identifier.trim(), password.trim());
      
      if (redirectTarget && role === 'APPLICANT') {
        navigate(redirectTarget, { replace: true });
      } else {
        navigate(destination, { replace: true });
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Login failed. Invalid credentials.');
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  const handleSendOTP = async () => {
    const cleanMobile = mobile.trim().replace(/\D/g, '');
    if (cleanMobile.length < 10) {
      setOtpError('Please enter a valid 10-digit Indian mobile number.');
      return;
    }

    setOtpSending(true);
    setOtpError(null);
    setOtpMessage(null);

    try {
      const res = await authApi.requestOTP(cleanMobile);
      setOtpSent(true);
      setOtpCooldown(60);
      setOtpMessage(res.message || `OTP dispatched via SMS to ${res.mobile_masked}`);
    } catch (err: any) {
      setOtpError(err.message || 'Failed to dispatch OTP. Please verify your mobile number or try again.');
    } finally {
      setOtpSending(false);
    }
  };

  const handleVerifyOTPSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanMobile = mobile.trim().replace(/\D/g, '');
    if (!cleanMobile || !otpCode.trim()) {
      setOtpError('Please enter both your registered mobile number and the 6-digit OTP.');
      return;
    }

    setOtpVerifying(true);
    setOtpError(null);

    try {
      const { destination, role } = await loginWithOTP(cleanMobile, otpCode.trim());
      if (redirectTarget && role === 'APPLICANT') {
        navigate(redirectTarget, { replace: true });
      } else {
        navigate(destination, { replace: true });
      }
    } catch (err: any) {
      setOtpError(err.message || 'Invalid or expired OTP. Please try again.');
    } finally {
      setOtpVerifying(false);
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
              <div className="bg-white p-2.5 rounded shadow-sm flex items-center justify-center flex-shrink-0">
                <img 
                  src="/mota-logo.png" 
                  alt="Ministry of Tribal Affairs Logo" 
                  className="h-12 sm:h-14 w-auto object-contain"
                />
              </div>

              <div className="space-y-0.5">
                <div className="flex items-center gap-2 text-xs font-medium text-[#FFC107]">
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

      {/* 2. Main Login Content */}
      <div className="gov-container py-10">
        <div className="max-w-md mx-auto bg-white rounded-xl shadow-md border border-[#CFD8DC] overflow-hidden">
          
          <div className="p-6 sm:p-8">
            <div className="text-center mb-6">
              <div className="w-12 h-12 bg-[#1D0A69]/10 rounded-full flex items-center justify-center mx-auto mb-2 text-[#1D0A69]">
                <KeyRound className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-[#1D0A69]">
                {language === 'hi' ? 'नागरिक एवं अधिकारी प्रवेश' : 'Citizen & Officer Login'}
              </h2>
              <p className="text-xs text-[#546E7A] mt-1">
                Enter your registered mobile, email, or username to securely access your portal.
              </p>
            </div>

            {/* Tab Switcher: Password vs Fast2SMS Mobile OTP */}
            <div className="flex border-b border-[#CFD8DC] mb-5">
              <button
                type="button"
                onClick={() => setLoginTab('PASSWORD')}
                className={`flex-1 py-2.5 text-xs font-bold text-center border-b-2 transition-all flex items-center justify-center gap-1.5 ${
                  loginTab === 'PASSWORD'
                    ? 'border-[#1D0A69] text-[#1D0A69] bg-[#E8EAF6]/40'
                    : 'border-transparent text-[#78909C] hover:text-[#1D0A69]'
                }`}
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Password Login</span>
              </button>
              <button
                type="button"
                onClick={() => setLoginTab('OTP')}
                className={`flex-1 py-2.5 text-xs font-bold text-center border-b-2 transition-all flex items-center justify-center gap-1.5 ${
                  loginTab === 'OTP'
                    ? 'border-[#1D0A69] text-[#1D0A69] bg-[#E8EAF6]/40'
                    : 'border-transparent text-[#78909C] hover:text-[#1D0A69]'
                }`}
              >
                <Smartphone className="w-3.5 h-3.5" />
                <span>Mobile OTP (SMS)</span>
              </button>
            </div>

            {loginTab === 'PASSWORD' ? (
              <>
                {errorMessage && (
                  <div className="mb-5 bg-[#FFEBEE] border border-[#FFCDD2] text-[#C62828] p-3 rounded text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  {/* Identifier Input */}
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                      Mobile Number / Email / Username
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#78909C]">
                        <User className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        required
                        placeholder="e.g. demo_applicant or mobile/email"
                        value={identifier}
                        onChange={(e) => setIdentifier(e.target.value)}
                        className="w-full pl-9 pr-3 py-2.5 text-xs border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                      />
                    </div>
                  </div>

                  {/* Password Input */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-bold text-[#1D0A69]">
                        Password
                      </label>
                    </div>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#78909C]">
                        <Lock className="w-4 h-4" />
                      </div>
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        placeholder="Enter password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full pl-9 pr-10 py-2.5 text-xs border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#78909C] hover:text-[#1D0A69]"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Security CAPTCHA */}
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                      Security Captcha
                    </label>
                    <div className="flex items-center gap-2">
                      <div className="bg-[#ECEFF1] border border-[#CFD8DC] px-3 py-2 rounded text-base font-mono font-extrabold tracking-widest text-[#1D0A69] select-none line-through">
                        {captchaCode}
                      </div>
                      <button
                        type="button"
                        onClick={refreshCaptcha}
                        className="p-2 text-[#546E7A] hover:text-[#1D0A69] hover:bg-[#ECEFF1] rounded"
                        title="Refresh CAPTCHA"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      <input
                        type="text"
                        required
                        placeholder="Enter characters"
                        value={captchaInput}
                        onChange={(e) => setCaptchaInput(e.target.value)}
                        className="flex-1 px-3 py-2 text-xs border border-[#CFD8DC] rounded-lg uppercase tracking-wider focus:outline-none focus:border-[#1D0A69]"
                      />
                    </div>
                  </div>

                  {/* Statutory Affirmation */}
                  <div className="flex items-start gap-2 pt-1">
                    <input
                      type="checkbox"
                      id="affirmed"
                      checked={affirmed}
                      onChange={(e) => setAffirmed(e.target.checked)}
                      className="mt-0.5 rounded text-[#1D0A69] focus:ring-[#1D0A69]"
                    />
                    <label htmlFor="affirmed" className="text-[11px] text-[#546E7A] leading-tight">
                      I affirm that I am the authorized account holder and agree to MoTA portal IT security regulations.
                    </label>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={loading || !affirmed}
                    className="w-full bg-[#1D0A69] hover:bg-[#15074D] disabled:opacity-50 text-white py-2.5 rounded-lg font-bold text-xs shadow-sm flex items-center justify-center gap-2 transition-all"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Verifying Credentials...</span>
                      </>
                    ) : (
                      <>
                        <span>{language === 'hi' ? 'सुरक्षित प्रवेश करें' : 'Sign In Securely'}</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>
              </>
            ) : (
              /* FAST2SMS MOBILE OTP LOGIN FORM */
              <div className="space-y-4">
                {otpError && (
                  <div className="bg-[#FFEBEE] border border-[#FFCDD2] text-[#C62828] p-3 rounded text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{otpError}</span>
                  </div>
                )}

                {otpMessage && (
                  <div className="bg-[#E8F5E9] border border-[#A5D6A7] text-[#1B5E20] p-3 rounded text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-[#2E7D32]" />
                    <span>{otpMessage}</span>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                    Registered Mobile Number (10 digits)
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#78909C] text-xs font-bold">
                        +91
                      </div>
                      <input
                        type="tel"
                        maxLength={10}
                        required
                        placeholder="e.g. 9876543210"
                        value={mobile}
                        onChange={(e) => setMobile(e.target.value.replace(/\D/g, ''))}
                        className="w-full pl-11 pr-3 py-2.5 text-xs border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69] font-mono tracking-wider"
                      />
                    </div>
                    <button
                      type="button"
                      disabled={otpSending || otpCooldown > 0 || mobile.length < 10}
                      onClick={handleSendOTP}
                      className="bg-[#1D0A69] hover:bg-[#15074D] disabled:opacity-50 text-white px-3 py-2.5 rounded-lg text-xs font-bold flex-shrink-0 transition-all flex items-center gap-1.5"
                    >
                      {otpSending ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          <span>Sending...</span>
                        </>
                      ) : otpCooldown > 0 ? (
                        <span>Resend ({otpCooldown}s)</span>
                      ) : (
                        <span>{otpSent ? 'Resend OTP' : 'Send OTP via SMS'}</span>
                      )}
                    </button>
                  </div>
                  <p className="text-[10px] text-[#78909C] mt-1">
                    Direct SMS dispatch through Fast2SMS Sovereign Gateway.
                  </p>
                </div>

                {otpSent && (
                  <form onSubmit={handleVerifyOTPSubmit} className="space-y-4 pt-2">
                    <div>
                      <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                        Enter 6-Digit One-Time Password (OTP)
                      </label>
                      <input
                        type="text"
                        maxLength={6}
                        required
                        placeholder="••••••"
                        value={otpCode}
                        onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                        className="w-full px-3 py-2.5 text-center text-lg tracking-widest font-mono font-bold border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                      />
                      <p className="text-[10px] text-[#78909C] mt-1 text-center">
                        Never share your OTP with anyone. Valid for 5 minutes.
                      </p>
                    </div>

                    <button
                      type="submit"
                      disabled={otpVerifying || otpCode.length !== 6}
                      className="w-full bg-[#198754] hover:bg-[#157347] disabled:opacity-50 text-white py-2.5 rounded-lg font-bold text-xs shadow-sm flex items-center justify-center gap-2 transition-all"
                    >
                      {otpVerifying ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Verifying OTP...</span>
                        </>
                      ) : (
                        <>
                          <span>Verify OTP & Sign In</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </form>
                )}
              </div>
            )}


            {/* Quick Persona Credentials for Pitch Showcase */}
            <div className="mt-5 p-3 rounded-lg bg-[#F8F9FA] border border-[#ECEFF1] text-[11px]">
              <div className="font-bold text-[#37474F] mb-1 flex items-center justify-between">
                <span>Synthetic Demo Persona Credentials:</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <button
                  type="button"
                  onClick={() => {
                    setIdentifier('demo_applicant');
                    setPassword('Tribal@2026');
                    setCaptchaInput(captchaCode);
                  }}
                  className="p-1.5 bg-white border border-[#CFD8DC] rounded hover:border-[#1D0A69] text-left"
                >
                  <div className="font-bold text-[#1D0A69]">ST Applicant</div>
                  <div className="text-[#546E7A]">demo_applicant</div>
                  <div className="text-[#78909C]">Tribal@2026</div>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIdentifier('demo_officer');
                    setPassword('Officer@2026');
                    setCaptchaInput(captchaCode);
                  }}
                  className="p-1.5 bg-white border border-[#CFD8DC] rounded hover:border-[#1D0A69] text-left"
                >
                  <div className="font-bold text-[#C85A17]">Scrutiny Officer</div>
                  <div className="text-[#546E7A]">demo_officer</div>
                  <div className="text-[#78909C]">Officer@2026</div>
                </button>
              </div>
            </div>

            {/* Register Link */}
            <div className="mt-6 pt-4 border-t border-[#ECEFF1] text-center text-xs text-[#546E7A]">
              <span>{language === 'hi' ? 'नया छात्र खाता चाहिए?' : 'New ST Applicant?'} </span>
              <Link 
                to="/register" 
                className="font-bold text-[#1D0A69] hover:underline"
              >
                {language === 'hi' ? 'एकल पंजीकरण (OTR) करें' : 'One-Time Registration (OTR)'}
              </Link>
            </div>

          </div>
        </div>
      </div>

    </div>
  );
};
