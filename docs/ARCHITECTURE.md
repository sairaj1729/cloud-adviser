# System Architecture Specification - Cloud Advisor V1

This document describes the V1 Modular Monolith architecture of Cloud Advisor.

---

## 1. High-Level Flow

```text
React Frontend (TanStack Start / Vite)
       │
       │ REST API (JWT Authenticated)
       ▼
FastAPI Backend (Modular Monolith)
       │
       ├── 1. Authentication (JWT, bcrypt/Argon2)
       ├── 2. Account Connection Manager (AWS STS AssumeRole, Azure Entra, GCP Workload Identity)
       ├── 3. Provider Connectors (Boto3, Azure SDK, GCP SDK)
       ├── 4. Normalization Layer (Common Resource Model)
       ├── 5. MongoDB Persistence (Motor Async Driver)
       └── 6. Rule Engine & Evidence Generator (Data-driven Rule Registry)
```

---

## 2. Component Layering

### Presentation Layer
React 19 + TanStack Start SPA sending authenticated REST HTTP requests to FastAPI endpoints.

### Application Layer (`backend/app/`)
- **API Controllers**: FastAPI APIRouter handlers for Auth, Accounts, Resources, Rules, Findings, and Dashboard.
- **Service Layer**: Ingestion orchestration (`scan_service.py`), Account verification (`account_service.py`), and Auth (`auth_service.py`).
- **Provider Layer**: `CloudProviderConnector` interface implementations isolating AWS, Azure, and GCP SDK calls.
- **Normalization Layer**: Converts raw SDK JSON payloads into provider-agnostic common resource representations.
- **Rule Engine Layer**: Evaluates normalized data against MongoDB data-driven rule definitions without invoking cloud SDKs.

### Persistence Layer
MongoDB database storing:
- `users`: User profiles and hashed credentials.
- `cloud_accounts`: Connection metadata (no plaintext secrets).
- `resources`: Normalized inventory and metric metrics.
- `rules`: Data-driven rule definitions.
- `findings`: Generated findings, evidence payloads, and estimated savings.

---

## 3. Strict Boundary Rules

1. **No External SDK Calls in Rule Engine**: The Rule Engine strictly operates on normalized resource documents stored in MongoDB or passed in memory from the Normalizer.
2. **No Secret Persistence**: IAM credentials, Client Secrets, and Service Account Keys are never logged, returned in API responses, or stored in plaintext.
3. **No Over-Engineering**: Redis, Celery, and Kafka are excluded in V1 in favor of a clean, synchronous/threaded modular monolith.
