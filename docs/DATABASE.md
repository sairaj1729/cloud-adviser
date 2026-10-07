# DATABASE.md - Database Specifications & Schema Documentation

This document provides complete technical documentation for the **MySQL 8.0** relational database (`api_database`) utilized by the Cloud Advisor platform.

---

## Database Overview

- **Database Engine**: MySQL 8.0 (InnoDB storage engine)
- **Database Name**: `api_database`
- **Character Set / Collation**: `utf8mb4` / `utf8mb4_0900_ai_ci`
- **Connection Hosts & Ports**:
  - Container Internal: `mysql:3306`
  - Host Machine Exposure: `localhost:3308`
- **Root Password**: `Cloud@123` (configured via Docker Compose `.env`)
- **Initialization Script**: `./mysql/mydb.sql` (mounted into `/docker-entrypoint-initdb.d/`)

---

## Entity Relationship & Table Inventory

`api_database` comprises **7 primary tables**:

| Table Name | Primary Purpose | Record Count (Default Seed) | Key Columns |
| :--- | :--- | :--- | :--- |
| **`users`** | User account credentials and optional provider API key pairs. | 2 records | `id` (PK), `username`, `password` |
| **`aws_costusage`** | Daily AWS billing metrics by service name and usage date. | 74 records | `id` (PK), `service`, `date`, `cost`, `total_cost` |
| **`azureusage`** | Azure cloud usage spending by service name and timestamp. | 12 records | `id` (PK), `ServiceName`, `UsageDate`, `PreTaxCost` |
| **`gcp_costusage`** | GCP service cost breakdowns and daily totals. | 10 records | `id` (PK), `service`, `date`, `cost`, `total_cost` |
| **`book1`** | EC2 benchmark dataset containing instance usage hours, CPU, and memory metrics. | 30 records | `InstanceType`, `HoursUsed`, `CPUUtilization`, `MemoryUtilization` |
| **`costusage`** | Normalized cross-cloud billing table for unified reporting. | 3 records | `NormalizedID` (PK), `ResourceID`, `UnblendedCostAmount` |
| **`gcpusage`** | Reserved schema for raw GCP usage log ingestion. | 0 records | Schema placeholder |

---

## Detailed Table Schemas

### 1. `users` Table
Stores registered application user accounts and optional user-level AWS access keys.

```sql
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(255) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `aws_access_key_id` VARCHAR(255) DEFAULT NULL,
  `aws_secret_access_key` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

#### Field Specifications
| Column Name | Data Type | Nullable | Primary Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INT` | No | Yes | Auto-incrementing unique user identifier. |
| `username` | `VARCHAR(255)` | No | No | Unique account username. |
| `password` | `VARCHAR(255)` | No | No | Password string (plaintext in current dev setup). |
| `aws_access_key_id` | `VARCHAR(255)` | Yes | No | Optional user-specific AWS Access Key ID. |
| `aws_secret_access_key` | `VARCHAR(255)` | Yes | No | Optional user-specific AWS Secret Access Key. |

#### Default Seed Data
- `id=1`: `username='Achal'`, `password='achal'`
- `id=2`: `username='varshini'`, `password='123'`

---

### 2. `aws_costusage` Table
Stores daily AWS cost Explorer metrics with 10 decimal place currency precision.

```sql
CREATE TABLE `aws_costusage` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `service` VARCHAR(255) NOT NULL,
  `service_total` DECIMAL(15,10) NOT NULL,
  `date` DATE NOT NULL,
  `cost` DECIMAL(15,10) NOT NULL,
  `total_cost` DECIMAL(15,10) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=75 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

#### Field Specifications
| Column Name | Data Type | Nullable | Primary Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INT` | No | Yes | Auto-incrementing record ID. |
| `service` | `VARCHAR(255)` | No | No | AWS service name (e.g. `Amazon Elastic Compute Cloud`). |
| `service_total` | `DECIMAL(15,10)` | No | No | Aggregated service cost across all dates. |
| `date` | `DATE` | No | No | Usage date (`YYYY-MM-DD`). |
| `cost` | `DECIMAL(15,10)` | No | No | Daily cost incurred for this specific service. |
| `total_cost` | `DECIMAL(15,10)` | No | No | Cumulative running total cost. |

---

### 3. `azureusage` Table
Stores Azure Cost Management billing records.

```sql
CREATE TABLE `azureusage` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `UsageDate` DATETIME DEFAULT NULL,
  `ServiceName` VARCHAR(255) DEFAULT NULL,
  `PreTaxCost` FLOAT DEFAULT NULL,
  `Currency` VARCHAR(10) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

#### Field Specifications
| Column Name | Data Type | Nullable | Primary Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INT` | No | Yes | Auto-incrementing record ID. |
| `UsageDate` | `DATETIME` | Yes | No | Timestamp of usage event. |
| `ServiceName` | `VARCHAR(255)` | Yes | No | Azure service / resource provider name. |
| `PreTaxCost` | `FLOAT` | Yes | No | Pre-tax spending amount in billing currency. |
| `Currency` | `VARCHAR(10)` | Yes | No | Currency code (e.g. `USD`). |

