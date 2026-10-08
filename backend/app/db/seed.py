import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_seed")

async def seed_database_instance(db):
    logger.info("Seeding database collections...")

    now = datetime.now(timezone.utc)

    # 1. Seed Users
    demo_user = {
        "email": "jordan@acme.io",
        "password_hash": get_password_hash("password123"),
        "name": "Jordan Davis",
        "created_at": now,
        "updated_at": now
    }
    admin_user = {
        "email": "achal@acme.io",
        "password_hash": get_password_hash("achal"),
        "name": "Achal",
        "created_at": now,
        "updated_at": now
    }

    res_user = await db.users.update_one(
        {"email": demo_user["email"]},
        {"$set": demo_user},
        upsert=True
    )
    await db.users.update_one(
        {"email": admin_user["email"]},
        {"$set": admin_user},
        upsert=True
    )

    user_doc = await db.users.find_one({"email": "jordan@acme.io"})
    user_id = str(user_doc["_id"])
    logger.info(f"Seeded users. Demo User ID: {user_id}")

    # 2. Seed Cloud Accounts
    accounts = [
        {
            "user_id": user_id,
            "provider": "aws",
            "display_name": "Production AWS Account",
            "status": "connected",
            "account_identifier": "123456789012",
            "region": "us-east-1",
            "credential_type": "assume_role",
            "provider_config": {
                "role_arn": "arn:aws:iam::123456789012:role/CloudAdvisorReadOnly",
                "external_id": "ca-ext-9988"
            },
            "last_verified_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "provider": "azure",
            "display_name": "Analytics Azure Subscription",
            "status": "connected",
            "account_identifier": "00000000-0000-0000-0000-000000000000",
            "region": "westeurope",
            "credential_type": "client_secret",
            "provider_config": {
                "azure_tenant_id": "11111111-1111-1111-1111-111111111111",
                "azure_client_id": "22222222-2222-2222-2222-222222222222"
            },
            "last_verified_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "provider": "gcp",
            "display_name": "Data Platform GCP Project",
            "status": "connected",
            "account_identifier": "acme-data-prod",
            "region": "us-central1",
            "credential_type": "service_account",
            "provider_config": {
                "gcp_project_id": "acme-data-prod"
            },
            "last_verified_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]

    account_ids = {}
    for acc in accounts:
        await db.cloud_accounts.update_one(
            {"user_id": user_id, "provider": acc["provider"], "account_identifier": acc["account_identifier"]},
            {"$set": acc},
            upsert=True
        )
        saved_acc = await db.cloud_accounts.find_one({
            "user_id": user_id,
            "provider": acc["provider"],
            "account_identifier": acc["account_identifier"]
        })
        account_ids[acc["provider"]] = str(saved_acc["_id"])

    logger.info(f"Seeded cloud accounts: {list(account_ids.keys())}")

    # 3. Seed Rules
    rules = [
        {
            "rule_id": "AWS-EC2-001",
            "name": "Underutilized EC2 Instance",
            "description": "EC2 instance running with average CPU utilization below 20% over 14 days.",
            "provider": "aws",
            "resource_type": "compute_instance",
            "required_data": ["metrics.cpu_average", "cost.monthly"],
            "lookback_window": {"value": 14, "unit": "days"},
            "conditions": {
                "logic": "AND",
                "items": [{"field": "metrics.cpu_average", "operator": "lt", "threshold": 20.0}]
            },
            "recommendation": {
                "type": "RIGHTSIZING_REVIEW",
                "action_template": "Downsize EC2 instance from m5.2xlarge to m5.xlarge."
            },
            "savings_calculation": {"type": "ESTIMATED_PERCENTAGE", "percentage": 50.0},
            "severity": "high",
            "status": "active",
            "provenance": "DERIVED"
        },
        {
            "rule_id": "AZURE-VM-001",
            "name": "Underutilized Azure Virtual Machine",
            "description": "Azure VM CPU utilization is below 15% over a 14-day window.",
            "provider": "azure",
            "resource_type": "compute_instance",
            "required_data": ["metrics.cpu_average"],
            "lookback_window": {"value": 14, "unit": "days"},
            "conditions": {
                "logic": "AND",
                "items": [{"field": "metrics.cpu_average", "operator": "lt", "threshold": 15.0}]
            },
            "recommendation": {
                "type": "RIGHTSIZING_REVIEW",
                "action_template": "Move to smaller SKU D4s v5 after testing peak loads."
            },
            "savings_calculation": {"type": "ESTIMATED_PERCENTAGE", "percentage": 45.0},
            "severity": "high",
            "status": "active",
            "provenance": "DERIVED"
        },
        {
            "rule_id": "AZURE-DISK-001",
            "name": "Unattached Azure Managed Disk",
            "description": "Managed disk is unattached to any VM over 30 days.",
            "provider": "azure",
            "resource_type": "storage_volume",
            "required_data": ["configuration.state"],
            "lookback_window": {"value": 30, "unit": "days"},
            "conditions": {
                "logic": "AND",
                "items": [{"field": "configuration.state", "operator": "eq", "threshold": "unattached"}]
            },
            "recommendation": {
                "type": "DELETE_RESOURCE",
                "action_template": "Verify snapshot coverage and delete unattached managed disk."
            },
            "savings_calculation": {"type": "ZERO_UTILIZATION"},
            "severity": "high",
            "status": "active",
            "provenance": "DERIVED"
        },
        {
            "rule_id": "GCP-GCE-001",
            "name": "Underutilized Compute Engine Instance",
            "description": "GCP Compute Engine instance average CPU is below 10%.",
            "provider": "gcp",
            "resource_type": "compute_instance",
            "required_data": ["metrics.cpu_average"],
            "lookback_window": {"value": 14, "unit": "days"},
            "conditions": {
                "logic": "AND",
                "items": [{"field": "metrics.cpu_average", "operator": "lt", "threshold": 10.0}]
            },
            "recommendation": {
                "type": "RIGHTSIZING_REVIEW",
                "action_template": "Adjust machine type from n2-standard-8 to n2-standard-4."
            },
            "savings_calculation": {"type": "ESTIMATED_PERCENTAGE", "percentage": 45.0},
            "severity": "high",
            "status": "active",
            "provenance": "DERIVED"
        }
    ]

    for rule in rules:
        await db.rules.update_one(
            {"rule_id": rule["rule_id"]},
            {"$set": rule},
            upsert=True
        )
    logger.info("Seeded default rules into Rule Registry.")

    # 4. Seed Resources
    resources = [
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["aws"],
            "provider": "aws",
            "account_id": "123456789012",
            "resource_type": "compute_instance",
            "resource_id": "i-0a1b2c3d4e5f67890",
            "region": "us-east-1",
            "name": "prod-api-worker-03",
            "configuration": {"instance_type": "m5.2xlarge", "state": "running"},
            "tags": {"Environment": "Production", "Team": "Backend"},
            "metrics": {"cpu_average": 4.8, "cpu_p95": 11.3, "memory_average": 11.3, "memory_p95": 18.2},
            "cost": {"monthly": 112.50, "currency": "USD"},
            "last_synced_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["azure"],
            "provider": "azure",
            "account_id": "00000000-0000-0000-0000-000000000000",
            "resource_type": "compute_instance",
            "resource_id": "analytics-node-01",
            "region": "westeurope",
            "name": "analytics-node-01",
            "configuration": {"instance_type": "D8s v5", "state": "running"},
            "tags": {"Environment": "Production", "Team": "Analytics"},
            "metrics": {"cpu_average": 12.4, "cpu_p95": 24.1, "memory_average": 23.1, "memory_p95": 35.0},
            "cost": {"monthly": 386.00, "currency": "USD"},
            "last_synced_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["azure"],
            "provider": "azure",
            "account_id": "00000000-0000-0000-0000-000000000000",
            "resource_type": "storage_volume",
            "resource_id": "orphaned-disks-westeurope",
            "region": "westeurope",
            "name": "orphaned-disks-westeurope",
            "configuration": {"size_gb": 100, "state": "unattached"},
            "tags": {"Environment": "Staging"},
            "metrics": {"cpu_average": 0.0, "cpu_p95": 0.0},
            "cost": {"monthly": 94.00, "currency": "USD"},
            "last_synced_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["gcp"],
            "provider": "gcp",
            "account_id": "acme-data-prod",
            "resource_type": "compute_instance",
            "resource_id": "batch-processor-eu",
            "region": "us-central1",
            "name": "batch-processor-eu",
            "configuration": {"instance_type": "n2-standard-8", "state": "RUNNING"},
            "tags": {"Environment": "Production"},
            "metrics": {"cpu_average": 8.2, "cpu_p95": 16.5, "memory_average": 18.6, "memory_p95": 28.0},
            "cost": {"monthly": 294.00, "currency": "USD"},
            "last_synced_at": datetime.utcnow()
        }
    ]

    for res in resources:
        await db.resources.update_one(
            {"user_id": user_id, "provider": res["provider"], "resource_id": res["resource_id"]},
            {"$set": res},
            upsert=True
        )
    logger.info("Seeded resources collection.")

    # 5. Seed Findings
    findings = [
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["aws"],
            "rule_id": "AWS-EC2-001",
            "resource_id": "i-0a1b2c3d4e5f67890",
            "resource_name": "prod-api-worker-03",
            "provider": "aws",
            "severity": "high",
            "status": "open",
            "evidence": {
                "rule_id": "AWS-EC2-001",
                "rule_name": "Underutilized EC2 Instance",
                "lookback_period": "14 days",
                "monthly_cost": 112.50,
                "currency": "USD",
                "explanation": "Resource 'prod-api-worker-03' CPU average (4.8%) is below threshold 20.0%."
            },
            "recommendation": {
                "type": "RIGHTSIZING_REVIEW",
                "action_template": "Downsize EC2 instance from m5.2xlarge to m5.xlarge."
            },
            "savings": {
                "monthly": 56.25,
                "annual": 675.00,
                "currency": "USD",
                "type": "ESTIMATED"
            },
            "source": "Cloud Advisor Rule Engine",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["azure"],
            "rule_id": "AZURE-VM-001",
            "resource_id": "analytics-node-01",
            "resource_name": "analytics-node-01",
            "provider": "azure",
            "severity": "high",
            "status": "open",
            "evidence": {
                "rule_id": "AZURE-VM-001",
                "rule_name": "Underutilized Azure Virtual Machine",
                "lookback_period": "14 days",
                "monthly_cost": 386.00,
                "currency": "USD",
                "explanation": "Resource 'analytics-node-01' CPU average (12.4%) is below threshold 15.0%."
            },
            "recommendation": {
                "type": "RIGHTSIZING_REVIEW",
                "action_template": "Move to smaller SKU D4s v5 after testing peak loads."
            },
            "savings": {
                "monthly": 173.70,
                "annual": 2084.40,
                "currency": "USD",
                "type": "ESTIMATED"
            },
            "source": "Cloud Advisor Rule Engine",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["azure"],
            "rule_id": "AZURE-DISK-001",
            "resource_id": "orphaned-disks-westeurope",
            "resource_name": "orphaned-disks-westeurope",
            "provider": "azure",
            "severity": "high",
            "status": "open",
            "evidence": {
                "rule_id": "AZURE-DISK-001",
                "rule_name": "Unattached Azure Managed Disk",
                "lookback_period": "30 days",
                "monthly_cost": 94.00,
                "currency": "USD",
                "explanation": "Managed disk state is unattached."
            },
            "recommendation": {
                "type": "DELETE_RESOURCE",
                "action_template": "Verify snapshot coverage and delete unattached managed disk."
            },
            "savings": {
                "monthly": 94.00,
                "annual": 1128.00,
                "currency": "USD",
                "type": "ZERO_UTILIZATION"
            },
            "source": "Cloud Advisor Rule Engine",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "user_id": user_id,
            "cloud_account_id": account_ids["gcp"],
            "rule_id": "GCP-GCE-001",
            "resource_id": "batch-processor-eu",
            "resource_name": "batch-processor-eu",
            "provider": "gcp",
            "severity": "high",
            "status": "open",
            "evidence": {
                "rule_id": "GCP-GCE-001",
                "rule_name": "Underutilized Compute Engine Instance",
                "lookback_period": "14 days",
                "monthly_cost": 294.00,
                "currency": "USD",
                "explanation": "Compute Engine instance CPU average (8.2%) is below threshold 10.0%."
            },
            "recommendation": {
                "type": "RIGHTSIZING_REVIEW",
                "action_template": "Adjust machine type from n2-standard-8 to n2-standard-4."
            },
            "savings": {
                "monthly": 132.30,
                "annual": 1587.60,
                "currency": "USD",
                "type": "ESTIMATED"
            },
            "source": "Cloud Advisor Rule Engine",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]

    for finding in findings:
        await db.findings.update_one(
            {"user_id": user_id, "resource_id": finding["resource_id"], "rule_id": finding["rule_id"]},
            {"$set": finding},
            upsert=True
        )
    logger.info("Seeded findings collection.")
    logger.info("Database seeding completed successfully!")

async def seed_database():
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
        await client.admin.command('ping')
        db = client[settings.MONGODB_DATABASE]
        await seed_database_instance(db)
        client.close()
    except Exception as e:
        logger.warning(f"Live Mongo connection failed ({e}). Seeding with AsyncMongoMockClient...")
        from mongomock_motor import AsyncMongoMockClient
        client = AsyncMongoMockClient()
        db = client[settings.MONGODB_DATABASE]
        await seed_database_instance(db)

if __name__ == "__main__":
    asyncio.run(seed_database())
