import React from 'react';
import { Home, Compass, FileSpreadsheet, MessageSquareWarning, ShieldCheck } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from './TribalPattern';

interface MobileBottomNavProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({
  activeTab,
  onSelectTab
}) => {
  const { language } = useLanguage();

  const navItems = [
    { id: 'home', labelEn: 'Home', labelHi: 'मुख्य', icon: <Home className="w-5 h-5" /> },
    { id: 'schemes', labelEn: 'Schemes', labelHi: 'योजनाएं', icon: <Compass className="w-5 h-5" /> },
    { id: 'dashboard', labelEn: 'Dossier', labelHi: 'डॉसियर', icon: <FileSpreadsheet className="w-5 h-5" /> },
    { id: 'grievance', labelEn: 'Grievance', labelHi: 'शिकायत', icon: <MessageSquareWarning className="w-5 h-5" /> },
    { id: 'officer', labelEn: 'Officer', labelHi: 'अधिकारी', icon: <ShieldCheck className="w-5 h-5" /> }
  ];

  return (
    <nav 
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#FFFFFF] border-t border-[#CFD8DC] shadow-[0_-4px_16px_rgba(29,10,105,0.08)] select-none"
      style={{ paddingBottom: 'max(0.35rem, env(safe-area-inset-bottom))' }}
      role="navigation"
      aria-label="Mobile Sovereign Navigation"
    >
      {/* Top Tribal Pattern Line Micro Ribbon */}
      <TribalPattern variant="woven" height={4} color="#1D0A69" opacity={0.7} />

      <div className="grid grid-cols-5 h-14 items-center">
        {navItems.map((item) => {
          const isActive = activeTab === item.id || 
            (item.id === 'schemes' && activeTab === 'scheme_detail') ||
            (item.id === 'dashboard' && (activeTab === 'wizard' || activeTab === 'deficiency')) ||
            (item.id === 'officer' && activeTab === 'workbench');

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`flex flex-col items-center justify-center py-1 transition-all relative ${
                isActive 
                  ? 'text-[#1D0A69] font-bold' 
                  : 'text-[#546E7A] hover:text-[#1D0A69]'
              }`}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative">
                {item.icon}
                {isActive && (
                  <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-[#FFC107] ring-1 ring-white" />
                )}
              </div>
              <span className="text-[10px] leading-tight mt-0.5 tracking-tight">
                {language === 'hi' ? item.labelHi : item.labelEn}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
