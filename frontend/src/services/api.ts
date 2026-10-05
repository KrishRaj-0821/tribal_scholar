/**
 * Central Authoritative API Service for Ministry of Tribal Affairs (MoTA) Portal
 */

export const API_BASE_URL = 
  (import.meta as any).env?.VITE_API_URL || 
  (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? '' 
    : 'https://backend-production-ba69a.up.railway.app');

const TOKEN_KEY = 'mota_auth_token';

export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setStoredToken = (token: string, remember: boolean = true) => {
  try {
    if (remember) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      sessionStorage.setItem(TOKEN_KEY, token);
    }
  } catch (e) {
    console.error('Failed to store token', e);
  }
};

export const clearStoredToken = () => {
  try {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  } catch (e) {
    console.error('Failed to clear token', e);
  }
};

export async function fetchApi<T = any>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') 
    ? endpoint 
    : `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  const token = getStoredToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Set Content-Type only if not FormData
  if (!(options.body instanceof FormData) && !headers['Content-Type'] && options.body) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Support HTTP-only session cookies
  });

  if (response.status === 401) {
    // Session expired or invalid
    clearStoredToken();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth:expired', { detail: { endpoint } }));
    }
    throw new Error('Authentication expired. Please login again.');
  }

  if (response.status === 204) {
    return null as any;
  }

  let data: any;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg = 
      (typeof data === 'object' && (data.error || data.message || data.detail)) || 
      (typeof data === 'string' ? data : `API Error (${response.status})`);
    const err = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    (err as any).status = response.status;
    (err as any).data = data;
    throw err;
  }

  return data as T;
}

// ----------------------------------------------------------------------
// Auth Service
// ----------------------------------------------------------------------
export const authApi = {
  login: async (identifier: string, password: string) => {
    const res = await fetchApi<{ message: string; token: string; user: any }>('/api/v1/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    });
    if (res.token) {
      setStoredToken(res.token);
    }
    return res;
  },

  register: async (payload: {
    username: string;
    email: string;
    password: string;
    phone_number?: string;
    community?: string;
    annual_family_income?: number;
  }) => {
    const res = await fetchApi<{ message: string; token: string; user: any }>('/api/v1/auth/register/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.token) {
      setStoredToken(res.token);
    }
    return res;
  },

  logout: async () => {
    try {
      await fetchApi('/api/v1/auth/logout/', { method: 'POST' });
    } catch {
      // Ignore network errors on logout
    } finally {
      clearStoredToken();
    }
  },

  getMe: async () => {
    return await fetchApi<{ user: any; token?: string }>('/api/v1/auth/me/');
  },

  requestOTP: async (mobile: string, resend: boolean = false) => {
    return await fetchApi<{ message: string; mobile_masked: string }>('/api/v1/auth/request-otp/', {
      method: 'POST',
      body: JSON.stringify({ mobile, resend }),
    });
  },

  verifyOTP: async (mobile: string, otp: string) => {
    const res = await fetchApi<{ message: string; token: string; user: any }>('/api/v1/auth/verify-otp/', {
      method: 'POST',
      body: JSON.stringify({ mobile, otp }),
    });
    if (res.token) {
      setStoredToken(res.token);
    }
    return res;
  },
};

// ----------------------------------------------------------------------
// Applicant Profile Service
// ----------------------------------------------------------------------
export const profileApi = {
  getProfile: async () => {
    return await fetchApi<any>('/api/v1/applicants/profile/');
  },
  updateProfile: async (data: any) => {
    return await fetchApi<any>('/api/v1/applicants/profile/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
};

// ----------------------------------------------------------------------
// Document Vault Service
// ----------------------------------------------------------------------
export interface VaultDocument {
  id: string;
  document_type: string;
  display_type: string;
  category: 'COMMUNITY' | 'FINANCIAL' | 'ACADEMIC' | 'IDENTITY' | 'ADMISSION' | 'OTHER';
  original_filename: string;
  file_size_bytes: number;
  uploaded_at: string;
  lifecycle_status: string;
  security_status: 'PASSED' | 'SCANNING' | 'FAILED';
  ocr_status: 'COMPLETED' | 'PENDING' | 'FAILED';
  verification_status: 'OCR_PROVISIONAL' | 'VERIFIED' | 'REJECTED';
  applications_count: number;
  application_id: string | null;
  extracted_fields: Array<{
    id: string;
    field_code: string;
    field_label: string;
    value: any;
    confidence: number;
    trust_level: string;
    source: string;
  }>;
  download_url: string;
}

export const vaultApi = {
  getDocuments: async (category?: string) => {
    const query = category && category !== 'ALL' ? `?category=${category}` : '';
    return await fetchApi<{
      title: string;
      description: string;
      count: number;
      documents: VaultDocument[];
    }>(`/api/v1/documents/vault/${query}`);
  },

  uploadDocument: async (file: File, documentType: string, extra?: Record<string, string>) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (extra) {
      Object.entries(extra).forEach(([k, v]) => formData.append(k, v));
    }
    return await fetchApi<VaultDocument>('/api/v1/documents/vault/', {
      method: 'POST',
      body: formData,
    });
  },

  getReusableFields: async () => {
    return await fetchApi<Record<string, {
      field_code: string;
      field_label: string;
      value: any;
      display_value: string;
      source: string;
      source_label: string;
      source_type: string;
      source_document_id?: string;
      source_document_name?: string;
      confidence: number;
      trust_level: string;
    }>>('/api/v1/documents/vault/reusable-fields/');
  },

  linkDocument: async (documentId: string, applicationId: string) => {
    return await fetchApi<any>(`/api/v1/documents/vault/${documentId}/link/${applicationId}/`, {
      method: 'POST',
    });
  },
};

// ----------------------------------------------------------------------
// Schemes & Applications Service
// ----------------------------------------------------------------------
export const applicationApi = {
  list: async () => {
    return await fetchApi<any>('/api/v1/applications/');
  },

  get: async (id: string) => {
    return await fetchApi<any>(`/api/v1/applications/${id}/`);
  },

  create: async (data: { scheme_code?: string; scheme_version?: string }) => {
    return await fetchApi<any>('/api/v1/applications/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getForm: async (applicationId: string) => {
    return await fetchApi<any>(`/api/v1/applications/${applicationId}/form/`);
  },

  saveForm: async (applicationId: string, answers: Record<string, any>, expectedRevision?: number) => {
    const body: any = { answers };
    if (expectedRevision !== undefined) {
      body.expected_revision_number = expectedRevision;
    }
    return await fetchApi<any>(`/api/v1/applications/${applicationId}/form/`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  },

  submit: async (applicationId: string, idempotencyKey: string) => {
    return await fetchApi<any>(`/api/v1/applications/${applicationId}/submit/`, {
      method: 'POST',
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
      body: JSON.stringify({ idempotency_key: idempotencyKey }),
    });
  },

  getSnapshot: async (applicationId: string) => {
    return await fetchApi<any>(`/api/v1/applications/${applicationId}/submission-snapshot/`);
  },

  uploadDocument: async (applicationId: string, file: File, documentType: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    return await fetchApi<any>(`/api/v1/applications/${applicationId}/documents/?sync=true`, {
      method: 'POST',
      body: formData,
    });
  },
};

// ----------------------------------------------------------------------
// Schemes Master Service
// ----------------------------------------------------------------------
export const schemesApi = {
  list: async (search?: string) => {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return await fetchApi<any>(`/api/v1/schemes/${query}`);
  },

  get: async (id: string) => {
    return await fetchApi<any>(`/api/v1/schemes/${id}/`);
  },

  getForm: async (schemeVersionId: string) => {
    return await fetchApi<any>(`/api/v1/schemes/${schemeVersionId}/application-form/`);
  },
};

// ----------------------------------------------------------------------
// Officer Verification Service
// ----------------------------------------------------------------------
export const officerApi = {
  getQueue: async (params?: Record<string, string>) => {
    const query = params ? `?${new URLSearchParams(params).toString()}` : '';
    return await fetchApi<any>(`/api/v1/verification/queue/${query}`);
  },

  getQueueItem: async (id: string) => {
    return await fetchApi<any>(`/api/v1/verification/queue/${id}/`);
  },

  resolveConflict: async (queueItemId: string, decision: string, reason?: string) => {
    return await fetchApi<any>(`/api/v1/verification/conflicts/${queueItemId}/resolve/`, {
      method: 'POST',
      body: JSON.stringify({ decision, reason: reason || 'Resolved following officer scrutiny.' }),
    });
  },

  verifyDocument: async (documentId: string, payload: {
    decision_action: string;
    reason_code?: string;
    notes?: string;
    override_data?: any;
  }) => {
    return await fetchApi<any>(`/api/v1/verification/documents/${documentId}/verify-document/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  resetDemo: async () => {
    return await fetchApi<any>('/api/v1/verification/demo/reset/', {
      method: 'POST',
    });
  },

  getDemoStatus: async () => {
    return await fetchApi<any>('/api/v1/verification/demo/status/');
  },
};

// ----------------------------------------------------------------------
// Notification & SMS Ledger Service
// ----------------------------------------------------------------------
export interface SMSNotificationRecord {
  id: string;
  notification_type: string;
  recipient_phone_masked: string;
  status: 'PENDING' | 'SENDING' | 'SENT_TO_PROVIDER' | 'DELIVERED' | 'FAILED' | 'RETRY_PENDING' | 'DEV_SKIPPED';
  provider: string;
  provider_request_id?: string;
  message_length: number;
  failure_reason?: string;
  created_at: string;
  sent_at?: string;
  delivered_at?: string;
  dlr_status?: string;
}


export const notificationsApi = {
  getApplicationSMS: async (applicationId: string) => {
    return await fetchApi<SMSNotificationRecord[]>(`/api/v1/applications/${applicationId}/notifications/`);
  },
  retrySMS: async (notificationId: string) => {
    return await fetchApi<SMSNotificationRecord>(`/api/v1/notifications/${notificationId}/retry/`, {
      method: 'POST',
    });
  },
};


