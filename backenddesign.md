# FastAPI + MongoDB V1 Backend Architecture Specification - Cloud Advisor

This document outlines the **V1 Modular Monolith Backend Architecture** for **Cloud Advisor**, a multi-cloud FinOps cost optimization and intelligence platform. 

The V1 backend is designed using **FastAPI**, **Python 3.12+**, **MongoDB (Motor)**, and official Cloud SDKs (**boto3**, **Azure SDK**, **Google Cloud client libraries**). It strictly enforces a **Provider Connector $\to$ Normalized Data $\to$ Rule Engine** pipeline without premature over-engineering (no Redis, Celery, Kafka, or microservices).

---

## 1. High-Level System Architecture

```text
React Frontend (TanStack Start / Vite)
       │
       │ REST API (JSON / JWT)
       ▼
FastAPI Backend (Modular Monolith)
       │
       ├── Auth Engine (JWT, Passlib/Argon2)
       ├── Cloud Account Manager (IAM Role, Azure Credentials, GCP Identity)
       │
       ▼
Provider Connectors (AWS | Azure | GCP)
       │
       ▼
Data Normalization Pipeline (Common Resource Model)
       │
       ▼
MongoDB Database (users, cloud_accounts, resources, metrics, rules, findings)
       │
       ▼
Rule Engine (Data-driven condition evaluator & operators)
       │
       ▼
Findings & Recommendations (Evidence & Savings Calculation)
```

---

## 2. Core Architectural Principles

1. **Provider Isolation**: The **Rule Engine NEVER directly calls AWS, Azure, or GCP SDK APIs**. All provider SDK interactions are encapsulated inside Provider Connectors (`app/providers/`).
2. **Normalized Data Representation**: Provider-specific API responses are transformed by the Normalization Layer (`app/normalization/`) into a common schema before DB storage or Rule Engine evaluation.
3. **Data-Driven Rule Registry**: Rules are defined as data-driven schemas in MongoDB (`rules` collection) containing explicit conditions, lookback windows, severity, evidence generators, and savings calculation algorithms.
4. **Modular Monolith**: Simple, clean execution model suitable for synchronous or background-thread execution without external broker dependencies (Redis/Celery deferred to V2).

---

## 3. Directory Structure Map (`backend/`)

```text
backend/
├── app/
│   ├── main.py                          # FastAPI Application Entrypoint & Middleware
│   ├── api/                             # API Routers
│   │   ├── auth.py                      # Auth Endpoints (/api/auth/*)
│   │   ├── accounts.py                  # Cloud Account Management (/api/accounts/*)
│   │   ├── resources.py                 # Normalized Resource Queries (/api/resources/*)
│   │   ├── rules.py                     # Rule Registry Management (/api/rules/*)
│   │   ├── findings.py                  # Cost Findings & Review (/api/findings/*)
│   │   └── dashboard.py                 # Executive FinOps Overview (/api/dashboard/*)
│   ├── core/                            # System Core Config & Security
│   │   ├── config.py                    # Pydantic Settings & Environment Variables
│   │   ├── security.py                  # JWT Auth & Password Hashing
│   │   └── dependencies.py              # FastAPI Request Dependencies
│   ├── db/
│   │   └── mongodb.py                   # Motor Async MongoDB Connection Manager
│   ├── models/                          # Pydantic DB Schemas / Documents
│   │   ├── user.py                      # User Account Document
│   │   ├── cloud_account.py             # Cloud Account Connection Document
│   │   ├── resource.py                  # Normalized Resource Document
│   │   ├── rule.py                      # Data-Driven Rule Specification
│   │   └── finding.py                   # Finding & Evidence Document
│   ├── schemas/                         # API Request & Response DTOs
│   │   ├── auth.py
│   │   ├── account.py
│   │   ├── resource.py
│   │   ├── rule.py
│   │   └── finding.py
│   ├── services/                        # Service Layer Orchestrators
│   │   ├── auth_service.py              # User authentication logic
│   │   ├── account_service.py           # Cloud Account lifecycle logic
│   │   └── scan_service.py              # Ingestion, Normalization & Scan Workflow
│   ├── providers/                       # Cloud Provider SDK Abstractions
│   │   ├── base.py                      # CloudProviderConnector Abstract Interface
│   │   ├── aws/                         # AWS Boto3 Connector & Aggregators
│   │   │   ├── connector.py
│   │   │   ├── inventory.py
│   │   │   ├── metrics.py
│   │   │   ├── costs.py
│   │   │   └── recommendations.py
│   │   ├── azure/                       # Azure SDK Connector
│   │   │   ├── connector.py
│   │   │   ├── inventory.py
│   │   │   ├── metrics.py
│   │   │   ├── costs.py
│   │   │   └── recommendations.py
│   │   └── gcp/                         # GCP SDK Connector
│   │       ├── connector.py
│   │       ├── inventory.py
│   │       ├── metrics.py
│   │       ├── costs.py
│   │       └── recommendations.py
│   ├── normalization/                   # Data Transformation Layer
│   │   ├── resource.py                  # Transform EC2/VM/GCE to common model
│   │   ├── metrics.py                   # Metric aggregation & unit normalization
│   │   └── cost.py                      # Currency & Billing normalization
│   └── rule_engine/                     # Rule Evaluation Engine
│       ├── engine.py                    # Master Rule Engine Controller
│       ├── evaluator.py                 # Recursive condition evaluator
│       ├── operators.py                 # Operators (eq, neq, gt, gte, lt, lte, in, not_in)
│       ├── registry.py                  # Rule Loader & In-memory cache
│       ├── evidence.py                  # Evidence payload generator
│       ├── savings.py                   # Savings calculation logic
│       └── rules/                       # Default Seed Rules (AWS, Azure, GCP)
│           ├── aws/
│           ├── azure/
│           └── gcp/
├── tests/                               # Pytest Test Suite (Mocked SDK responses)
├── requirements.txt                     # Python Dependencies
├── .env.example                         # Environment Variables Template
├── Dockerfile                           # Production Uvicorn Docker Container
└── README.md                            # Setup & Operations Guide
```

