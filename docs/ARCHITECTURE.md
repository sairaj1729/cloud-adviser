# ARCHITECTURE.md - Cloud Advisor System Architecture & Design

This document details the architectural design, container topology, request lifecycles, data flows, and algorithmic rules engine powering the **Cloud Advisor** multi-cloud cost intelligence platform.

---

## High-Level System Architecture

Cloud Advisor uses a **three-tier microservices-inspired architecture** comprising:

1. **Presentation Layer**: A modern Single Page Application (SPA) built with **React 19**, **TanStack Start**, **Vite**, **TypeScript**, and **Tailwind CSS v4**.
2. **API & Business Logic Layer**: A **Python 3.10 Flask** backend container utilizing a multi-threaded process orchestrator (`main.py`) that executes 5 specialized microservice listeners on dedicated ports (`8000`, `5000`, `5001`, `5002`, `5005`).
3. **Data Persistence Layer**: A containerized **MySQL 8.0** relational database (`api_database`) storing historical cost usage records, user accounts, and benchmark instance utilization data.

```mermaid
graph TD
    Client[Browser User] -->|HTTP :3000 / :8080| Frontend[TanStack Start React 19 App]

    subgraph "Backend Container (Python Multi-Threaded Process)"
        Frontend -->|POST /api/login :8000| AuthSvc[login.py - Auth Service]
        Frontend -->|GET /fetch-cost-usage-* :5000| AWSSvc[aws.py - AWS Cost Service]
        Frontend -->|GET /fetch-azure-* :5001| AzureSvc[azure_script.py - Azure Cost Service]
        Frontend -->|GET /api/*-unused-services :5002| UnusedSvc[unused.py - Unused Engine]
        Frontend -->|GET /fetch-cost-usage-* :5005| GCPSvc[GCP.py - GCP Cost Service]

        ThreadMgr[main.py Thread Manager] -.->|Spawns| AuthSvc
        ThreadMgr -.->|Spawns| AWSSvc
        ThreadMgr -.->|Spawns| AzureSvc
        ThreadMgr -.->|Spawns| UnusedSvc
        ThreadMgr -.->|Spawns| GCPSvc
    end

    subgraph "External Cloud Provider APIs"
        AWSSvc -->|Boto3 SDK| AWSCE[AWS Cost Explorer API]
        AzureSvc -->|Azure Mgmt SDK| AzureCost[Azure Cost Management API]
        GCPSvc -->|Google Cloud SDK| GCPBilling[GCP Billing API]
    end

    subgraph "Database Tier (Container)"
        AuthSvc -->|SQL| MySQL[(MySQL 8.0 - api_database)]
        AWSSvc -->|SQL| MySQL
        AzureSvc -->|SQL| MySQL
        UnusedSvc -->|SQL| MySQL
        GCPSvc -->|SQL| MySQL
    end
```

---

## Container & Network Topology

The application stack is orchestrated via `docker-compose.yml` on an isolated bridge network named `app-network`.

```text
+---------------------------------------------------------------------------------------+
|                                    DOCKER HOST                                        |
|                                                                                       |
|  +----------------------+     +-------------------------------+     +--------------+  |
|  |       frontend       |     |            backend            |     |    mysql     |  |
|  | (React / TanStack)   |     | (Python Flask Multi-Thread)   |     | (MySQL 8.0)  |  |
|  |                      |     |                               |     |              |  |
|  | Port: 3000 / 8080    |     | Port 8000: Login              |     | Port: 3306   |  |
|  |                      |     | Port 5000: AWS API            |     |    -> 3308   |  |
|  |                      |     | Port 5001: Azure API          |     |              |  |
|  |                      |     | Port 5002: Unused API         |     |              |  |
|  |                      |     | Port 5005: GCP API            |     |              |  |
|  +----------+-----------+     +---------------+---------------+     +------+-------+  |
|             |                                 |                            |          |
|             +---------------------------------+----------------------------+          |
|                                         app-network                                   |
+---------------------------------------------------------------------------------------+
```

---

## Detailed Sequence & Data Flows

### 1. Authentication Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as React LoginPage
    participant Auth as login.py (:8000)
    participant DB as MySQL api_database

    User->>Frontend: Input Username & Password
    Frontend->>Auth: POST /api/login { username, password }
    Auth->>DB: SELECT * FROM users WHERE username=%s AND password=%s
    DB-->>Auth: User Record / null
    alt Valid Credentials
        Auth-->>Frontend: 200 OK { success: true, username: "Achal" }
        Frontend->>Frontend: Save selectedCloud & user session context
        Frontend-->>User: Navigate to Dashboard (/cost-usage)
    else Invalid Credentials
        Auth-->>Frontend: 401 Unauthorized { error: "Invalid credentials" }
        Frontend-->>User: Display authentication error toast
    end
