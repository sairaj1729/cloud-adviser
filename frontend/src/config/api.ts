// Centralized API configuration and client for Cloud Advisor FastAPI V1 Backend
export const API_BASE_URL = 'http://localhost:8000/api';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('cloud-advisor-token');
}

export function setStoredToken(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) {
    localStorage.setItem('cloud-advisor-token', token);
  } else {
    localStorage.removeItem('cloud-advisor-token');
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

// Auth API Methods
export async function apiLogin(username: string, password: string) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Invalid credentials' }));
    throw new Error(errorData.detail || 'Login failed');
  }

  const data = await response.json();
  setStoredToken(data.access_token);
  return data;
}

export async function apiRegister(email: string, password: string, name: string) {
  const data = await request<{ access_token: string; user: any }>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  });
  setStoredToken(data.access_token);
  return data;
}

export async function apiGetMe() {
  return request<any>('/auth/me');
}

// Accounts API Methods
export async function apiListAccounts() {
  return request<any[]>('/accounts');
}

export function apiLogout() {
  setStoredToken(null);
}

export async function apiCreateAccount(payload: {
  provider: string;
  display_name: string;
  account_identifier: string;
  region?: string;
  credential_type: string;
  role_arn?: string;
  external_id?: string;
  azure_tenant_id?: string;
  azure_client_id?: string;
  azure_client_secret?: string;
  gcp_project_id?: string;
}) {
  return request<any>('/accounts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function apiVerifyAccount(accountId: string) {
  return request<any>(`/accounts/${accountId}/verify`, { method: 'POST' });
}

export async function apiScanAccount(accountId: string) {
  return request<{
    status: string;
    resources_scanned: number;
    rules_evaluated: number;
    findings_created: number;
    estimated_monthly_savings: number;
  }>(`/accounts/${accountId}/scan`, { method: 'POST' });
}

export async function apiDeleteAccount(accountId: string) {
  return request<void>(`/accounts/${accountId}`, { method: 'DELETE' });
}

// Dashboard & Analytics API Methods
export async function apiGetDashboardSummary() {
  return request<{
    total_cloud_accounts: number;
    total_resources: number;
    total_findings: number;
    open_findings: number;
    high_severity_findings: number;
    total_monthly_cost: number;
    estimated_monthly_savings: number;
    estimated_annual_savings: number;
    savings_by_provider: { aws: number; azure: number; gcp: number };
    cost_by_provider: { aws: number; azure: number; gcp: number };
    top_services: Array<{ name: string; cost: number; count: number }>;
  }>('/dashboard/summary');
}

export async function apiGetDashboardAnalytics() {
  return request<any>('/dashboard/analytics');
}

export async function apiGetResources(provider?: string) {
  const query = provider ? `?provider=${provider.toLowerCase()}` : '';
  return request<any[]>(`/resources${query}`);
}

export async function apiGetFindings(provider?: string, severity?: string) {
  const params = new URLSearchParams();
  if (provider) params.append('provider', provider.toLowerCase());
  if (severity) params.append('severity', severity);
  const query = params.toString() ? `?${params.toString()}` : '';
  return request<any[]>(`/findings${query}`);
}

export async function apiUpdateFindingStatus(findingId: string, status: string, notes?: string) {
  return request<any>(`/findings/${findingId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status, notes })
  });
}

