// Centralized API configuration and client for Cloud Advisor FastAPI V1 Backend
export const API_BASE_URL = 
  (typeof window !== 'undefined' && (window as any).__CLOUDADVISOR_API_URL__) ||
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_URL) ||
  'http://localhost:8000/api';

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
  region?: string | undefined;
  credential_type: string;
  role_arn?: string | undefined;
  external_id?: string | undefined;
  azure_tenant_id?: string | undefined;
  azure_client_id?: string | undefined;
  azure_client_secret?: string | undefined;
  gcp_project_id?: string | undefined;
  gcp_service_account_key?: string | undefined;
  gcp_billing_table?: string | undefined;
}) {
  return request<any>('/accounts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export type AwsInitiateResponse = {
  connection_id?: string | undefined;
  external_id: string;
  platform_aws_account_id: string;
  platform_role_arn: string;
  trust_policy: Record<string, any>;
  recommended_permissions: string[];
};

export type AwsVerifyPayload = {
  connection_id?: string | undefined;
  display_name: string;
  account_id: string;
  role_arn: string;
  external_id: string;
  region: string;
};

export async function apiInitiateAwsConnection() {
  return request<AwsInitiateResponse>('/accounts/aws/initiate', { method: 'POST' });
}

export async function apiVerifyAwsConnection(payload: AwsVerifyPayload) {
  return request<{
    status: string;
    verified: boolean;
    account: any;
    session_info?: any;
    message: string;
  }>('/accounts/aws/verify', {
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
export type DatasetMeta = {
  id: string;
  name: string;
  domain: string;
  description: string;
  file: string;
  item_count: number;
  icon: string;
  is_active: boolean;
  loaded_resources: number;
  generated_findings: number;
};

export async function apiListDatasets() {
  return request<DatasetMeta[]>('/dashboard/datasets');
}

export async function apiSwitchDataset(datasetId: string) {
  return request<any>('/dashboard/datasets/switch', {
    method: 'POST',
    body: JSON.stringify({ dataset_id: datasetId }),
  });
}

export async function apiGetDashboardSummary(datasetId?: string) {
  const query = datasetId ? `?dataset=${encodeURIComponent(datasetId)}` : '';
  return request<{
    active_dataset_id?: string;
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
  }>(`/dashboard/summary${query}`);
}

export async function apiGetDashboardAnalytics(refresh: boolean = true, datasetId?: string) {
  const params = new URLSearchParams();
  params.append('refresh', String(refresh));
  if (datasetId) params.append('dataset', datasetId);
  return request<any>(`/dashboard/analytics?${params.toString()}`);
}

export async function apiRefreshDashboardAnalytics(datasetId?: string) {
  const query = datasetId ? `?dataset=${encodeURIComponent(datasetId)}` : '';
  return request<any>(`/dashboard/refresh${query}`, { method: 'POST' });
}

export async function apiGenerateFindings() {
  return request<any>('/findings/generate', { method: 'POST' });
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

// AI Recommendations API Methods
export type AIRecommendationData = {
  resource_id: string;
  resource_name?: string;
  provider: string;
  action: 'RIGHTSIZE' | 'STOP' | 'TERMINATE' | 'STORAGE_DOWNGRADE' | 'NO_ACTION' | string;
  target_sku?: string | null;
  current_sku?: string | null;
  current_monthly_cost: number;
  estimated_monthly_savings: number;
  estimated_savings_percentage: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  justification: string;
  remediation_steps: string[];
  remediation_command?: string | null;
  llm_provider_used: string;
  llm_model_used: string;
  status: 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'EXECUTED' | string;
  created_at: string;
};

export type AIBatchResult = {
  total_findings_analyzed: number;
  recommendations_generated: number;
  total_estimated_monthly_savings: number;
  items: AIRecommendationData[];
};

export async function apiGetAIRecommendation(resourceId: string, findingId?: string, provider?: string): Promise<AIRecommendationData> {
  const params = new URLSearchParams();
  if (findingId) params.append('finding_id', findingId);
  if (provider) params.append('provider', provider);
  const query = params.toString() ? `?${params.toString()}` : '';
  return request<AIRecommendationData>(`/ai/recommend/${encodeURIComponent(resourceId)}${query}`, {
    method: 'POST'
  });
}

export async function apiBatchGenerateAIRecommendations(
  limit: number = 15,
  cloudProvider?: string,
  datasetId?: string,
  forceRefresh: boolean = false,
  llmProvider?: string
): Promise<AIBatchResult> {
  const params = new URLSearchParams();
  params.append('limit', String(limit));
  if (cloudProvider && cloudProvider !== 'All') params.append('cloud_provider', cloudProvider.toLowerCase());
  if (datasetId) params.append('dataset_id', datasetId);
  if (forceRefresh) params.append('force_refresh', 'true');
  if (llmProvider) params.append('provider', llmProvider);
  return request<AIBatchResult>(`/ai/batch-generate?${params.toString()}`, {
    method: 'POST'
  });
}

export async function apiListAIRecommendations(limit: number = 50): Promise<AIRecommendationData[]> {
  return request<AIRecommendationData[]>(`/ai/recommendations?limit=${limit}`);
}

export async function apiUpdateAIRecommendationStatus(resourceId: string, newStatus: string) {
  return request<any>(`/ai/recommendations/${encodeURIComponent(resourceId)}/status?new_status=${encodeURIComponent(newStatus)}`, {
    method: 'PATCH'
  });
}