```

---

### 2. Cost Dashboard Query Flow (AWS Example)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Cost Usage Component
    participant AWS as aws.py (:5000)
    participant DB as MySQL api_database

    User->>UI: Select Provider "AWS" & Filter "Daily"
    UI->>AWS: GET /fetch-cost-usage-daily
    AWS->>DB: SELECT date, service, SUM(cost) AS service_cost FROM aws_costusage GROUP BY date, service ORDER BY date
    DB-->>AWS: Rows [{ date: "2025-01-01", service: "Amazon EC2", service_cost: 18.4200000 }]
    AWS->>AWS: Format service_cost to .7f precision string
    AWS-->>UI: 200 OK { cost_usage_daily: [...] }
    UI->>UI: Aggregate total cost, average monthly spending & active service count
    UI-->>User: Render Recharts Trend Bar Graph & Service Cost Donut Chart
```

---

### 3. Cloud Provider Live Synchronization Flow

```mermaid
sequenceDiagram
    autonumber
    participant Admin as Scheduled Job / Internal Route
    participant Backend as aws.py / azure_script.py / GCP.py
    participant Cloud as Cloud Provider API (AWS CE / Azure / GCP)
    participant DB as MySQL api_database

    Admin->>Backend: Trigger Sync (e.g. GET /getAWSClooudCost)
    Backend->>Cloud: Request Cost Explorer API (Start: 2025-01-01, End: Today)
    Cloud-->>Backend: Return Granularity='DAILY', Metrics=['BlendedCost'], GroupBy=['SERVICE']
    loop For Each Date & Service Result
        Backend->>DB: INSERT INTO aws_costusage (service, service_total, date, cost, total_cost) VALUES (...) ON DUPLICATE KEY UPDATE cost=VALUES(cost), total_cost=VALUES(total_cost)
    end
    Backend->>DB: COMMIT Transaction
    Backend-->>Admin: 200 OK { message: "Cost data synced successfully" }
```

---

### 4. Unused Service & Recommendations Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Recommendations / Unused Page
    participant Unused as unused.py (:5002)
    participant DB as MySQL api_database

    User->>UI: Open /unused-services or /recommendations
    UI->>Unused: GET /api/aws-unused-services (or azure/gcp)
    Unused->>DB: SELECT service, date FROM aws_costusage WHERE total_cost < 0.000001
    DB-->>Unused: Array of zero-cost / low-cost records
    Unused-->>UI: 200 OK [{ service: "Amazon RDS", date: "2025-01-15" }]
    UI->>UI: Evaluate rules engine heuristics (Right-sizing, Reserved Instances, Archival)
    UI-->>User: Render prioritized finding cards with estimated monthly savings ($)
```

---

## Algorithmic Rules & Recommendation Heuristics

The **Recommendation Engine** evaluates resource utilization metrics stored in MySQL (`book1`, `costusage`, `aws_costusage`, `azureusage`, `gcp_costusage`) against specific heuristic rules:

### 1. Unused / Idle Service Detection Rules
- **AWS Threshold**: `total_cost < 0.000001` over a 30-day window -> Tagged as *Zero-Cost / Idle Service*.
- **Azure Threshold**: `PreTaxCost <= 3.00` over billing cycle -> Tagged as *Minimal Utilization Service*.
- **GCP Threshold**: `cost <= 10.00` over billing cycle -> Tagged as *Low Activity Resource*.

### 2. Compute Right-Sizing Heuristic
$$\text{Average CPU} < 15\% \quad \text{AND} \quad \text{Average Memory} < 25\% \implies \text{Recommend Downsizing SKU}$$
- *Action*: Downsize instance tier by one step (e.g. `m5.2xlarge` $\to$ `m5.xlarge`), yielding an estimated **50% cost reduction**.

### 3. Reserved Instances (RI) / Savings Plans Heuristic
$$\text{Service Run Hours} \ge 720 \text{ hrs/month} \quad \text{AND} \quad \text{Utilization Consistency} \ge 90\% \implies \text{Recommend 1-Yr / 3-Yr RI}$$
- *Action*: Purchase 1-Year or 3-Year Reserved Instances / Savings Plans, yielding an estimated **30%--60% cost reduction**.

### 4. Object Storage Archival Heuristic
$$\text{Last Read Access} \ge 30 \text{ days} \quad \text{AND} \quad \text{Bucket Storage} > 100 \text{ GB} \implies \text{Recommend Storage Tier Transition}$$
- *Action*: Transition objects from S3 Standard / Blob Standard to Glacier / Coldline storage, yielding an estimated **70% storage cost reduction**.
