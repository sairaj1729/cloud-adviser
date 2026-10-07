// Centralized endpoints for the existing services. The V1 interface runs on demo data
// until these services are reachable from a deployed environment.
export const API_ENDPOINTS = {
  auth: 'http://localhost:8000',
  AWS: 'http://localhost:5000',
  Azure: 'http://localhost:5001',
  GCP: 'http://localhost:5005',
  unused: 'http://localhost:5002',
} as const;
