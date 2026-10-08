# API Specification & OpenAPI Documentation - Cloud Advisor V1

This document specifies the RESTful HTTP API provided by the Cloud Advisor FastAPI V1 backend.

---

## 1. Base URL & Authentication

- **Base Path**: `/api`
- **Authentication**: HTTP Bearer JWT Header (`Authorization: Bearer <access_token>`)
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

## 2. Endpoint Index

### Auth Endpoints (`/api/auth`)
- `POST /api/auth/register`: Register user account & hash password.
- `POST /api/auth/login`: Authenticate credentials & return JWT access token.
- `GET /api/auth/me`: Get active user profile.

### Cloud Account Endpoints (`/api/accounts`)
- `GET /api/accounts`: List user's connected cloud accounts.
- `POST /api/accounts`: Connect new AWS, Azure, or GCP account.
- `GET /api/accounts/{id}`: Fetch cloud account connection details.
- `POST /api/accounts/{id}/verify`: Verify credentials & permissions.
- `POST /api/accounts/{id}/scan`: Synchronously trigger resource discovery, normalization & rule evaluation.
- `DELETE /api/accounts/{id}`: Disconnect cloud account.

### Inventory Resource Endpoints (`/api/resources`)
- `GET /api/resources`: List normalized inventory resources with provider & resource_type filters.

### Rule Registry Endpoints (`/api/rules`)
- `GET /api/rules`: List active FinOps rules.
- `GET /api/rules/{rule_id}`: Fetch rule definition by ID.

### Finding & Recommendation Endpoints (`/api/findings`)
- `GET /api/findings`: List findings filterable by provider, severity, status, and resource_type.
- `GET /api/findings/{id}`: Detailed finding view with evidence and savings calculation.

### Dashboard Endpoint (`/api/dashboard`)
- `GET /api/dashboard/summary`: Summary metrics (account count, total resources, open findings, high severity count, monthly & annual estimated savings).
