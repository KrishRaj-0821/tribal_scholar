import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth, UserRole } from '../../context/AuthContext';
import { RefreshCw } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactElement;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  allowedRoles 
}) => {
  const { isAuthenticated, user, role, loading } = useAuth();
  const location = useLocation();

  // 1. Mandatory Sovereign Auth Resolution State: Never render private content prematurely
  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-white p-8 rounded-xl shadow-lg border border-[#CFD8DC] max-w-md w-full flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-[#1D0A69]/10 flex items-center justify-center animate-spin text-[#1D0A69]">
            <RefreshCw className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[#1D0A69]">Verifying Sovereign Credentials</h2>
            <p className="text-xs text-[#546E7A] mt-1">
              Establishing authenticated session with Ministry of Tribal Affairs digital gateway...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 2. Unauthenticated Boundary: Redirect to /login with redirect context
  if (!isAuthenticated || !user || !role) {
    const redirectUrl = location.pathname !== '/login' && location.pathname !== '/'
      ? `/login?redirect=${encodeURIComponent(location.pathname + location.search)}`
      : '/login';
    return <Navigate to={redirectUrl} replace />;
  }

  // 3. Strict Role Boundary Protection
  if (allowedRoles && allowedRoles.length > 0) {
    if (!allowedRoles.includes(role)) {
      // Role mismatch redirection
      if (role === 'APPLICANT') {
        return <Navigate to="/dashboard" replace />;
      }
      if (role === 'ADMIN') {
        return <Navigate to="/admin" replace />;
      }
      // Officers
      return <Navigate to="/officer" replace />;
    }
  }

  return children;
};
