import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { AccessibilityProvider } from './context/AccessibilityContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { DemoProvider } from './context/DemoContext';
import { AccessibilityToolbar } from './components/common/AccessibilityToolbar';
import { GovernmentHeader } from './components/common/GovernmentHeader';
import { GovernmentFooter } from './components/common/GovernmentFooter';
import { PortalNavigationBar } from './components/common/PortalNavigationBar';
import { MobileBottomNav } from './components/common/MobileBottomNav';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { PwaOfflineBanner } from './components/common/PwaOfflineBanner';

// Views
import { HomeView } from './components/views/HomeView';
import { SchemeExplorerView } from './components/views/SchemeExplorerView';
import { SchemeDetailView } from './components/views/SchemeDetailView';
import { LoginView } from './components/views/LoginView';
import { RegistrationView } from './components/views/RegistrationView';
import { ApplicantDashboardView } from './components/views/ApplicantDashboardView';
import { ApplicantProfileView } from './components/views/ApplicantProfileView';
import { DocumentVaultView } from './components/views/DocumentVaultView';
import { ApplicationWizardView } from './components/views/ApplicationWizardView';
import { ApplicantStatusView } from './components/views/ApplicantStatusView';
import { DeficiencyResolutionView } from './components/views/DeficiencyResolutionView';
import { GrievanceView } from './components/views/GrievanceView';
import { OfficerDashboardView } from './components/views/OfficerDashboardView';
import { VerificationWorkbenchView } from './components/views/VerificationWorkbenchView';
import { AdminDashboardView } from './components/views/AdminDashboardView';
import { HelpView } from './components/views/HelpView';
import { AboutView } from './components/views/AboutView';

import { SchemeInfo, OFFICIAL_MOTA_SCHEMES } from './theme/tokens';

// Scheme Explorer Wrapper
const SchemeExplorerPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const handleSelectScheme = (scheme: SchemeInfo) => {
    navigate(`/schemes/${scheme.code}`);
  };

  const handleApplyScheme = (scheme: SchemeInfo) => {
    if (!isAuthenticated) {
      navigate(`/login?redirect=/applications/new?scheme=${scheme.code}`);
    } else {
      navigate(`/applications/new?scheme=${scheme.code}`);
    }
  };

  return (
    <SchemeExplorerView
      onSelectScheme={handleSelectScheme}
      onApplyScheme={handleApplyScheme}
    />
  );
};

// Scheme Detail Wrapper
const SchemeDetailPage: React.FC = () => {
  const { schemeId } = useParams<{ schemeId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const scheme = OFFICIAL_MOTA_SCHEMES.find(
    s => s.code.toLowerCase() === schemeId?.toLowerCase() || s.officialCode.toLowerCase() === schemeId?.toLowerCase()
  ) || OFFICIAL_MOTA_SCHEMES[2]; // Default Top Class

  const handleApply = (sch: SchemeInfo) => {
    if (!isAuthenticated) {
      navigate(`/login?redirect=/applications/new?scheme=${sch.code}`);
    } else {
      navigate(`/applications/new?scheme=${sch.code}`);
    }
  };

  return (
    <SchemeDetailView
      scheme={scheme}
      onBack={() => navigate('/schemes')}
      onApply={handleApply}
    />
  );
};

// Application Wizard Wrapper
const ApplicationWizardPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const schemeCode = searchParams.get('scheme');

  const initialScheme = OFFICIAL_MOTA_SCHEMES.find(
    s => s.code.toLowerCase() === schemeCode?.toLowerCase()
  ) || OFFICIAL_MOTA_SCHEMES[2];

  return (
    <ApplicationWizardView
      initialScheme={initialScheme}
      onSubmitted={() => navigate('/dashboard')}
      onCancel={() => navigate('/schemes')}
    />
  );
};

// Verification Workbench Wrapper
const VerificationWorkbenchPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  return (
    <VerificationWorkbenchView
      applicationId={id || 'APP-2026-001DB3'}
      onBackToQueue={() => navigate('/officer')}
    />
  );
};

// Home View Wrapper
const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <HomeView
      onSelectScheme={(scheme) => navigate(`/schemes/${scheme.code}`)}
      onNavigateTab={(tab) => {
        if (tab === 'schemes') navigate('/schemes');
        else if (tab === 'dashboard') navigate('/dashboard');
        else if (tab === 'login') navigate('/login');
        else if (tab === 'grievance') navigate('/grievance');
        else navigate('/');
      }}
    />
  );
};

