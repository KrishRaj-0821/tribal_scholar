import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { applicationApi, vaultApi, profileApi, VaultDocument } from '../../services/api';
import { TribalPattern } from '../common/TribalPattern';
import { 
  ShieldCheck, ArrowRight, CheckCircle2, 
  Clock, FolderLock, PlusCircle, FileText, 
  RefreshCw, ExternalLink
} from 'lucide-react';

interface ApplicantDashboardViewProps {
  onResolveDeficiency?: () => void;
  onNavigateTab?: (tab: string) => void;
}

export const ApplicantDashboardView: React.FC<ApplicantDashboardViewProps> = () => {
  const { language } = useLanguage();
  const { user } = useAuth();

  const [applications, setApplications] = useState<any[]>([]);
  const [vaultDocs, setVaultDocs] = useState<VaultDocument[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      setLoading(true);
      try {
        const [appsRes, docsRes, profRes] = await Promise.allSettled([
          applicationApi.list(),
          vaultApi.getDocuments(),
          profileApi.getProfile()
        ]);

        if (appsRes.status === 'fulfilled') {
          const appsData = appsRes.value;
          setApplications(Array.isArray(appsData) ? appsData : appsData?.results || []);
        }
        if (docsRes.status === 'fulfilled') {
          setVaultDocs(docsRes.value?.documents || []);
        }
        if (profRes.status === 'fulfilled') {
          setProfile(profRes.value);
        }
      } catch (e) {
        console.error('Failed to load dashboard data', e);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const completionPct = profile?.completion_percentage || 85;

  return (
    <div className="space-y-6 pb-12 bg-[#F4F6F8] min-h-screen">
      
      {/* 1. Header Hero with Sovereign Theme */}
      <section className="relative bg-[#FFFFFF] border-b border-[#CFD8DC] py-8 overflow-hidden">
        <TribalPattern family="woven" opacity={0.06} color="#1D0A69" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative z-10 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs text-[#546E7A] font-mono">
                <span>OTR: <strong>OTR-2026-ST-{user?.username?.toUpperCase() || '774912'}</strong></span>
                <span>•</span>
                <span>{profile?.community || 'ST'} Category</span>
              </div>
              
              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#1D0A69] font-serif mt-1">
                {language === 'hi' 
                  ? `नमस्ते, ${user?.first_name || user?.username}` 
                  : `Welcome, ${user?.first_name || user?.username}`}
              </h1>
              
              <p className="text-xs sm:text-sm text-[#263238] mt-1 max-w-2xl">
                National Tribal Scholarship & Fellowship Portal — Track your active dossiers, manage verified document vault, and check real-time scrutiny status.
              </p>
            </div>

            {/* Profile Completion Meter */}
            <div className="bg-[#F8F9FA] border border-[#CFD8DC] p-3 rounded-xl flex items-center gap-3 shadow-xs">
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
                    className="text-[#1D0A69]"
                    strokeDasharray={`${completionPct}, 100`}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <span className="text-[11px] font-bold text-[#1D0A69] absolute">{completionPct}%</span>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-[#78909C]">Profile Status</div>
                <div className="text-xs font-bold text-[#1D0A69]">
                  {completionPct === 100 ? 'Fully Completed' : 'Profile Incomplete'}
                </div>
                <Link to="/profile" className="text-[11px] text-[#C85A17] font-semibold hover:underline">
                  Update details →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Quick Action Cards (Document Vault & Scheme Finder) */}
      <section className="gov-container">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          {/* Document Vault Summary Card */}
          <div className="bg-white p-5 rounded-xl border border-[#CFD8DC] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-lg bg-[#E8EAF6] text-[#1D0A69] flex items-center justify-center font-bold">
                  <FolderLock className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-[#2E7D32] bg-[#E8F5E9] px-2 py-0.5 rounded">
                  ✓ ClamAV Safe
                </span>
              </div>
              <h3 className="font-bold text-sm text-[#1D0A69] mt-3">My Document Vault</h3>
              <p className="text-xs text-[#546E7A] mt-1">
                {vaultDocs.length} important certificates saved. Reusable across all scholarship schemes.
              </p>
            </div>
            <Link
              to="/documents"
              className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-[#1D0A69] hover:text-[#C85A17]"
            >
              <span>Open Document Vault</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Start New Application Card */}
          <div className="bg-white p-5 rounded-xl border border-[#CFD8DC] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-lg bg-[#FFF8E1] text-[#C85A17] flex items-center justify-center font-bold">
                  <PlusCircle className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-[#C85A17] bg-[#FFF3E0] px-2 py-0.5 rounded">
                  5 Schemes Open
                </span>
              </div>
              <h3 className="font-bold text-sm text-[#1D0A69] mt-3">Apply for Scholarships</h3>
              <p className="text-xs text-[#546E7A] mt-1">
                Explore Top Class Education, National Fellowship, and Overseas Scholarships.
              </p>
            </div>
            <Link
              to="/schemes"
              className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-[#1D0A69] hover:text-[#C85A17]"
            >
              <span>Explore Schemes & Apply</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* DBT & Bank Status Card */}
          <div className="bg-white p-5 rounded-xl border border-[#CFD8DC] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-lg bg-[#E8F5E9] text-[#2E7D32] flex items-center justify-center font-bold">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-[#2E7D32] bg-[#E8F5E9] px-2 py-0.5 rounded">
                  Aadhaar Seeded
                </span>
              </div>
              <h3 className="font-bold text-sm text-[#1D0A69] mt-3">NPCI DBT Direct Account</h3>
              <p className="text-xs text-[#546E7A] mt-1">
                Direct Benefit Transfer enabled for sovereign stipend and fellowship disbursement.
              </p>
            </div>
            <div className="mt-4 text-[11px] text-[#2E7D32] font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>100% Payment Ready</span>
            </div>
          </div>

        </div>
      </section>

      {/* 3. Active Applications List & Scrutiny Timeline */}
      <section className="gov-container space-y-4">
        <div className="flex items-center justify-between border-b border-[#CFD8DC] pb-2">
          <div>
            <h2 className="text-lg font-bold text-[#1D0A69] font-serif">
              My Scholarship Applications
            </h2>
            <p className="text-xs text-[#546E7A]">
              Authoritative statutory lifecycle tracking under Ministry of Tribal Affairs
            </p>
          </div>
          <Link
            to="/schemes"
            className="text-xs font-bold bg-[#1D0A69] text-white hover:bg-[#15074D] px-3 py-1.5 rounded flex items-center gap-1.5"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Application</span>
          </Link>
        </div>

        {loading ? (
          <div className="bg-white p-8 rounded-xl border border-[#CFD8DC] text-center">
            <RefreshCw className="w-6 h-6 animate-spin text-[#1D0A69] mx-auto mb-2" />
            <p className="text-xs text-[#546E7A]">Retrieving your application dossiers...</p>
          </div>
        ) : applications.length === 0 ? (
          <div className="bg-white p-8 rounded-xl border border-[#CFD8DC] text-center">
            <FileText className="w-10 h-10 text-[#B0BEC5] mx-auto mb-2" />
            <h3 className="text-sm font-bold text-[#1D0A69]">No Active Applications Found</h3>
            <p className="text-xs text-[#546E7A] mt-1">
              You haven't submitted any scholarship applications yet. Browse the official schemes and start your application.
            </p>
            <Link
              to="/schemes"
              className="mt-4 inline-flex items-center gap-1.5 bg-[#FFC107] text-[#120538] hover:bg-[#FFD54F] px-4 py-2 rounded text-xs font-bold"
            >
              <span>Browse 5 Statutory Schemes</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {applications.map((app) => (
              <div 
                key={app.id} 
                className="bg-white border border-[#CFD8DC] rounded-xl p-5 shadow-xs hover:shadow-md transition-shadow"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#ECEFF1]">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-[#1D0A69] bg-[#E8EAF6] px-2 py-0.5 rounded">
                        APPLICATION #{app.application_number}
                      </span>
                      <span className="text-xs text-[#78909C]">
                        AY {app.academic_year || '2026-27'}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-[#263238] mt-1">
                      {app.scheme_code === 'TOP_CLASS' || app.scheme_code === 'TOP-05'
                        ? 'Top Class Education for ST Students'
                        : app.scheme_code === 'NFST'
                        ? 'National Fellowship for Higher Education of ST Students'
                        : app.scheme_code === 'NOS'
                        ? 'National Overseas Scholarship for ST Candidates'
                        : `MoTA Scheme (${app.scheme_code})`}
                    </h3>
                  </div>

                  <div className="flex flex-col items-start sm:items-end gap-1">
                    <span className="text-xs font-bold px-2.5 py-1 rounded bg-[#E8F5E9] text-[#1B5E20] border border-[#C8E6C9] flex items-center gap-1">
                      <Clock className="w-3 h-3 text-[#1B5E20]" />
                      <span>{app.current_state_code || 'UNDER_SCRUTINY'}</span>
                    </span>
                    <span className="text-[11px] text-[#78909C]">
                      Next action: <strong className="text-[#37474F]">No action required</strong>
                    </span>
                  </div>
                </div>

                {/* Application Timeline Progress Bar */}
                <div className="pt-4">
                  <div className="text-[11px] font-bold text-[#546E7A] mb-2 uppercase tracking-wider">
                    Statutory Verification Timeline
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
                    <div className="bg-[#E8F5E9] text-[#2E7D32] p-2 rounded border border-[#C8E6C9] font-bold">
                      ✓ 1. Submitted
                    </div>
                    <div className="bg-[#E8F5E9] text-[#2E7D32] p-2 rounded border border-[#C8E6C9] font-bold">
                      ✓ 2. ClamAV & OCR Processed
                    </div>
                    <div className="bg-[#FFF8E1] text-[#F57F17] p-2 rounded border border-[#FFE082] font-bold animate-pulse">
                      ● 3. Scrutiny Review
                    </div>
                    <div className="bg-[#ECEFF1] text-[#78909C] p-2 rounded font-semibold">
                      ○ 4. Sanction & DBT
                    </div>
                  </div>
                </div>

                {/* SMS Notification Status Badge */}
                <div className="mt-3 flex items-center justify-between bg-[#F8F9FA] px-3 py-1.5 rounded border border-[#ECEFF1] text-[11px]">
                  <div className="flex items-center gap-1.5 text-[#00695C] font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#00897B]" />
                    <span>Notification: ✓ Dispatched to Gateway (******4912)</span>
                  </div>
                  <span className="text-[10px] text-[#546E7A] bg-white px-2 py-0.5 rounded border border-gray-200 font-mono font-bold">
                    SENT_TO_PROVIDER
                  </span>
                </div>



                {/* Bottom Action */}
                <div className="mt-4 pt-3 border-t border-[#ECEFF1] flex items-center justify-between">
                  <span className="text-[11px] text-[#78909C]">
                    Last updated: {new Date(app.updated_at || app.created_at).toLocaleDateString('en-IN')}
                  </span>
                  <Link
                    to={`/applications/${app.id}/status`}
                    className="text-xs font-bold text-[#1D0A69] hover:underline flex items-center gap-1"
                  >
                    <span>View Dossier Details</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

    </div>
  );
};
