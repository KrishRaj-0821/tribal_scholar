import React, { useState } from 'react';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { AccessibilityProvider } from './context/AccessibilityContext';
import { AccessibilityToolbar } from './components/common/AccessibilityToolbar';
import { GovernmentHeader } from './components/common/GovernmentHeader';
import { GovernmentFooter } from './components/common/GovernmentFooter';
import { MobileBottomNav } from './components/common/MobileBottomNav';
import { HomeView } from './components/views/HomeView';
import { SchemeExplorerView } from './components/views/SchemeExplorerView';
import { SchemeDetailView } from './components/views/SchemeDetailView';
import { LoginView } from './components/views/LoginView';
import { RegistrationView } from './components/views/RegistrationView';
import { ApplicantDashboardView } from './components/views/ApplicantDashboardView';
import { ApplicationWizardView } from './components/views/ApplicationWizardView';
import { DeficiencyResolutionView } from './components/views/DeficiencyResolutionView';
import { GrievanceView } from './components/views/GrievanceView';
import { OfficerDashboardView } from './components/views/OfficerDashboardView';
import { VerificationWorkbenchView } from './components/views/VerificationWorkbenchView';
import { AdminDashboardView } from './components/views/AdminDashboardView';
import { PwaOfflineBanner } from './components/common/PwaOfflineBanner';
import { SchemeInfo, OFFICIAL_MOTA_SCHEMES } from './theme/tokens';
import { 
  Home, Compass, FileSpreadsheet, ShieldCheck, 
  Settings, MessageSquareWarning, LogIn 
} from 'lucide-react';

export type PortalTab = 
  | 'home' 
  | 'schemes' 
  | 'scheme_detail' 
  | 'login' 
  | 'register' 
  | 'dashboard' 
  | 'wizard' 
  | 'deficiency' 
  | 'grievance' 
  | 'officer' 
  | 'workbench' 
  | 'admin';