// App Layout with statutory Government Header, Nav, and Footer
const AppLayout: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col bg-[#F4F6F8]">
      {/* 0. PWA Offline & Install Indicators */}
      <PwaOfflineBanner />

      {/* 1. GIGW 3.0 Accessibility Toolbar */}
      <AccessibilityToolbar />

      {/* 2. Official Ministry of Tribal Affairs Sovereign Header */}
      <GovernmentHeader />

      {/* 3. Authoritative Portal Navigation Bar */}
      <PortalNavigationBar />

      {/* 4. Sovereign Main Routed View Content */}
      <main id="main-content" className="flex-1 pb-16 md:pb-0" role="main">
        <Routes>
          {/* ========================================================
              PUBLIC ROUTES (Requirement 3: Never require auth)
              ======================================================== */}
          <Route path="/" element={<HomePage />} />
          <Route path="/schemes" element={<SchemeExplorerPage />} />
          <Route path="/schemes/:schemeId" element={<SchemeDetailPage />} />
          <Route path="/login" element={<LoginView />} />
          <Route path="/register" element={<RegistrationView />} />
          <Route path="/help" element={<HelpView />} />
          <Route path="/about" element={<AboutView />} />
          <Route path="/grievance" element={<GrievanceView />} />

          {/* ========================================================
              APPLICANT PROTECTED ROUTES (Requirement 4 & 7)
              Unauthenticated -> /login, Officer/Admin -> role dashboard
              ======================================================== */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicantDashboardView 
                  onResolveDeficiency={() => navigate('/deficiency')}
                  onNavigateTab={(t) => navigate(`/${t}`)}
                />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/profile" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicantProfileView />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/documents" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <DocumentVaultView />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/applications" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicantDashboardView 
                  onResolveDeficiency={() => navigate('/deficiency')}
                  onNavigateTab={(t) => navigate(`/${t}`)}
                />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/applications/new" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicationWizardPage />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/applications/:id/form" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicationWizardPage />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/applications/:id" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicantStatusView />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/applications/:id/status" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicantStatusView />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/notifications" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <ApplicantDashboardView />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/grievance/my" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <GrievanceView />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/deficiency" 
            element={
              <ProtectedRoute allowedRoles={['APPLICANT']}>
                <DeficiencyResolutionView 
                  onBack={() => navigate('/dashboard')}
                  onResolved={() => navigate('/dashboard')}
                />
              </ProtectedRoute>
            } 
          />

          {/* ========================================================
              OFFICER PROTECTED ROUTES (Requirement 5 & 7)
              Applicant -> /dashboard, Unauthenticated -> /login
              ======================================================== */}
          <Route 
            path="/officer" 
            element={
              <ProtectedRoute allowedRoles={['SCRUTINY_OFFICER', 'VERIFYING_AUTHORITY', 'SANCTIONING_OFFICER', 'ADMIN']}>
                <OfficerDashboardView 
                  onOpenWorkbench={(appId) => navigate(`/officer/verification/${appId}`)}
                />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/officer/queue" 
            element={
              <ProtectedRoute allowedRoles={['SCRUTINY_OFFICER', 'VERIFYING_AUTHORITY', 'SANCTIONING_OFFICER', 'ADMIN']}>
                <OfficerDashboardView 
                  onOpenWorkbench={(appId) => navigate(`/officer/verification/${appId}`)}
                />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/officer/verification/:id" 
            element={
              <ProtectedRoute allowedRoles={['SCRUTINY_OFFICER', 'VERIFYING_AUTHORITY', 'SANCTIONING_OFFICER', 'ADMIN']}>
                <VerificationWorkbenchPage />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/officer/applications/:id" 
            element={
              <ProtectedRoute allowedRoles={['SCRUTINY_OFFICER', 'VERIFYING_AUTHORITY', 'SANCTIONING_OFFICER', 'ADMIN']}>
                <VerificationWorkbenchPage />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/officer/documents/:id" 
            element={
              <ProtectedRoute allowedRoles={['SCRUTINY_OFFICER', 'VERIFYING_AUTHORITY', 'SANCTIONING_OFFICER', 'ADMIN']}>
                <VerificationWorkbenchPage />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/officer/audit" 
            element={
              <ProtectedRoute allowedRoles={['SCRUTINY_OFFICER', 'VERIFYING_AUTHORITY', 'SANCTIONING_OFFICER', 'ADMIN']}>
                <OfficerDashboardView 
                  onOpenWorkbench={(appId) => navigate(`/officer/verification/${appId}`)}
                />
              </ProtectedRoute>
            } 
          />

          {/* ========================================================
              ADMIN PROTECTED ROUTES (Requirement 6 & 7)
              ======================================================== */}
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <AdminDashboardView />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/admin/*" 
            element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <AdminDashboardView />
              </ProtectedRoute>
            } 
          />

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {/* 5. GIGW 3.0 Statutory Footer */}
      <GovernmentFooter />

      {/* 6. Mobile Role-Aware Sticky Bottom Navigation */}
      <MobileBottomNav />
    </div>
  );
};

export default function App() {
  return (
    <LanguageProvider>
      <AccessibilityProvider>
        <AuthProvider>
          <DemoProvider>
            <BrowserRouter>
              <AppLayout />
            </BrowserRouter>
          </DemoProvider>
        </AuthProvider>
      </AccessibilityProvider>
    </LanguageProvider>
  );
}
