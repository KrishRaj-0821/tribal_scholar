import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { TribalPattern } from './TribalPattern';
import { 
  ShieldCheck, PhoneCall, LogIn, LogOut, 
  User, Menu, X, Home, Compass, FileSpreadsheet, 
  FolderLock, Shield, MessageSquareWarning, HelpCircle
} from 'lucide-react';

export const GovernmentHeader: React.FC = () => {
  const { language } = useLanguage();
  const { user, role, authState, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    setMobileMenuOpen(false);
    await logout();
    navigate('/login', { replace: true });
  };

  const closeMenu = () => setMobileMenuOpen(false);

  return (
    <header className="w-full bg-[#FFFFFF] border-b border-[#CFD8DC] select-none relative z-50" role="banner">
      {/* Top Tricolor Micro Stripe */}
      <div className="h-1 w-full flex" aria-hidden="true">
        <div className="w-1/3 bg-[#FF9933]"></div>
        <div className="w-1/3 bg-[#FFFFFF]"></div>
        <div className="w-1/3 bg-[#138808]"></div>
      </div>

      {/* Main Sovereign Ministry Header */}
      <div className="gov-container py-2.5 sm:py-3">
        <div className="flex items-center justify-between gap-2 sm:gap-4">
          
          {/* Left: Official Ministry of Tribal Affairs Identity Lockup */}
          <Link to="/" onClick={closeMenu} className="flex items-center gap-2.5 sm:gap-3 group">
            <img 
              src="/mota-logo.png" 
              alt="Ministry of Tribal Affairs | जनजातीय कार्य मंत्रालय | Government of India" 
              className="h-10 sm:h-14 md:h-16 w-auto object-contain flex-shrink-0"
            />
            <div className="border-l-2 border-[#1D0A69] pl-2 sm:pl-3 py-0.5">
              <div className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-[#C85A17]">
                {language === 'hi' ? 'भारत सरकार • राष्ट्रीय छात्रवृत्ति' : 'Government of India • Sovereign Portal'}
              </div>
              <div className="text-base sm:text-xl font-extrabold text-[#1D0A69] tracking-tight font-serif leading-tight">
                <span>Tribal Scholar</span>
              </div>
              <div className="hidden sm:block text-[11px] font-medium text-[#546E7A] line-clamp-1">
                {language === 'hi' ? 'जनजातीय राष्ट्रीय छात्रवृत्ति एवं अध्येतावृत्ति प्रबंधन प्रणाली' : 'National Scholarship & Fellowship Management System'}
              </div>
            </div>
          </Link>

          {/* Center/Right: Desktop Sovereign Indicators */}
          <div className="hidden xl:flex items-center gap-3 text-xs">
            <div className="flex items-center gap-2 bg-[#E8F5E9] border border-[#A5D6A7] px-2.5 py-1 rounded">
              <ShieldCheck className="w-3.5 h-3.5 text-[#198754]" />
              <div>
                <div className="font-bold text-[#198754] text-[11px] leading-tight">100% Direct DBT</div>
                <div className="text-[9px] text-[#263238]">Aadhaar-NPCI Seeded</div>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-[#F4F6F8] border border-[#CFD8DC] px-2.5 py-1 rounded">
              <PhoneCall className="w-3.5 h-3.5 text-[#0F4C81]" />
              <div>
                <div className="font-bold text-[#0F4C81] text-[11px] leading-tight">1800-11-7788</div>
                <div className="text-[9px] text-[#546E7A]">Toll-Free Helpline</div>
              </div>
            </div>
          </div>

          {/* Right Action: Auth Buttons & Mobile Menu Trigger */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2">
                {/* Authenticated User Badge */}
                <Link
                  to={role === 'APPLICANT' ? '/profile' : '/officer'}
                  className="flex items-center gap-1.5 bg-[#F4F6F8] hover:bg-[#E8EAF6] border border-[#CFD8DC] px-2 sm:px-3 py-1 rounded transition-colors text-left"
                  title="View Profile"
                >
                  <div className="w-6 h-6 rounded-full bg-[#1D0A69] text-white flex items-center justify-center font-bold text-[10px]">
                    {user.username.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="hidden sm:block">
                    <div className="text-xs font-bold text-[#1D0A69] line-clamp-1 max-w-[120px]">
                      {user.first_name ? `${user.first_name}` : user.username}
                    </div>
                    <div className="text-[9px] font-mono text-[#546E7A]">
                      {role === 'APPLICANT' ? 'ST Applicant' : role}
                    </div>
                  </div>
                </Link>

                {/* Direct Logout Button */}
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1 py-1 px-2.5 rounded text-xs font-bold bg-[#D32F2F] hover:bg-[#B71C1C] text-white transition-colors shadow-xs"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{language === 'hi' ? 'लॉगआउट' : 'Logout'}</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 sm:gap-2">
                <Link
                  to="/login"
                  className="flex items-center gap-1 py-1.5 px-3 rounded text-xs font-bold bg-[#FFC107] text-[#120538] hover:bg-[#FFD54F] transition-all shadow-xs border border-[#FFA000]"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>{language === 'hi' ? 'प्रवेश' : 'Login'}</span>
                </Link>

                <Link
                  to="/register"
                  className="hidden xs:flex items-center gap-1 py-1.5 px-2.5 rounded text-xs font-bold bg-[#1D0A69] text-white hover:bg-[#15074D] transition-colors"
                >
                  <span>{language === 'hi' ? 'पंजीकरण' : 'Register'}</span>
                </Link>
              </div>
            )}

            {/* Mobile Hamburger Drawer Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 text-[#1D0A69] hover:bg-[#F4F6F8] rounded border border-[#CFD8DC] transition-colors ml-1"
              aria-label="Toggle Navigation Menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>
      </div>

      {/* Sovereign Cultural Divider Band */}
      <TribalPattern variant="woven" height={6} color="#1D0A69" opacity={0.9} />

      {/* Mobile Off-Canvas Menu Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#1D0A69] text-white border-b border-[#0F4C81] shadow-xl animate-in slide-in-from-top-2 duration-200">
          <div className="gov-container py-3 space-y-1">
            
            {/* User status banner if authenticated */}
            {isAuthenticated && user && (
              <div className="p-2.5 mb-2 bg-[#15074D] rounded border border-[#546E7A] flex items-center justify-between text-xs">
                <div>
                  <div className="font-bold text-[#FFC107]">
                    {user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user.username}
                  </div>
                  <div className="text-[10px] text-[#B0BEC5] font-mono">
                    {user.email || user.username} • {role}
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="bg-[#D32F2F] hover:bg-[#B71C1C] text-white text-[11px] font-bold px-2 py-1 rounded flex items-center gap-1"
                >
                  <LogOut className="w-3 h-3" />
                  <span>Logout</span>
                </button>
              </div>
            )}

            {/* Public Links */}
            <Link
              to="/"
              onClick={closeMenu}
              className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                location.pathname === '/' ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
              }`}
            >
              <Home className="w-4 h-4" />
              <span>{language === 'hi' ? 'मुख्य पृष्ठ' : 'Portal Home'}</span>
            </Link>

            <Link
              to="/schemes"
              onClick={closeMenu}
              className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                location.pathname.startsWith('/schemes') ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
              }`}
            >
              <Compass className="w-4 h-4" />
              <span>{language === 'hi' ? 'सभी 5 योजनाएं' : 'All 5 Statutory Schemes'}</span>
            </Link>

            {/* Student Authenticated Links */}
            {authState === 'AUTHENTICATED_APPLICANT' && (
              <>
                <Link
                  to="/dashboard"
                  onClick={closeMenu}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                    location.pathname === '/dashboard' ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
                  }`}
                >
                  <FileSpreadsheet className="w-4 h-4" />
                  <span>{language === 'hi' ? 'आवेदक डैशबोर्ड' : 'My Dashboard & Dossier'}</span>
                </Link>

                <Link
                  to="/documents"
                  onClick={closeMenu}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                    location.pathname === '/documents' ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
                  }`}
                >
                  <FolderLock className="w-4 h-4 text-[#FFC107]" />
                  <span>{language === 'hi' ? 'दस्तावेज़ वॉल्ट' : 'Document Vault & OCR'}</span>
                </Link>

                <Link
                  to="/profile"
                  onClick={closeMenu}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                    location.pathname === '/profile' ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
                  }`}
                >
                  <User className="w-4 h-4" />
                  <span>{language === 'hi' ? 'मेरी प्रोफाइल' : 'My Profile & Details'}</span>
                </Link>
              </>
            )}

            {/* Officer Authenticated Links */}
            {authState === 'AUTHENTICATED_OFFICER' && (
              <>
                <Link
                  to="/officer"
                  onClick={closeMenu}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                    location.pathname === '/officer' ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
                  }`}
                >
                  <ShieldCheck className="w-4 h-4 text-[#FFC107]" />
                  <span>{language === 'hi' ? 'जांच कार्यक्षेत्र' : 'Officer Scrutiny Queue'}</span>
                </Link>

                <Link
                  to="/officer/verification/APP-2026-001DB3"
                  onClick={closeMenu}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                    location.pathname.includes('/verification') ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
                  }`}
                >
                  <Shield className="w-4 h-4 text-[#FFC107]" />
                  <span>{language === 'hi' ? 'सत्यापन कार्यपीठ' : 'Verification Workbench'}</span>
                </Link>
              </>
            )}

            {/* Common Public Support Links */}
            <Link
              to="/grievance"
              onClick={closeMenu}
              className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                location.pathname === '/grievance' ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
              }`}
            >
              <MessageSquareWarning className="w-4 h-4" />
              <span>{language === 'hi' ? 'शिकायत निवारण (CPGRAMS)' : 'CPGRAMS Grievance'}</span>
            </Link>

            <Link
              to="/help"
              onClick={closeMenu}
              className={`flex items-center gap-2.5 px-3 py-2 rounded text-xs font-bold ${
                location.pathname === '/help' ? 'bg-[#FFC107] text-[#120538]' : 'text-white hover:bg-[#15074D]'
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span>{language === 'hi' ? 'सहायता एवं दिशानिर्देश' : 'Help & Guidelines'}</span>
            </Link>

            {/* Unauthenticated Login/Register inside Drawer */}
            {!isAuthenticated && (
              <div className="pt-2 border-t border-[#546E7A] flex items-center gap-2">
                <Link
                  to="/login"
                  onClick={closeMenu}
                  className="flex-1 text-center py-2 rounded text-xs font-bold bg-[#FFC107] text-[#120538] hover:bg-[#FFD54F]"
                >
                  Citizen Login
                </Link>
                <Link
                  to="/register"
                  onClick={closeMenu}
                  className="flex-1 text-center py-2 rounded text-xs font-bold border border-[#FFC107] text-[#FFC107] hover:bg-[#15074D]"
                >
                  OTR Register
                </Link>
              </div>
            )}

          </div>
        </div>
      )}
    </header>
  );
};
