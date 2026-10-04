import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Home, Compass, FileSpreadsheet, FolderLock, 
  User, ShieldCheck, Shield, HelpCircle, LogIn, UserPlus
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { useAuth } from '../../context/AuthContext';
import { TribalPattern } from './TribalPattern';

export const MobileBottomNav: React.FC = () => {
  const { language } = useLanguage();
  const { authState, isAuthenticated } = useAuth();

  // Role-bound mobile bottom navigation tabs
  const getNavItems = () => {
    if (!isAuthenticated || authState === 'PUBLIC') {
      return [
        { to: '/', labelEn: 'Home', labelHi: 'मुख्य', icon: Home, end: true },
        { to: '/schemes', labelEn: 'Schemes', labelHi: 'योजनाएं', icon: Compass, end: false },
        { to: '/login', labelEn: 'Login', labelHi: 'प्रवेश', icon: LogIn, end: true, highlight: true },
        { to: '/register', labelEn: 'Register', labelHi: 'पंजीकरण', icon: UserPlus, end: true },
        { to: '/help', labelEn: 'Help', labelHi: 'सहायता', icon: HelpCircle, end: false },
      ];
    }

    if (authState === 'AUTHENTICATED_OFFICER') {
      return [
        { to: '/officer', labelEn: 'Queue', labelHi: 'कतार', icon: ShieldCheck, end: true },
        { to: '/officer/verification/APP-2026-001DB3', labelEn: 'Workbench', labelHi: 'कार्यपीठ', icon: Shield, end: false },
        { to: '/officer/audit', labelEn: 'Audit', labelHi: 'ऑडिट', icon: FileSpreadsheet, end: false },
        { to: '/profile', labelEn: 'Profile', labelHi: 'प्रोफ़ाइल', icon: User, end: true },
      ];
    }

    // Default to AUTHENTICATED_APPLICANT
    return [
      { to: '/', labelEn: 'Home', labelHi: 'मुख्य', icon: Home, end: true },
      { to: '/schemes', labelEn: 'Schemes', labelHi: 'योजनाएं', icon: Compass, end: false },
      { to: '/dashboard', labelEn: 'Dossier', labelHi: 'डैशबोर्ड', icon: FileSpreadsheet, end: false },
      { to: '/documents', labelEn: 'Vault', labelHi: 'वॉल्ट', icon: FolderLock, end: false },
      { to: '/profile', labelEn: 'Profile', labelHi: 'प्रोफ़ाइल', icon: User, end: true },
    ];
  };

  const navItems = getNavItems();
  const gridColsClass = navItems.length === 4 ? 'grid-cols-4' : 'grid-cols-5';

  return (
    <nav 
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#FFFFFF] border-t border-[#CFD8DC] shadow-[0_-4px_16px_rgba(29,10,105,0.08)] select-none"
      style={{ paddingBottom: 'max(0.35rem, env(safe-area-inset-bottom))' }}
      role="navigation"
      aria-label="Mobile Navigation Bar"
    >
      {/* Top Tribal Pattern Line Micro Ribbon */}
      <TribalPattern variant="woven" height={3} color="#1D0A69" opacity={0.8} />

      <div className={`grid ${gridColsClass} h-14 items-center`}>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center py-1 transition-all relative ${
                  isActive 
                    ? 'text-[#1D0A69] font-bold' 
                    : item.highlight
                    ? 'text-[#C85A17] font-semibold hover:text-[#1D0A69]'
                    : 'text-[#546E7A] hover:text-[#1D0A69]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div className="relative">
                    <Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${isActive ? 'stroke-[2.5]' : 'stroke-2'}`} />
                    {isActive && (
                      <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-[#FFC107] ring-1 ring-white" />
                    )}
                  </div>
                  <span className={`text-[10px] leading-tight mt-0.5 tracking-tight ${isActive ? 'font-bold text-[#1D0A69]' : ''}`}>
                    {language === 'hi' ? item.labelHi : item.labelEn}
                  </span>
                </>
              )}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
};
