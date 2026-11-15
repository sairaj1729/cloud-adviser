# DECISIONS.md - Architectural Decision Records (ADRs)

This document captures the key architectural decisions, rationale, trade-offs, and technical design choices established during the development of the Cloud Advisor platform.

---

## ADR Index

1. [ADR-001: Multi-Threaded Flask Microservice Orchestration](#adr-001-multi-threaded-flask-microservice-orchestration)
2. [ADR-002: MySQL Caching Layer for Remote Cloud Provider APIs](#adr-002-mysql-caching-layer-for-remote-cloud-provider-apis)
3. [ADR-003: Client-Side Provider Context Persistence](#adr-003-client-side-provider-context-persistence)
4. [ADR-004: Dedicated Microservice Port Allocation](#adr-004-dedicated-microservice-port-allocation)
5. [ADR-005: High-Precision String Formatting for Currency Metrics](#adr-005-high-precision-string-formatting-for-currency-metrics)
6. [ADR-006: Modern React 19 & TanStack Start Frontend Architecture](#adr-006-modern-react-19--tanstack-start-frontend-architecture)

---

## Detailed Decision Records

### ADR-001: Multi-Threaded Flask Microservice Orchestration

#### Context & Problem
The system requires distinct domain services (User Authentication, AWS Cost Explorer integration, Azure Cost Management integration, GCP Billing integration, Unused Resource detection). Deploying each service as a separate Docker container increases Docker build times, local memory consumption, and developer setup friction.

#### Decision
Implement a **multi-service thread manager** (`main.py`) that uses Python's native `threading.Thread` module to start 5 distinct Flask application servers listening on separate ports (`8000`, `5000`, `5001`, `5002`, `5005`) within a **single backend Docker container**.

#### Rationale & Advantages
- **Single Container Deployment**: Keeps Docker Compose topology simple (3 containers: `frontend`, `backend`, `mysql`).
- **Shared Python Runtime**: Avoids duplicating Python interpreter dependencies across 5 separate images.
- **Domain Logic Separation**: Isolates AWS logic in `aws.py`, Azure in `azure_script.py`, GCP in `GCP.py`, etc.

#### Tradeoffs & Consequences
- **Python GIL Constraints**: Python's Global Interpreter Lock limits true CPU-bound parallelism across threads.
- **Development WSGI Server Warning**: Running Flask development servers (`app.run()`) inside threads is suitable for local development/demonstration, but should be replaced with Gunicorn workers or an Nginx API Gateway for production traffic.

---

### ADR-002: MySQL Caching Layer for Remote Cloud Provider APIs

#### Context & Problem
Invoking cloud provider APIs (AWS Boto3 Cost Explorer, Azure Mgmt API, Google Billing API) synchronously on every user dashboard request causes high latency (2--5s per query), risks hitting cloud rate limits, and incurs API charge costs (e.g. AWS Cost Explorer charges $0.01 per query).

#### Decision
Cache all ingested cloud cost metrics in local MySQL database tables (`aws_costusage`, `azureusage`, `gcp_costusage`). Frontend dashboard pages query local MySQL tables rather than making live external HTTP requests to cloud provider APIs.

#### Rationale & Advantages
- **Sub-Millisecond Latency**: Local database queries execute in milliseconds instead of waiting for external cloud API round-trips.
- **Cost Minimization**: Prevents incurring API billing fees from repeated Cost Explorer queries.
- **Offline Resilience**: Frontend remains operational even during temporary cloud provider API downtime.

#### Tradeoffs & Consequences
- **Data Freshness**: Requires explicit sync triggers (e.g. `/getAWSClooudCost`) or automated background cron jobs to pull fresh data into MySQL.

---

### ADR-003: Client-Side Provider Context Persistence

#### Context & Problem
The user must switch between AWS, Azure, and GCP views seamlessly across different feature pages (Cost Usage, Unused Services, Low Utilization, Recommendations, Account Management). Complex state management boilerplate adds friction for a simple provider toggle state.

#### Decision
Maintain active cloud provider selection context (`"AWS"`, `"Azure"`, `"GCP"`) in the browser context / `localStorage` (`localStorage.setItem("selectedCloud", platform)`).

#### Rationale & Advantages
- **State Survival**: Selected provider context survives page refreshes and direct URL navigation.
- **Clean Component Access**: Components can read current provider state directly:
  ```ts
  const selectedCloud = localStorage.getItem("selectedCloud") || "AWS";
  ```

#### Tradeoffs & Consequences
- Requires explicit component re-renders when the selected provider tab changes.

---

### ADR-004: Dedicated Microservice Port Allocation

#### Context & Problem
Without an API gateway container, routing requests to multiple backend domain modules requires explicit port mappings.

#### Decision
Allocate dedicated TCP ports per backend microservice module:
- Port `8000`: Authentication (`login.py`)
- Port `5000`: AWS Cost Management (`aws.py`)
- Port `5001`: Azure Cost Management (`azure_script.py`)
- Port `5002`: Unused Resources Engine (`unused.py`)
- Port `5005`: GCP Cost Management (`GCP.py`)

#### Rationale & Advantages
- **Port-Level Domain Separation**: A failure or delay in Azure or GCP API processing does not block AWS or Login services.
- **Independent Testing**: Developers can curl or debug port `5000` independently without bringing up the full application stack.

#### Tradeoffs & Consequences
- **CORS Management**: Frontend must handle cross-origin requests to multiple ports on `localhost`.
- Centralized configuration (`frontend/src/config/api.ts`) is required to avoid hardcoded URLs spread across components.

---

### ADR-005: High-Precision String Formatting for Currency Metrics

#### Context & Problem
Cloud cost metrics frequently contain micro-fractional cent values (e.g. `$0.0000004` per unit hour). Converting currency values directly to standard 2-decimal floats causes floating-point truncation or binary floating-point representation drift (`0.1 + 0.2 = 0.30000000000000004`).

#### Decision
Define MySQL currency columns as high-precision decimals (`DECIMAL(15,10)` or `DECIMAL(20,7)`) and explicitly format numeric values as 7-decimal place strings (`f"{float(val):.7f}"`) in Flask response serializers.

#### Rationale & Advantages
- **Prevents Floating Point Drift**: Avoids JavaScript / Python floating-point arithmetic artifacts.
- **Accurate Aggregation**: Preserves micro-cost records essential for zero-cost vs low-cost unused service detection.

---

### ADR-006: Modern React 19 & TanStack Start Frontend Architecture

#### Context & Problem
The legacy React 18 frontend relied on unmaintained dependencies, hardcoded port strings in components, and basic CSS.

#### Decision
Migrate the primary web UI in `frontend/` to **React 19**, **TanStack Start**, **Vite**, **TypeScript**, **Tailwind CSS v4**, and **Recharts**.

#### Rationale & Advantages
- **Type Safety**: Full TypeScript support across route parameters, API responses, and chart data structures.
- **File-Based Routing**: Clean route organization via TanStack Router (`frontend/src/routes/`).
- **Modern Data Visualization**: Recharts integration for responsive, high-performance trend charts.
- **Centralized API Management**: Configurable backend target routing in `src/config/api.ts`.
