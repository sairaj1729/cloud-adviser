# Cloud Advisor - FastAPI V1 Backend

A clean, modular V1 backend for **Cloud Advisor**, built with **Python 3.12+**, **FastAPI**, and **MongoDB (Motor)**. 

It implements a provider-decoupled FinOps optimization pipeline that discovers resources across **AWS**, **Microsoft Azure**, and **Google Cloud Platform (GCP)**, normalizes them into a unified schema, and runs a data-driven Rule Engine to generate cost savings recommendations.

---

## 1. High-Level Architecture

```text
React Frontend
      │
      │ REST API (JWT Authenticated)
      ▼
FastAPI Backend (Modular Monolith)
      │
      ├── Auth Service (JWT + Passlib/Argon2)
      ├── Account Manager (AWS STS AssumeRole, Azure Entra, GCP Identity)
      ├── Provider Connectors (boto3, Azure SDK, Google Cloud client libraries)
      ├── Data Normalization Pipeline
      ├── MongoDB Database (users, cloud_accounts, resources, rules, findings)
      └── Data-Driven Rule Engine (Operators, Evidence & Savings Calculators)
```

---

## 2. Key Directories

- `app/api/`: FastAPI route handlers for Auth, Accounts, Resources, Rules, Findings, and Dashboard.
- `app/core/`: Configuration via Pydantic BaseSettings, Security (JWT/Password Hashing), and FastAPI Dependencies.
- `app/db/`: MongoDB AsyncMotor connection manager & automated index initialization.
- `app/providers/`: Encapsulated cloud provider connectors (`base.py`, `aws/`, `azure/`, `gcp/`).
- `app/normalization/`: Data transformers for mapping raw provider payloads to common resource models.
- `app/rule_engine/`: Data-driven rule evaluator, comparison operators, evidence builder, and savings calculator.
- `docs/`: In-depth documentation for architecture, provider integration, rule engine, and API specs.

---

## 3. Installation & Local Setup

### Prerequisites
- Python 3.12+
- MongoDB Server running locally on `localhost:27017` (or Docker container)

### Step 1: Virtual Environment
```bash
cd backend
python -m venv venv

# On Linux/macOS:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Environment Configuration
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

Set your local MongoDB URI and JWT secrets:
```env
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DATABASE="cloud_advisor"
SECRET_KEY="supersecret_jwt_signing_key"
```

### Step 4: Run FastAPI Dev Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000/api/docs`** to access interactive Swagger API documentation.

---

## 4. Docker Deployment

### Run with Docker
```bash
docker build -t cloud-advisor-backend .
docker run -p 8000:8000 --env-file .env cloud-advisor-backend
```

---

## 5. Running Tests

Unit tests mock cloud provider API responses and test normalization and rule evaluation without calling live APIs:

```bash
pytest
```

---

## 6. How to Add a New Rule

1. Open `backend/app/rule_engine/registry.py` (or post to `/api/rules`).
2. Add a new data-driven rule definition:
```json
{
  "rule_id": "AWS-EBS-001",
  "name": "Unattached EBS Volume",
  "provider": "aws",
  "resource_type": "storage_volume",
  "conditions": {
    "logic": "AND",
    "items": [
      {"field": "configuration.state", "operator": "eq", "threshold": "available"}
    ]
  },
  "savings_calculation": {"type": "ZERO_UTILIZATION"},
  "severity": "high",
  "status": "active"
}
```

---

## 7. How to Add a New Provider

1. Create a new directory in `app/providers/<provider_name>/`.
2. Implement `CloudProviderConnector` (`verify_connection`, `get_resources`, `get_metrics`, `get_costs`, `get_recommendations`).
3. Add a normalizer method in `app/normalization/resource.py`.
4. Register the connector in `app/providers/factory.py`.
5. The Rule Engine will automatically work with the new provider without code changes.
