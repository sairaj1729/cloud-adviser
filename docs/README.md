# Cloud Advisor - Multi-Cloud Cost Optimization Platform

**Cloud Advisor** is a multi-cloud cost intelligence, analytics, and management platform designed to help organizations monitor, analyze, and optimize cloud infrastructure expenditures across **Amazon Web Services (AWS)**, **Microsoft Azure**, and **Google Cloud Platform (GCP)**.

The platform aggregates billing, daily/monthly usage metrics, and resource utilization data into intuitive interactive dashboards. It detects zero-cost and underutilized idle resources, provides algorithmic cost optimization recommendations (e.g. right-sizing, Reserved Instances / Savings Plans, storage class optimization), and handles user access control.

---

## Technical Architecture Overview

Cloud Advisor utilizes a **three-tier containerized architecture**:

1. **Frontend Layer**: 
   - **Modern Frontend (`frontend/`)**: Built with **React 19**, **TanStack Start**, **Vite**, **TypeScript**, **Tailwind CSS v4**, and **Recharts**.
   - **Legacy Frontend**: React 18 SPA served via Nginx.
2. **Backend Microservices Layer**: 
   - Powered by **Python 3.10** and **Flask**.
   - Uses a **multi-threaded orchestrator (`main.py`)** to run 5 specialized microservice listeners on dedicated ports within a single runtime container.
3. **Database Layer**: 
   - **MySQL 8.0** relational database (`api_database`) storing historical cost metrics, user accounts, and resource utilization data.

---

## Service Port Mapping

When deployed via Docker Compose or run locally, the services communicate across the following ports:

| Service / Container | Internal Port | Host Port | Endpoint / Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend Web UI** | `80` / `3000` | `8080` / `3000` | `http://localhost:8080` or `http://localhost:3000` - Interactive Dashboard UI |
| **Authentication Service** | `8000` | `8000` | `http://localhost:8000/api/login` - Auth & User Credential Validation (`login.py`) |
| **AWS Cost Service** | `5000` | `5000` | `http://localhost:5000/fetch-cost-usage-daily` - AWS Cost Explorer & DB metrics (`aws.py`) |
| **Azure Cost Service** | `5001` | `5001` | `http://localhost:5001/fetch-cost-usage-daily` - Azure Cost Management & DB metrics (`azure_script.py`) |
| **Unused Services Engine** | `5002` | `5002` | `http://localhost:5002/api/aws-unused-services` - Zero/Low-cost idle resource detection (`unused.py`) |
| **GCP Cost Service** | `5005` | `5005` | `http://localhost:5005/fetch-cost-usage-daily` - GCP Billing & DB metrics (`GCP.py`) |
| **MySQL Database** | `3306` | `3308` | `localhost:3308` - Relational Storage (`api_database`) |

---

## Directory Structure

```text
cloud-adviser/
├── frontend/                        # Modern React 19 + TanStack Start Frontend
│   ├── src/
│   │   ├── components/cloud/        # Dashboard Shell, Charts, Approvals, Connections, Views
│   │   ├── config/api.ts            # Centralized API endpoint routing configuration
│   │   ├── mockData/                # Provider metadata, trend data, resources & findings
│   │   ├── routes/                  # TanStack Router route tree (index, login, cost-usage, etc.)
│   │   └── styles.css               # Global Tailwind CSS v4 styling
│   ├── package.json                 # Node dependencies & Vite scripts
│   └── vite.config.ts               # Vite & TanStack Start build configuration
└── docs/                            # Core Documentation Suite
    ├── README.md                    # Project overview, architecture, setup & usage (this file)
    ├── AGENTS.md                    # Operational guidelines and constraints for AI coding agents
    ├── CURRENT_STATE.md             # Operational status, completed features, known bugs & roadmap
    ├── ARCHITECTURE.md              # In-depth system design, data flows & sequence diagrams
    ├── DATABASE.md                  # Complete MySQL schema, table specifications & query registry
    └── DECISIONS.md                 # Architectural Decision Records (ADRs)
```

---

## Key Features & Capabilities

- **Unified Multi-Cloud Dashboard**: Seamlessly switch between **AWS**, **Azure**, and **GCP** views while maintaining global provider context.
- **Cost Analytics & Visualization**:
  - Daily, monthly, 15-day interval, and custom date range spending breakdowns.
  - Interactive trend bar graphs and cost distribution charts.
- **Unused Service Detection**: Automated detection of zero-cost or minimal-utilization services:
  - AWS: `total_cost < 0.000001`
  - Azure: `PreTaxCost <= 3.00`
  - GCP: `cost <= 10.00`
- **Low Utilization Analysis**: Resource-level inspection of compute instances (CPU/Memory usage) to identify downsizing candidates.
- **Algorithmic Recommendation Engine**: Tailored cost-reduction advice prioritizing High, Medium, and Low severity savings opportunities.
- **Cloud API Synchronization**: Direct integration with AWS Boto3 Cost Explorer, Azure Cost Management SDK, and Google Cloud Billing APIs.

---

## Quick Start & Installation

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+) or [Bun](https://bun.sh/)
- [Python](https://www.python.org/) (v3.10+)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v20.10+) with Docker Compose
- Git

---

### Method 1: Running with Docker Compose (Recommended)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/sairaj1729/cloud-adviser.git
   cd cloud-adviser
   ```

2. **Configure Environment Variables**:
   Create a `.env` file for backend cloud credentials:
   ```env
   # Database Credentials
   DB_HOST=mysql
   DB_USER=root
   DB_PASSWORD=Cloud@123
   DB_NAME=api_database

   # AWS Cloud Credentials
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=us-east-1

   # Azure Cloud Credentials
   AZURE_TENANT_ID=your_tenant_id
   AZURE_CLIENT_ID=your_client_id
   AZURE_CLIENT_SECRET=your_client_secret
   AZURE_SUBSCRIPTION_ID=your_subscription_id

   # GCP Credentials
   GCP_KEY_PATH=key.json
   ```

3. **Launch the Container Stack**:
   ```bash
   docker-compose up --build
   ```

4. **Access the Application**:
   Open browser at `http://localhost:8080` (or `http://localhost:3000`).

---

### Method 2: Manual Local Development Setup

#### 1. Frontend Setup
```bash
cd frontend
npm install   # or bun install
npm run dev   # or bun dev
```
The modern frontend will be available at `http://localhost:3000`.

#### 2. Backend Setup
```bash
# Navigate to backend directory
cd path/to/Cloud_Advisor_Backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install Python requirements
pip install -r requirement.txt

# Start multi-threaded Flask orchestrator
python main.py
```

---

## Default Login Credentials

Initial database seed data includes pre-configured demo user accounts:

| Username | Password | Access Level |
| :--- | :--- | :--- |
| `Achal` | `achal` | Administrator |
| `varshini` | `123` | Administrator |

---

## Workflow & User Journey

1. **Login & Authenticate**: User submits credentials on `/login` -> Validated via `POST http://localhost:8000/api/login`.
2. **Provider Selection**: User selects AWS, Azure, or GCP -> Provider choice stored in browser context / `localStorage`.
3. **Analyze Cost Trends**: View daily/monthly trends on `/cost-usage`. Filter by custom date range.
4. **Inspect Unused Services**: Navigate to `/unused-services` to identify idle resources and review cost details.
5. **Review Recommendations**: Navigate to `/recommendations` to view actionable right-sizing, reserved instance, and archival suggestions.