---

## 4. Normalized Data Model Specification

```json
{
  "_id": "65f1a2b3c4d5e6f7a8b9c0d1",
  "user_id": "65f1a0000000000000000001",
  "cloud_account_id": "65f1a1111111111111111111",
  "provider": "aws",
  "account_id": "123456789012",
  "resource_type": "compute_instance",
  "resource_id": "i-0a1b2c3d4e5f67890",
  "region": "us-east-1",
  "name": "prod-api-worker-01",
  "configuration": {
    "instance_type": "m5.2xlarge",
    "state": "running",
    "vpc_id": "vpc-01234567"
  },
  "tags": {
    "Environment": "Production",
    "Team": "Backend"
  },
  "metrics": {
    "cpu_average": 4.8,
    "cpu_p95": 11.2,
    "memory_average": 11.3,
    "memory_p95": 18.5
  },
  "cost": {
    "monthly": 112.50,
    "currency": "USD"
  },
  "last_synced_at": "2026-10-07T16:00:00Z"
}
```

---

## 5. API Endpoints Summary

| Group | Method | Path | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/auth/register` | Register user account |
| **Auth** | `POST` | `/api/auth/login` | Authenticate & return JWT bearer token |
| **Auth** | `GET` | `/api/auth/me` | Fetch active authenticated user profile |
| **Accounts**| `GET` | `/api/accounts` | List connected cloud accounts |
| **Accounts**| `POST` | `/api/accounts` | Connect new AWS/Azure/GCP account |
| **Accounts**| `GET` | `/api/accounts/{id}` | Get account connection detail |
| **Accounts**| `POST` | `/api/accounts/{id}/verify` | Verify cloud account credentials |
| **Accounts**| `POST` | `/api/accounts/{id}/scan` | Synchronously scan resources & run rules |
| **Accounts**| `DELETE`| `/api/accounts/{id}` | Remove connected cloud account |
| **Resources**| `GET` | `/api/resources` | List normalized inventory resources |
| **Rules** | `GET` | `/api/rules` | List active rules in Rule Registry |
| **Findings** | `GET` | `/api/findings` | Query generated findings & evidence |
| **Findings** | `GET` | `/api/findings/{id}` | Finding detail view with evidence payload |
| **Dashboard**| `GET` | `/api/dashboard/summary` | Return executive summary KPIs & savings |
