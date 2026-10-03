import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { profileApi } from '../../services/api';
import { TribalPattern } from '../common/TribalPattern';
import { 
  ShieldCheck, ArrowRight, ArrowLeft, 
  AlertCircle, RefreshCw, User, 
  FileCheck, Building, Sparkles
} from 'lucide-react';

export const RegistrationView: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [phase, setPhase] = useState<'REGISTER' | 'COMPLETE_PROFILE'>('REGISTER');

  // Registration Form
  const [username, setUsername] = useState('rajesh_soren');
  const [email, setEmail] = useState('rajesh.soren@tribal.gov.in');
  const [password, setPassword] = useState('Tribal@2026');
  const [phone, setPhone] = useState('9876543210');
  const [community, setCommunity] = useState('ST');
  const [income, setIncome] = useState<number>(350000);

  // Profile Onboarding Form
  const [firstName, setFirstName] = useState('Rajeshwar');
  const [lastName, setLastName] = useState('Soren');
  const [gender, setGender] = useState('MALE');
  const [dob, setDob] = useState('2003-08-14');
  const [casteCertNo, setCasteCertNo] = useState('JH/ST/2024/77491');
  const [stateDomicile, setStateDomicile] = useState('JHARKHAND');
  const [district, setDistrict] = useState('Ranchi');
  const [institution, setInstitution] = useState('IIT Kharagpur');
  const [course, setCourse] = useState('B.Tech Computer Science');

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Compute profile completion percentage
  const calculateCompletion = () => {
    const fields = [
      firstName, lastName, email, phone, community,
      casteCertNo, income, dob, gender, stateDomicile, district, institution
    ];
    const filled = fields.filter(f => f !== '' && f !== null && f !== undefined).length;
    return Math.round((filled / fields.length) * 100);
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password: password.trim(),
        phone_number: phone.trim(),
        community,
        annual_family_income: Number(income),
      });

      // Advance to profile onboarding phase
      setPhase('COMPLETE_PROFILE');
    } catch (err: any) {
      setErrorMsg(err.message || 'Registration failed. Please check details.');
    } finally {
      setLoading(false);
    }
  };

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    try {
      await profileApi.updateProfile({
        user: {
          first_name: firstName,
          last_name: lastName,
          phone_number: phone,
        },
        gender,
        date_of_birth: dob,
        caste_certificate_number: casteCertNo,
        annual_family_income: income,
      });

      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update profile details.');
    } finally {
      setLoading(false);
    }
  };

  const completionPct = calculateCompletion();

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Official MoTA Sovereign Header */}
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
                <div className="flex items-center gap-2 text-xs font-medium text-[#FFC107]">
                  <span>PERMANENT SCHOLARSHIP IDENTIFIER</span>
                  <span>•</span>
                  <span>OTR ONBOARDING</span>
                </div>
                <h1 className="text-xl sm:text-2xl font-bold font-serif text-white tracking-tight">
                  {phase === 'REGISTER' 
                    ? 'One-Time Registration (OTR) — New ST Candidate Onboarding'
                    : 'Complete Your Applicant Profile'}
                </h1>
                <p className="text-xs text-[#EBEAEA]/80">
                  Unified Central ST Scholarship Portal under Article 342 of the Constitution of India
                </p>
              </div>
            </div>

            {phase === 'REGISTER' && (
              <Link
                to="/login"
                className="text-xs text-white/90 hover:text-white underline font-semibold flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Login</span>
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* 2. Main Content Container */}
      <div className="gov-container py-8">
        
        {phase === 'REGISTER' ? (
          <div className="max-w-xl mx-auto bg-white rounded-xl shadow-md border border-[#CFD8DC] p-6 sm:p-8">
            <div className="mb-6">
              <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-[#E8EAF6] text-[#1D0A69]">
                Step 1 of 2: Create Sovereign ST Identity
              </span>
              <h2 className="text-lg font-bold text-[#1D0A69] mt-1">
                Candidate Account Registration
              </h2>
              <p className="text-xs text-[#546E7A] mt-0.5">
                Public registration creates an official APPLICANT account. Officers and authorities are provisioned via administrative channels.
              </p>
            </div>

            {errorMsg && (
              <div className="mb-5 bg-[#FFEBEE] border border-[#FFCDD2] text-[#C62828] p-3 rounded text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleRegisterSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                    Desired Username *
                  </label>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                    Email Address *
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                    Password *
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                    Mobile Phone (Aadhaar linked) *
                  </label>
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                    Community Category *
                  </label>
                  <select
                    value={community}
                    onChange={(e) => setCommunity(e.target.value)}
                    className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                  >
                    <option value="ST">Scheduled Tribe (ST)</option>
                    <option value="PVTG">Particularly Vulnerable Tribal Group (PVTG)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                    Gross Annual Family Income (₹) *
                  </label>
                  <input
                    type="number"
                    required
                    value={income}
                    onChange={(e) => setIncome(Number(e.target.value))}
                    className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded-lg bg-[#F8F9FA] focus:bg-white focus:outline-none focus:border-[#1D0A69]"
                  />
                </div>
              </div>

              <div className="p-3 bg-[#E8F5E9] rounded-lg border border-[#C8E6C9] text-xs text-[#2E7D32] flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>
                  Your registration automatically generates your permanent ST Scholarship OTR number and initializes your secure Document Vault.
                </span>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#1D0A69] hover:bg-[#15074D] disabled:opacity-50 text-white py-3 rounded-lg font-bold text-xs shadow-sm flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Registering ST Candidate...</span>
                  </>
                ) : (
                  <>
                    <span>Create Applicant Account & Continue</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>
        ) : (
          /* Step 2: COMPLETE YOUR PROFILE (Requirement 10) */
          <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-md border border-[#CFD8DC] p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-[#ECEFF1]">
              <div>
                <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-[#E8F5E9] text-[#2E7D32]">
                  Registration Successful
                </span>
                <h2 className="text-xl font-bold text-[#1D0A69] mt-1">
                  COMPLETE YOUR PROFILE
                </h2>
                <p className="text-xs text-[#546E7A]">
                  Add your academic and community information to unlock personalized scheme matching.
                </p>
              </div>

              {/* Profile Completion Meter (0 -> 100%) */}
              <div className="flex items-center gap-3 bg-[#F8F9FA] px-4 py-2 rounded-xl border border-[#CFD8DC]">
                <div className="text-right">
                  <div className="text-[10px] uppercase font-bold text-[#78909C]">Profile Completion</div>
                  <div className="text-base font-extrabold text-[#1D0A69]">{completionPct}%</div>
                </div>
                <div className="w-12 h-12 relative flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-[#ECEFF1]"
                      strokeWidth="3.5"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="text-[#FFC107]"
                      strokeDasharray={`${completionPct}, 100`}
                      strokeWidth="3.5"
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <Sparkles className="w-4 h-4 text-[#FFC107] absolute" />
                </div>
              </div>
            </div>

            {errorMsg && (
              <div className="mb-5 bg-[#FFEBEE] border border-[#FFCDD2] text-[#C62828] p-3 rounded text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleProfileSave} className="space-y-5">
              {/* Personal Information */}
              <div className="space-y-3">
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-[#37474F] flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-[#1D0A69]" />
                  <span>Personal Information</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">First Name</label>
                    <input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">Last Name</label>
                    <input
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">Date of Birth</label>
                    <input
                      type="date"
                      value={dob}
                      onChange={(e) => setDob(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">Gender</label>
                    <select
                      value={gender}
                      onChange={(e) => setGender(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    >
                      <option value="MALE">Male</option>
                      <option value="FEMALE">Female</option>
                      <option value="OTHER">Other / Transgender</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Community & Domicile */}
              <div className="space-y-3 pt-3 border-t border-[#ECEFF1]">
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-[#37474F] flex items-center gap-1.5">
                  <FileCheck className="w-3.5 h-3.5 text-[#1D0A69]" />
                  <span>Community & Domicile Information</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">ST Certificate Number</label>
                    <input
                      type="text"
                      value={casteCertNo}
                      onChange={(e) => setCasteCertNo(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">State Domicile</label>
                    <input
                      type="text"
                      value={stateDomicile}
                      onChange={(e) => setStateDomicile(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">Home District</label>
                    <input
                      type="text"
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                </div>
              </div>

              {/* Academic Profile */}
              <div className="space-y-3 pt-3 border-t border-[#ECEFF1]">
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-[#37474F] flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-[#1D0A69]" />
                  <span>Academic Information</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">Institution / University</label>
                    <input
                      type="text"
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#1D0A69] mb-1">Course of Study</label>
                    <input
                      type="text"
                      value={course}
                      onChange={(e) => setCourse(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                </div>
              </div>

              {/* Submission & Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-[#ECEFF1]">
                <button
                  type="button"
                  onClick={() => navigate('/documents')}
                  className="text-xs text-[#1D0A69] hover:underline font-bold"
                >
                  Upload Documents to Vault First →
                </button>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full sm:w-auto bg-[#1D0A69] text-white hover:bg-[#15074D] px-6 py-2.5 rounded font-bold text-xs flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Saving Profile...</span>
                    </>
                  ) : (
                    <>
                      <span>Save Profile & Open Dashboard</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

      </div>
    </div>
  );
};