---

### 4. `gcp_costusage` Table
Stores GCP billing records with 7 decimal place currency precision.

```sql
CREATE TABLE `gcp_costusage` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `service` VARCHAR(255) DEFAULT NULL,
  `service_total` DECIMAL(20,7) DEFAULT NULL,
  `date` DATE DEFAULT NULL,
  `cost` DECIMAL(20,7) DEFAULT NULL,
  `total_cost` DECIMAL(20,7) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

#### Field Specifications
| Column Name | Data Type | Nullable | Primary Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INT` | No | Yes | Auto-incrementing record ID. |
| `service` | `VARCHAR(255)` | Yes | No | GCP service name (e.g. `Compute Engine`). |
| `service_total` | `DECIMAL(20,7)` | Yes | No | Aggregated service spending total. |
| `date` | `DATE` | Yes | No | Usage date (`YYYY-MM-DD`). |
| `cost` | `DECIMAL(20,7)` | Yes | No | Daily cost incurred for the service. |
| `total_cost` | `DECIMAL(20,7)` | Yes | No | Cumulative total cost. |

---

### 5. `book1` Table
Benchmark utilization metrics dataset used for compute right-sizing heuristics.

```sql
CREATE TABLE `book1` (
  `InstanceType` VARCHAR(20) DEFAULT NULL,
  `StartDate` DATE DEFAULT NULL,
  `EndDate` DATE DEFAULT NULL,
  `Region` VARCHAR(50) DEFAULT NULL,
  `HoursUsed` INT DEFAULT NULL,
  `PerUnitCost` DECIMAL(10,2) DEFAULT NULL,
  `TotalCost` DECIMAL(10,2) DEFAULT NULL,
  `CPUUtilization` INT DEFAULT NULL,
  `MemoryUtilization` INT DEFAULT NULL,
  `CPUMax` INT DEFAULT NULL,
  `MaxMemoryUtil` INT DEFAULT NULL,
  `TotalCostSummary` DECIMAL(10,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

### 6. `costusage` Table
Normalized table schema for cross-cloud resource cost aggregation.

```sql
CREATE TABLE `costusage` (
  `NormalizedID` INT NOT NULL,
  `ResourceID` VARCHAR(255) DEFAULT NULL,
  `LaunchTime` DATETIME DEFAULT NULL,
  `AvailabilityZone` VARCHAR(255) DEFAULT NULL,
  `UserID` INT DEFAULT NULL,
  `UserName` VARCHAR(255) DEFAULT NULL,
  `StartDate` DATE DEFAULT NULL,
  `EndDate` DATE DEFAULT NULL,
  `UnblendedCostAmount` DECIMAL(10,2) DEFAULT NULL,
  `UnblendedCostCurrency` VARCHAR(10) DEFAULT NULL,
  `UsageQuantityAmount` DECIMAL(10,8) DEFAULT NULL,
  `UsageQuantityUnit` VARCHAR(50) DEFAULT NULL,
  `InstanceType` VARCHAR(100) DEFAULT NULL,
  `DBInstanceIdentifier` VARCHAR(255) DEFAULT NULL,
  `AllocatedStorage` INT DEFAULT NULL,
  `Engine` VARCHAR(100) DEFAULT NULL,
  `BucketName` VARCHAR(255) DEFAULT NULL,
  `CreationDate` DATE DEFAULT NULL,
  PRIMARY KEY (`NormalizedID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

## SQL Query Registry

### 1. User Authentication (`login.py`)
```sql
SELECT * FROM users 
WHERE username = %s AND password = %s;
```

### 2. Daily Cost Aggregation (`aws.py`, `GCP.py`)
```sql
SELECT date, service, SUM(cost) AS service_cost
FROM aws_costusage 
GROUP BY date, service
ORDER BY date;
```

### 3. Monthly Cost Aggregation (`aws.py`, `azure_script.py`, `GCP.py`)
```sql
SELECT DATE_FORMAT(date, '%Y-%m') AS month, service, SUM(cost) AS service_cost
FROM aws_costusage 
GROUP BY month, service;
```

### 4. Zero-Cost & Unused Resource Query (`unused.py`)
```sql
-- AWS Zero Cost Query
SELECT service, date 
FROM aws_costusage 
WHERE total_cost < 0.000001;

-- Azure Low Cost Query
SELECT ServiceName, UsageDate 
FROM azureusage 
WHERE PreTaxCost <= 3.00;

-- GCP Low Cost Query
SELECT service, date 
FROM gcp_costusage 
WHERE cost <= 10.00;
```

### 5. Upsert Pattern for Cloud Ingestion (`aws.py`, `azure_script.py`, `GCP.py`)
```sql
INSERT INTO aws_costusage (service, service_total, date, cost, total_cost) 
VALUES (%s, %s, %s, %s, %s) 
ON DUPLICATE KEY UPDATE 
cost = VALUES(cost), 
total_cost = VALUES(total_cost);
```