const MainPortalContent: React.FC = () => {
  const { language } = useLanguage();
  const [activeTab, setActiveTab] = useState<PortalTab>('home');
  const [selectedScheme, setSelectedScheme] = useState<SchemeInfo | null>(OFFICIAL_MOTA_SCHEMES[2]); // Default Top Class

  const handleSelectScheme = (scheme: SchemeInfo) => {
    setSelectedScheme(scheme);
    setActiveTab('scheme_detail');
  };

  const handleApplyScheme = (scheme: SchemeInfo) => {
    setSelectedScheme(scheme);
    setActiveTab('wizard');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F4F6F8]">
      {/* 0. PWA Offline & Install Indicators */}
      <PwaOfflineBanner />

      {/* 1. Top GIGW 3.0 Accessibility Toolbar */}
      <AccessibilityToolbar />

      {/* 2. Official Ministry of Tribal Affairs Sovereign Header */}
      <GovernmentHeader />

      {/* 3. Primary Sovereign Navigation Bar (Desktop) */}
      <nav 
        className="hidden md:block bg-[#1D0A69] text-white select-none border-b border-[#0F4C81] sticky top-0 z-40 shadow-sm"
        role="navigation"
        aria-label="Primary Portal Navigation"
      >
        <div className="gov-container flex items-center justify-between">
          <div className="flex items-center gap-1 overflow-x-auto text-xs font-bold">
            <button
              onClick={() => setActiveTab('home')}
              className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition-colors ${
                activeTab === 'home'
                  ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
                  : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
              }`}
            >
              <Home className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'मुख्य पृष्ठ' : 'Home'}</span>
            </button>

            <button
              onClick={() => setActiveTab('schemes')}
              className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition-colors ${
                activeTab === 'schemes' || activeTab === 'scheme_detail'
                  ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
                  : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'योजनाएं (5 Schemes)' : 'All Schemes'}</span>
            </button>

            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition-colors ${
                activeTab === 'dashboard' || activeTab === 'deficiency'
                  ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
                  : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
              }`}
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'आवेदक डैशबोर्ड' : 'Applicant Dashboard'}</span>
              <span className="w-2 h-2 rounded-full bg-[#FFC107]"></span>
            </button>

            <button
              onClick={() => setActiveTab('wizard')}
              className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition-colors ${
                activeTab === 'wizard'
                  ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
                  : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
              }`}
            >
              <span>{language === 'hi' ? 'ऑनलाइन आवेदन (Apply)' : 'Apply Online'}</span>
            </button>

            <button
              onClick={() => setActiveTab('officer')}
              className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition-colors ${
                activeTab === 'officer' || activeTab === 'workbench'
                  ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
                  : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'जांच कार्यक्षेत्र (Officer)' : 'Officer Workbench'}</span>
            </button>

            <button
              onClick={() => setActiveTab('admin')}
              className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition-colors ${
                activeTab === 'admin'
                  ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
                  : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
              }`}
            >
              <Settings className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'केंद्रीय प्रशासन' : 'Central Admin'}</span>
            </button>

            <button
              onClick={() => setActiveTab('grievance')}
              className={`flex items-center gap-1.5 py-3 px-3.5 border-b-2 transition-colors ${
                activeTab === 'grievance'
                  ? 'border-[#FFC107] text-[#FFC107] bg-[#15074D]'
                  : 'border-transparent text-[#FFFFFF] hover:text-[#FFC107] hover:bg-[#15074D]'
              }`}
            >
              <MessageSquareWarning className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'शिकायत निवारण' : 'Grievance / CPGRAMS'}</span>
            </button>
          </div>

          {/* Right Action: Login / OTR */}
          <button
            onClick={() => setActiveTab('login')}
            className={`flex items-center gap-1.5 py-1 px-3 rounded text-xs font-bold border transition-colors ${
              activeTab === 'login' || activeTab === 'register'
                ? 'bg-[#FFC107] text-[#150202] border-[#FFC107]'
                : 'border-[#546E7A] text-white hover:bg-[#15074D]'
            }`}
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>{language === 'hi' ? 'नागरिक प्रवेश' : 'Citizen Login / OTR'}</span>
          </button>
        </div>
      </nav>

      {/* 4. Main Page View Content */}
      <main id="main-content" className="flex-1" role="main">
        {activeTab === 'home' && (
          <HomeView
            onSelectScheme={handleSelectScheme}
            onNavigateTab={(t) => setActiveTab(t as any)}
          />
        )}

        {activeTab === 'schemes' && (
          <SchemeExplorerView
            onSelectScheme={handleSelectScheme}
            onApplyScheme={handleApplyScheme}
          />
        )}

        {activeTab === 'scheme_detail' && selectedScheme && (
          <SchemeDetailView
            scheme={selectedScheme}
            onBack={() => setActiveTab('schemes')}
            onApply={handleApplyScheme}
          />
        )}

        {activeTab === 'login' && (
          <LoginView
            onLoginSuccess={(role) => {
              if (role === 'applicant') {
                setActiveTab('dashboard');
              } else {
                setActiveTab('officer');
              }
            }}
            onNavigateRegister={() => setActiveTab('register')}
          />
        )}

        {activeTab === 'register' && (
          <RegistrationView
            onBackToLogin={() => setActiveTab('login')}
            onRegistered={() => setActiveTab('dashboard')}
          />
        )}

        {activeTab === 'dashboard' && (
          <ApplicantDashboardView
            onResolveDeficiency={() => setActiveTab('deficiency')}
            onNavigateTab={(t) => setActiveTab(t as any)}
          />
        )}

        {activeTab === 'wizard' && (
          <ApplicationWizardView
            initialScheme={selectedScheme}
            onSubmitted={() => setActiveTab('dashboard')}
            onCancel={() => setActiveTab('home')}
          />
        )}

        {activeTab === 'deficiency' && (
          <DeficiencyResolutionView
            onBack={() => setActiveTab('dashboard')}
            onResolved={() => setActiveTab('dashboard')}
          />
        )}

        {activeTab === 'grievance' && (
          <GrievanceView />
        )}

        {activeTab === 'officer' && (
          <OfficerDashboardView
            onOpenWorkbench={() => setActiveTab('workbench')}
          />
        )}

        {activeTab === 'workbench' && (
          <VerificationWorkbenchView
            applicationId="MOTA/2026/TC/09841"
            onBackToQueue={() => setActiveTab('officer')}
          />
        )}

        {activeTab === 'admin' && (
          <AdminDashboardView />
        )}
      </main>

      {/* 5. GIGW 3.0 Statutory Footer */}
      <GovernmentFooter />

      {/* 6. PWA Mobile Bottom Navigation */}
      <MobileBottomNav
        activeTab={activeTab}
        onSelectTab={(t) => setActiveTab(t as any)}
      />
    </div>
  );
};

export default function App() {
  return (
    <LanguageProvider>
      <AccessibilityProvider>
        <MainPortalContent />
      </AccessibilityProvider>
    </LanguageProvider>
  );
}
