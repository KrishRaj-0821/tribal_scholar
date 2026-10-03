import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { profileApi } from '../../services/api';
import { TribalPattern } from '../common/TribalPattern';
import { 
  User, CheckCircle2, AlertCircle, RefreshCw, 
  Save, Sparkles, FileCheck
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const ApplicantProfileView: React.FC = () => {
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [gender, setGender] = useState('MALE');
  const [dob, setDob] = useState('');
  const [community, setCommunity] = useState('ST');
  const [casteCertNo, setCasteCertNo] = useState('');
  const [income, setIncome] = useState<number>(0);
  const [incomeCertNo, setIncomeCertNo] = useState('');
  const [completionPct, setCompletionPct] = useState(0);

  useEffect(() => {
    const fetchProfile = async () => {
      setLoading(true);
      try {
        const prof = await profileApi.getProfile();
        if (prof) {
          setFirstName(prof.first_name || '');
          setLastName(prof.last_name || '');
          setEmail(prof.email || user?.email || '');
          setPhone(prof.phone_number || '');
          setGender(prof.gender || 'MALE');
          setDob(prof.date_of_birth || '');
          setCommunity(prof.community || 'ST');
          setCasteCertNo(prof.caste_certificate_number || '');
          setIncome(Number(prof.annual_family_income || 0));
          setIncomeCertNo(prof.income_certificate_number || '');
          setCompletionPct(prof.completion_percentage || 0);
        }
      } catch (e: any) {
        setErrorMsg(e.message || 'Failed to load profile.');
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const updated = await profileApi.updateProfile({
        user: {
          first_name: firstName,
          last_name: lastName,
          email,
          phone_number: phone,
        },
        gender,
        date_of_birth: dob || null,
        community,
        caste_certificate_number: casteCertNo,
        annual_family_income: income,
        income_certificate_number: incomeCertNo,
      });

      setCompletionPct(updated.completion_percentage || 100);
      setSuccessMsg('✓ Profile information updated and synchronized across all scholarship applications.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-[#F4F6F8] min-h-screen pb-20">
      
      {/* Header */}
      <div className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="woven" opacity={0.07} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-[#FFC107]">
                <User className="w-6 h-6" />
              </div>
              <div>
                <div className="text-xs font-semibold text-[#FFC107]">
                  ONE-TIME REGISTRATION (OTR) PROFILE
                </div>
                <h1 className="text-2xl font-bold font-serif text-white tracking-tight">
                  Permanent ST Applicant Profile
                </h1>
                <p className="text-xs text-[#EBEAEA]/90 mt-0.5">
                  Keep your demographic, community, and academic parameters up to date for instant eligibility matching.
                </p>
              </div>
            </div>

            {/* Profile Completion Indicator */}
            <div className="flex items-center gap-3 bg-white/10 px-4 py-2 rounded-xl border border-white/20 flex-shrink-0">
              <div className="text-right">
                <div className="text-[10px] uppercase font-bold text-[#FFC107]">Profile Completion</div>
                <div className="text-base font-extrabold text-white">{completionPct}%</div>
              </div>
              <Sparkles className="w-5 h-5 text-[#FFC107]" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Form */}
      <div className="gov-container py-8 max-w-4xl mx-auto">
        
        {successMsg && (
          <div className="mb-5 bg-[#E8F5E9] border border-[#A5D6A7] text-[#1B5E20] p-3 rounded-lg text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-[#2E7D32]" />
            <span>{successMsg}</span>
          </div>
        )}

        {errorMsg && (
          <div className="mb-5 bg-[#FFEBEE] border border-[#FFCDD2] text-[#C62828] p-3 rounded-lg text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {loading ? (
          <div className="bg-white p-12 rounded-xl border border-[#CFD8DC] text-center">
            <RefreshCw className="w-8 h-8 animate-spin text-[#1D0A69] mx-auto mb-3" />
            <p className="text-xs font-bold text-[#546E7A]">Loading applicant profile records...</p>
          </div>
        ) : (
          <form onSubmit={handleSave} className="bg-white rounded-xl shadow-xs border border-[#CFD8DC] p-6 sm:p-8 space-y-6">
            
            {/* 1. Personal Information */}
            <div>
              <h2 className="text-sm font-bold text-[#1D0A69] mb-3 pb-2 border-b border-[#ECEFF1] flex items-center gap-2">
                <User className="w-4 h-4 text-[#1D0A69]" />
                <span>Personal & Contact Information</span>
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">First Name</label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Last Name</label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Phone Number (Aadhaar Seeded)</label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Date of Birth</label>
                  <input
                    type="date"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Gender</label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  >
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="OTHER">Other / Transgender</option>
                  </select>
                </div>
              </div>
            </div>

            {/* 2. Community & Financial */}
            <div className="pt-2">
              <h2 className="text-sm font-bold text-[#1D0A69] mb-3 pb-2 border-b border-[#ECEFF1] flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-[#1D0A69]" />
                <span>Community & Financial Parameters</span>
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Community Category</label>
                  <select
                    value={community}
                    onChange={(e) => setCommunity(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  >
                    <option value="ST">Scheduled Tribe (ST)</option>
                    <option value="PVTG">Particularly Vulnerable Tribal Group (PVTG)</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Caste Certificate Number</label>
                  <input
                    type="text"
                    value={casteCertNo}
                    onChange={(e) => setCasteCertNo(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Gross Annual Family Income (INR)</label>
                  <input
                    type="number"
                    value={income}
                    onChange={(e) => setIncome(Number(e.target.value))}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="block font-bold text-[#37474F] mb-1">Income Certificate Number</label>
                  <input
                    type="text"
                    value={incomeCertNo}
                    onChange={(e) => setIncomeCertNo(e.target.value)}
                    className="w-full p-2.5 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
              </div>
            </div>

            {/* Save Button */}
            <div className="pt-4 border-t border-[#ECEFF1] flex items-center justify-between">
              <Link
                to="/documents"
                className="text-xs text-[#1D0A69] font-bold hover:underline"
              >
                Go to Document Vault →
              </Link>

              <button
                type="submit"
                disabled={saving}
                className="bg-[#1D0A69] hover:bg-[#15074D] text-white px-6 py-2.5 rounded font-bold text-xs flex items-center gap-2 shadow-xs"
              >
                {saving ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    <span>Save Profile Changes</span>
                  </>
                )}
              </button>
            </div>

          </form>
        )}

      </div>
    </div>
  );
};
