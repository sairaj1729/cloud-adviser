# CURRENT_STATE.md - Application Status & Engineering Roadmap

This document captures the **current operational state** of the Cloud Advisor platform as of **October 2026**. It lists fully functional capabilities, features in progress, known bugs/limitations, security vulnerabilities, and upcoming engineering priorities.

---

## Executive Summary

| Subsystem / Feature | Operational Status | Summary & Details |
| :--- | :--- | :--- |
| **Modern Web UI (`frontend/`)** | 🟢 Fully Functional | Built with React 19, TanStack Start, Vite, and Tailwind v4. Responsive navigation, provider context switching, and interactive charts active. |
| **Docker Orchestration** | 🟢 Fully Functional | Docker Compose manages Frontend (Nginx), Backend (Flask 5-port multi-thread container), and MySQL 8.0 (`api_database`). |
| **User Authentication** | 🟢 Functional | Login validation against MySQL `users` table via `POST /api/login` (Port 8000). |
| **AWS Cost Analytics** | 🟢 Fully Functional | Boto3 Cost Explorer integration active; daily, monthly, 15-day interval, and custom date range queries operational. |
| **Azure Cost Analytics** | 🟡 Needs Bug Fix | Dashboard view functional; `/getAzureCloudCost` sync route triggers a `NameError` due to function name mismatch in `azure_script.py`. |
| **GCP Cost Analytics** | 🟡 Partial / Mock Data | Dashboard views functional; GCP synchronization script uses a stubbed mock data payload. |
| **Unused Service Engine** | 🟢 Fully Functional | Detects zero/low-cost services across AWS (`< $0.000001`), Azure (`<= $3.00`), and GCP (`<= $10.00`) via Port 5002. |
| **Recommendation Engine** | 🟢 Fully Functional | Heuristic cost optimization engine generates prioritized right-sizing, reserved instance, and storage archival suggestions. |

---

## Detailed Feature Status

### 1. Fully Functional Features

- **Modern Frontend Redesign (`frontend/`)**:
  - File-based routing via `@tanstack/react-router` (`/`, `/login`, `/cost-usage`, `/unused-services`, `/low-utilization`, `/recommendations`, `/account`).
  - Provider context switching across **AWS**, **Azure**, and **GCP**.
  - Interactive data visualization powered by **Recharts** and custom metric cards.
  - Centralized API endpoint routing defined in `src/config/api.ts`.
- **AWS Cost Intelligence (`aws.py` - Port 5000)**:
  - Fetches daily costs (`/fetch-cost-usage-daily`), monthly aggregated costs (`/fetch-cost-usage-monthly`), 15-day sampling (`/fetch-cost-usage-15days`), and date range filtered records (`/fetch-cost-usage-date-range`).
  - Integrates Boto3 Cost Explorer (`ce.get_cost_and_usage`) pulling `BlendedCost` metrics into `aws_costusage`.
- **Unused Resource Detection (`unused.py` - Port 5002)**:
  - Interrogates `aws_costusage`, `azureusage`, and `gcp_costusage` tables for zero/low usage records.
  - Displays resource names, cost impact, and detection dates.
- **Low Utilization Metrics**:
  - Highlights compute instances running at low CPU/Memory thresholds (e.g. CPU < 15%, Memory < 25%).
- **Recommendation Engine**:
  - Generates actionable savings cards categorized by severity (High, Medium, Low) and confidence score.
- **Database Initialization (`mysql/mydb.sql`)**:
  - Automatically provisions `api_database` with 7 core tables and seed data upon initial `docker-compose up`.

---

### 2. In-Progress & Known Bugs

> [!WARNING]
> The following issues require developer resolution:

1. **`NameError` Bug in `azure_script.py`**:
   - Endpoint `@app.route('/getAzureCloudCost')` invokes `fetch_and_insert_azure_cost_usage_data()`, but the actual function definition in `azure_script.py` is named `fetch_and_insert_cost_usage_data()`. Calling this endpoint will result in a runtime `NameError: name 'fetch_and_insert_azure_cost_usage_data' is not defined`.
2. **Mocked GCP Sync Payload (`GCP.py`)**:
   - Function `fetch_and_insert_cost_usage_data()` connects to Google Billing client but inserts a hardcoded dummy record `[{'service': 'example-service', 'service_total': 123.456789, ...}]` into `gcp_costusage` instead of processing live BigQuery billing export rows.
3. **Hardcoded Machine Path Fallback in `GCP.py`**:
   - `GCP.py` contains a hardcoded fallback path (`C:\Users\khamk\OneDrive\Desktop\...`) for `GCP_KEY_PATH`.

---

## Security Vulnerabilities & Technical Debt

1. **Plaintext Password Storage**:
   - User credentials in the MySQL `users` table are stored as unhashed text (`achal`, `123`).
   - *Remediation*: Implement password hashing using `werkzeug.security` (`generate_password_hash` / `check_password_hash`) or `bcrypt`.
2. **Hardcoded Database Credentials in Python Code**:
   - `unused.py` hardcodes `host="mysql"`, `user="root"`, `password="Cloud@123"`.
   - *Remediation*: Refactor `unused.py` to use `os.getenv()` environment variables consistent with `login.py` and `aws.py`.
3. **Permissive CORS Wildcards**:
   - `login.py`, `aws.py`, `unused.py`, `azure_script.py`, and `GCP.py` apply broad CORS wildcards (`Access-Control-Allow-Origin: *`).
   - *Remediation*: Restrict origins to trusted frontend domains (`http://localhost:3000`, `http://localhost:8080`).
4. **Development WSGI Server Warning**:
   - `main.py` starts Flask development servers via `app.run()` inside Python threads. This displays WSGI production warnings and should be replaced with Gunicorn workers in production deployments.

---

## Actionable Engineering Roadmap

### Phase 1: High-Priority Fixes (Immediate)
- [ ] Fix function name mismatch in `azure_script.py` (`fetch_and_insert_cost_usage_data`).
- [ ] Refactor `unused.py` to pull database credentials from environment variables (`.env`).
- [ ] Implement `werkzeug.security` password hashing for user registration and authentication.

### Phase 2: System Refactoring (Medium-Term)
- [ ] Complete GCP Billing API integration to ingest live Google Cloud BigQuery billing data.
- [ ] Introduce an API Gateway (Nginx reverse proxy container) to unify backend endpoints under a single port (`5000`) with path-based routing (`/api/auth`, `/api/aws`, `/api/azure`, `/api/gcp`, `/api/unused`).
- [ ] Add multi-tenant user credential management (allowing individual users to configure their own AWS/Azure/GCP API keys via the Account settings page).

### Phase 3: Advanced Optimization (Long-Term)
- [ ] Implement automated background cron jobs for periodic cloud cost synchronization.
- [ ] Add PDF / CSV export capabilities for cost usage reports and recommendations.
