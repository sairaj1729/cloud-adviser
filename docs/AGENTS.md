# AGENTS.md - Operational Instructions & Guidelines for AI Coding Agents

This document defines the architectural patterns, code conventions, operational rules, and constraints that **AI coding agents** (and human developers) must follow when inspecting, modifying, or extending the Cloud Advisor codebase.

---

## Workspace Map & Directory Structure

```text
cloud-adviser/
├── frontend/                               # Modern React 19 + TanStack Start Frontend
│   ├── src/
│   │   ├── components/cloud/               # UI components (AppShell, Charts, Approvals, etc.)
│   │   ├── config/api.ts                   # Centralized backend URL config
│   │   ├── mockData/                       # Demo dataset & provider metadata
│   │   ├── routes/                         # TanStack Start file-based routing
│   │   └── styles.css                      # Tailwind CSS v4 entry point
│   ├── package.json                        # Frontend packages & scripts
│   └── vite.config.ts                      # Vite build setup
└── docs/                                   # Documentation suite
    ├── README.md                           # Quick start, features & overview
    ├── AGENTS.md                           # AI agent rules & guidelines (this file)
    ├── CURRENT_STATE.md                    # System status, bugs & roadmap
    ├── ARCHITECTURE.md                     # System architecture & sequence diagrams
    ├── DATABASE.md                         # Database schema & query registry
    └── DECISIONS.md                        # Architectural Decision Records (ADRs)
```

> [!IMPORTANT]
> Always verify relative paths when adding or importing files. Frontend source code resides in `frontend/src/`, and documentation files reside in `docs/`.

---

## Architectural Rules & Code Conventions

### 1. Backend Multi-Threaded Microservices Architecture (`main.py`)
- The backend runs **5 distinct Flask application servers** on separate TCP ports within a single Python process, managed via `threading.Thread` in `main.py`:
  - `login_app` on Port `8000` (`login.py`)
  - `aws_app` on Port `5000` (`aws.py`)
  - `azure_app` on Port `5001` (`azure_script.py`)
  - `unused_app` on Port `5002` (`unused.py`)
  - `gcp_app` on Port `5005` (`GCP.py`)
- **Rules for Agents**:
  - Do **NOT** assume a single unified Flask app instance or shared global memory state.
  - Adding new routes must be done inside the specific service script (`aws.py`, `login.py`, etc.).
  - If introducing a new backend microservice, import its Flask `app` in `main.py` and assign a new thread listener on an unused port.

---

### 2. Database Driver Dual-Convention & Connection Hygiene
- The codebase uses **two distinct MySQL libraries**:
  - `mysql.connector`: Used in `login.py` and parts of `unused.py`.
  - `pymysql`: Used in `aws.py`, `azure_script.py`, and `GCP.py`.
- **Rules for Agents**:
  - Always wrap SQL queries in `try...except...finally` blocks.
  - **Mandatory**: Close both `cursor` and `connection` objects in the `finally:` block to prevent MySQL thread connection exhaustion.
  - Use `DictCursor` (`pymysql.cursors.DictCursor` or `conn.cursor(dictionary=True)`) to ensure query results are returned as key-value dictionaries.
  - **Parameterized Queries**: Always use `%s` placeholders for dynamic SQL values. Never construct SQL queries via raw string interpolation or f-strings.

---

### 3. Currency Precision & High-Precision Decimal Formatting
- Cloud cost figures often contain micro-cents (e.g. `$0.0000004`).
- **Rules for Agents**:
  - In MySQL, currency columns use `DECIMAL(15,10)` or `DECIMAL(20,7)`.
  - When returning cost totals from Flask endpoints, format numeric strings to 7 decimal places:
    ```python
    row['service_cost'] = f"{float(row['service_cost']):.7f}"
    ```
  - Do NOT cast currency values directly to standard 2-decimal floats before JSON serialization, as this truncates zero-cost and low-cost detection data.

---

### 4. Frontend Architecture & Context Management
- **Routing Engine**: `frontend/` uses **TanStack Start** with file-based routing (`@tanstack/react-router`).
- **Centralized API Config**: All backend endpoint base URLs are defined in `frontend/src/config/api.ts`:
  ```ts
  export const API_ENDPOINTS = {
    auth: 'http://localhost:8000',
    AWS: 'http://localhost:5000',
    Azure: 'http://localhost:5001',
    GCP: 'http://localhost:5005',
    unused: 'http://localhost:5002',
  } as const;
  ```
- **Rules for Agents**:
  - Do **NOT** hardcode API URLs inside individual React components. Import `API_ENDPOINTS` from `src/config/api.ts`.
  - Fallback cleanly when accessing cloud provider selection context (`AWS` | `Azure` | `GCP`).

---

### 5. Defensive Error Handling & Response Contracts
- **Rules for Agents**:
  - Handle empty query results (`fetchall()` returning `[]` or `None`) gracefully without throwing `TypeError` or `KeyError`.
  - Flask endpoints must return structured JSON responses with explicit HTTP status codes (e.g., `400` for missing parameters, `401` for invalid credentials, `500` for database failures).
  - Explicitly include CORS headers on custom OPTIONS preflight routes.

---

## Agent Verification Checklist

Before marking any task as complete, AI agents must verify:

1. [ ] **Syntax Validation**: Python files pass `python -m py_compile <file.py>` and TypeScript frontend code passes `npm run lint` / `bun dev`.
2. [ ] **Connection Cleanup**: Every database transaction in backend Python code closes `cursor` and `connection` inside a `finally:` block.
3. [ ] **API Endpoint Consistency**: Updated backend endpoints correspond to the mapping in `frontend/src/config/api.ts`.
4. [ ] **Documentation Updates**: Any changes to database tables, API routes, or architectural patterns are documented in the respective files under `docs/`.
