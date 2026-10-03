import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, clearStoredToken } from '../services/api';

export type UserRole = 
  | 'APPLICANT' 
  | 'SCRUTINY_OFFICER' 
  | 'VERIFYING_AUTHORITY' 
  | 'SANCTIONING_OFFICER' 
  | 'ADMIN';

export type AppAuthState = 
  | 'PUBLIC' 
  | 'AUTHENTICATED_APPLICANT' 
  | 'AUTHENTICATED_OFFICER' 
  | 'AUTHENTICATED_ADMIN';

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  phone_number?: string;
  is_verified?: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  first_name?: string;
  last_name?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  role: UserRole | null;
  authState: AppAuthState;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (identifier: string, password: string) => Promise<{ destination: string; role: UserRole }>;
  loginWithOTP: (mobile: string, otp: string) => Promise<{ destination: string; role: UserRole }>;
  register: (payload: {
    username: string;
    email: string;
    password: string;
    phone_number?: string;
    community?: string;
    annual_family_income?: number;
  }) => Promise<{ destination: string; role: UserRole }>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<AuthUser | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const resolveAuthState = (role?: UserRole | null): AppAuthState => {
    if (!role) return 'PUBLIC';
    if (role === 'APPLICANT') return 'AUTHENTICATED_APPLICANT';
    if (role === 'ADMIN') return 'AUTHENTICATED_ADMIN';
    if (['SCRUTINY_OFFICER', 'VERIFYING_AUTHORITY', 'SANCTIONING_OFFICER'].includes(role)) {
      return 'AUTHENTICATED_OFFICER';
    }
    return 'PUBLIC';
  };

  const getRoleDestination = (role: UserRole): string => {
    if (role === 'APPLICANT') return '/dashboard';
    if (role === 'ADMIN') return '/admin';
    return '/officer';
  };

  // Authoritative session refresh directly against backend
  const refreshSession = useCallback(async (): Promise<AuthUser | null> => {
    try {
      const res = await authApi.getMe();
      if (res && res.user) {
        setUser(res.user as AuthUser);
        return res.user as AuthUser;
      } else {
        setUser(null);
        return null;
      }
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial check on portal boot
  useEffect(() => {
    refreshSession();

    // Listen for session expiration events from API layer
    const handleAuthExpired = () => {
      setUser(null);
      clearStoredToken();
    };

    window.addEventListener('auth:expired', handleAuthExpired);
    return () => {
      window.removeEventListener('auth:expired', handleAuthExpired);
    };
  }, [refreshSession]);

  const login = async (identifier: string, password: string) => {
    setError(null);
    try {
      const res = await authApi.login(identifier, password);
      const authUser = res.user as AuthUser;
      setUser(authUser);
      const destination = getRoleDestination(authUser.role);
      return { destination, role: authUser.role };
    } catch (err: any) {
      const msg = err.message || 'Login failed. Please check your credentials.';
      setError(msg);
      throw err;
    }
  };

  const loginWithOTP = async (mobile: string, otp: string) => {

    setError(null);
    try {
      const res = await authApi.verifyOTP(mobile, otp);
      const authUser = res.user as AuthUser;
      setUser(authUser);
      const destination = getRoleDestination(authUser.role);
      return { destination, role: authUser.role };
    } catch (err: any) {
      const msg = err.message || 'OTP verification failed. Please check the code and try again.';
      setError(msg);
      throw err;
    }
  };

  const register = async (payload: {
    username: string;
    email: string;
    password: string;
    phone_number?: string;
    community?: string;
    annual_family_income?: number;
  }) => {
    setError(null);
    try {
      const res = await authApi.register(payload);
      const authUser = res.user as AuthUser;
      setUser(authUser);
      const destination = getRoleDestination(authUser.role);
      return { destination, role: authUser.role };
    } catch (err: any) {
      const msg = err.message || 'Registration failed. Please check the provided information.';
      setError(msg);
      throw err;
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setError(null);
      setLoading(false);
    }
  };

  const role = user?.role || null;
  const authState = resolveAuthState(role);
  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        authState,
        isAuthenticated,
        loading,
        error,
        login,
        loginWithOTP,
        register,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );

};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
