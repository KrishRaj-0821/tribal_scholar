import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { 
  Home, Compass, FileSpreadsheet, ShieldCheck, 
  Settings, MessageSquareWarning, LogIn, LogOut, 
  FolderLock, User, HelpCircle, Shield
} from 'lucide-react';

export const PortalNavigationBar: React.FC = () => {
  const { language } = useLanguage();
  const { user, role, authState, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1.5 py-3 px-3.5 border-b-2 text-xs font-bold transition-colors select-none ${
      isActive
        ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
        : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
    }`;

  return (
    <nav 
      className="hidden md:block bg-[#1D0A69] text-white select-none border-b border-[#0F4C81] sticky top-0 z-40 shadow-sm"
      role="navigation"
      aria-label="Primary Portal Navigation"
    >
      <div className="gov-container flex items-center justify-between">
        
        {/* Left Links - Strictly Bound to Role */}
        <div className="flex items-center gap-1 overflow-x-auto text-xs font-bold">
          
          {/* Public Links (Available to public & applicants) */}
          {authState !== 'AUTHENTICATED_OFFICER' && authState !== 'AUTHENTICATED_ADMIN' && (
            <>
              <NavLink to="/" end className={navLinkClass}>
                <Home className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'मुख्य पृष्ठ' : 'Home'}</span>
              </NavLink>

              <NavLink to="/schemes" className={navLinkClass}>
                <Compass className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'योजनाएं (5 Schemes)' : 'All Schemes'}</span>
              </NavLink>
            </>
          )}

          {/* APPLICANT ONLY Links */}
          {authState === 'AUTHENTICATED_APPLICANT' && (
            <>
              <NavLink to="/dashboard" className={navLinkClass}>
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'आवेदक डैशबोर्ड' : 'Applicant Dashboard'}</span>
              </NavLink>

              <NavLink to="/documents" className={navLinkClass}>
                <FolderLock className="w-3.5 h-3.5 text-[#FFC107]" />
                <span className="text-[#FFC107]">{language === 'hi' ? 'दस्तावेज़ वॉल्ट' : 'Document Vault'}</span>
              </NavLink>

              <NavLink to="/profile" className={navLinkClass}>
                <User className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'मेरी प्रोफ़ाइल' : 'My Profile'}</span>
              </NavLink>

              <NavLink to="/grievance/my" className={navLinkClass}>
                <MessageSquareWarning className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'मेरी शिकायतें' : 'My Grievances'}</span>
              </NavLink>
            </>
          )}

          {/* OFFICER ONLY Links */}
          {authState === 'AUTHENTICATED_OFFICER' && (
            <>
              <NavLink to="/officer" end className={navLinkClass}>
                <ShieldCheck className="w-3.5 h-3.5 text-[#FFC107]" />
                <span>{language === 'hi' ? 'जांच कार्यक्षेत्र' : 'Officer Queue'}</span>
              </NavLink>

              <NavLink to="/officer/verification/APP-2026-001DB3" className={navLinkClass}>
                <Shield className="w-3.5 h-3.5 text-[#FFC107]" />
                <span>{language === 'hi' ? 'सत्यापन कार्यपीठ' : 'Verification Workbench'}</span>
              </NavLink>

              <NavLink to="/officer/audit" className={navLinkClass}>
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'ऑडिट लॉग' : 'Officer Audit'}</span>
              </NavLink>
            </>
          )}

          {/* ADMIN ONLY Links */}
          {authState === 'AUTHENTICATED_ADMIN' && (
            <>
              <NavLink to="/admin" end className={navLinkClass}>
                <Settings className="w-3.5 h-3.5 text-[#FFC107]" />
                <span>{language === 'hi' ? 'केंद्रीय प्रशासन' : 'Central Admin'}</span>
              </NavLink>

              <NavLink to="/admin/schemes" className={navLinkClass}>
                <Compass className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'योजना नियम' : 'Scheme Rules'}</span>
              </NavLink>

              <NavLink to="/admin/audit" className={navLinkClass}>
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'प्रशासनिक ऑडिट' : 'Statutory Audit'}</span>
              </NavLink>
            </>
          )}

          {/* Public Common Help Link */}
          {authState === 'PUBLIC' && (
            <>
              <NavLink to="/grievance" className={navLinkClass}>
                <MessageSquareWarning className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'शिकायत (CPGRAMS)' : 'CPGRAMS Grievance'}</span>
              </NavLink>

              <NavLink to="/help" className={navLinkClass}>
                <HelpCircle className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'सहायता' : 'Help & Guidelines'}</span>
              </NavLink>
            </>
          )}

        </div>

        {/* Right Action: Auth Status / Login / Logout */}
        <div className="flex items-center gap-2">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-bold text-white flex items-center gap-1 justify-end">
                  <span className="w-2 h-2 rounded-full bg-[#198754]"></span>
                  <span>{user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user.username}</span>
                </div>
                <div className="text-[10px] text-[#FFC107] font-mono">
                  {role}
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 py-1 px-3 rounded text-xs font-bold bg-[#D32F2F] hover:bg-[#B71C1C] text-white transition-colors shadow-2xs"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'लॉगआउट' : 'Logout'}</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <NavLink
                to="/login"
                className="flex items-center gap-1.5 py-1 px-3 rounded text-xs font-bold bg-[#FFC107] text-[#150202] hover:bg-[#FFD54F] transition-colors shadow-2xs"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>{language === 'hi' ? 'नागरिक प्रवेश' : 'Citizen Login'}</span>
              </NavLink>

              <NavLink
                to="/register"
                className="flex items-center gap-1.5 py-1 px-2.5 rounded text-xs font-bold border border-[#546E7A] text-white hover:bg-[#15074D] transition-colors"
              >
                <span>OTR Register</span>
              </NavLink>
            </div>
          )}
        </div>

      </div>
    </nav>
  );
};
