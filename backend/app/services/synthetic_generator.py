"""
Dynamic AI & Rule-driven Synthetic Cloud Fleet Generator for Retail Enterprises.

Models realistic omnichannel retail workloads across AWS, Azure, and GCP:
- Core E-Commerce Storefront
- Order Management & Logistics (OMS/WMS)
- Customer Service CRM & Call Center Portal
- AI & Big Data Analytics
- Store Edge & Point of Sale (POS) Hybrid Systems
- Core Infrastructure, Networking & Security

Generates diurnal utilization metrics, seasonal spikes (Black Friday / Holidays),
and realistic FinOps waste patterns (unattached disks, idle replicas, oversized VMs).
Supports generating an exact target count per provider (e.g. 100 entries each).
"""

import os
import sys
import json
import math
import random
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

RETAIL_SERVICES_SPEC = {
    "ecommerce_storefront": [
        {"name": "ecom-storefront-web", "rtype": "compute_instance", "sku": {"aws": "m6i.xlarge", "azure": "Standard_D4s_v5", "gcp": "n2-standard-4"}, "base_cost": 140.0, "healthy_cpu": 52.0},
        {"name": "ecom-cart-checkout-api", "rtype": "compute_instance", "sku": {"aws": "c6i.2xlarge", "azure": "Standard_F8s_v2", "gcp": "c2-standard-8"}, "base_cost": 280.0, "healthy_cpu": 65.0},
        {"name": "ecom-mobile-api-gateway", "rtype": "compute_instance", "sku": {"aws": "m6i.large", "azure": "Standard_D2s_v5", "gcp": "n2-standard-2"}, "base_cost": 96.0, "healthy_cpu": 44.0},
        {"name": "ecom-session-cache", "rtype": "cache_cluster", "sku": {"aws": "cache.r6g.large", "azure": "Premium_P1", "gcp": "standard-ha-16"}, "base_cost": 210.0, "healthy_cpu": 22.0},
        {"name": "ecom-product-catalog-db", "rtype": "nosql_table", "sku": {"aws": "DynamoDB-OnDemand", "azure": "CosmosDB-Session", "gcp": "Cloud-Bigtable-SSD"}, "base_cost": 450.0, "healthy_cpu": 15.0},
        {"name": "ecom-cdn-distribution", "rtype": "cdn_distribution", "sku": {"aws": "CloudFront-Global", "azure": "AzureFrontDoor-Premium", "gcp": "Cloud-CDN-Static"}, "base_cost": 320.0, "healthy_cpu": 0.0},
        {"name": "ecom-public-app-alb", "rtype": "load_balancer", "sku": {"aws": "ApplicationLoadBalancer", "azure": "AppGateway-v2", "gcp": "Global-HTTPS-LB"}, "base_cost": 45.0, "healthy_cpu": 38.0},
        {"name": "ecom-search-opensearch", "rtype": "search_domain", "sku": {"aws": "OpenSearch-r6g.large", "azure": "Azure-AI-Search-Standard", "gcp": "Vertex-AI-Search"}, "base_cost": 380.0, "healthy_cpu": 41.0},
        {"name": "ecom-perimeter-waf", "rtype": "web_acl", "sku": {"aws": "AWS-WAF-Regional", "azure": "Azure-WAF-Policy", "gcp": "Cloud-Armor-Enterprise"}, "base_cost": 65.0, "healthy_cpu": 0.0},
    ],
    "order_management": [
        {"name": "oms-order-router-worker", "rtype": "compute_instance", "sku": {"aws": "m6i.large", "azure": "Standard_D2s_v5", "gcp": "n2-standard-2"}, "base_cost": 96.0, "healthy_cpu": 45.0},
        {"name": "oms-inventory-allocation-engine", "rtype": "compute_instance", "sku": {"aws": "c6i.xlarge", "azure": "Standard_F4s_v2", "gcp": "c2-standard-4"}, "base_cost": 185.0, "healthy_cpu": 58.0},
        {"name": "oms-primary-transaction-db", "rtype": "database", "sku": {"aws": "db.r6g.2xlarge", "azure": "BusinessCritical_80vc", "gcp": "db-custom-32-131072"}, "base_cost": 1250.0, "healthy_cpu": 62.0},
        {"name": "oms-events-streaming-hub", "rtype": "event_stream", "sku": {"aws": "Kinesis-4Shards", "azure": "EventHub-Premium", "gcp": "PubSub-Dedicated"}, "base_cost": 380.0, "healthy_cpu": 0.0},
        {"name": "oms-invoice-archive-bucket", "rtype": "object_storage", "sku": {"aws": "S3-Standard", "azure": "Blob-Hot-GRS", "gcp": "GCS-Standard"}, "base_cost": 280.0, "healthy_cpu": 0.0},
        {"name": "oms-fulfillment-dispatch-worker", "rtype": "compute_instance", "sku": {"aws": "m6i.large", "azure": "Standard_D2s_v5", "gcp": "n2-standard-2"}, "base_cost": 96.0, "healthy_cpu": 48.0},
        {"name": "oms-carrier-integration-api", "rtype": "compute_instance", "sku": {"aws": "t3.xlarge", "azure": "Standard_B4ms", "gcp": "e2-standard-4"}, "base_cost": 120.0, "healthy_cpu": 35.0},
        {"name": "oms-async-message-queue", "rtype": "message_topic", "sku": {"aws": "SQS-FIFO", "azure": "ServiceBus-Standard", "gcp": "PubSub-Standard"}, "base_cost": 42.0, "healthy_cpu": 0.0},
    ],
    "customer_service_crm": [
        {"name": "crm-agent-portal-api", "rtype": "compute_instance", "sku": {"aws": "m6i.xlarge", "azure": "Standard_D4s_v5", "gcp": "n2-standard-4"}, "base_cost": 140.0, "healthy_cpu": 35.0},
        {"name": "crm-telephony-screenpop-service", "rtype": "compute_instance", "sku": {"aws": "m6i.large", "azure": "Standard_D2s_v5", "gcp": "n2-standard-2"}, "base_cost": 96.0, "healthy_cpu": 28.0},
        {"name": "crm-callcenter-read-replica", "rtype": "database", "sku": {"aws": "db.r6g.xlarge", "azure": "BusinessCritical_16vc", "gcp": "db-custom-16-65536"}, "base_cost": 750.0, "healthy_cpu": 25.0},
        {"name": "crm-call-audio-recordings-store", "rtype": "object_storage", "sku": {"aws": "S3-Standard", "azure": "Blob-Hot-GRS", "gcp": "GCS-Standard"}, "base_cost": 720.0, "healthy_cpu": 0.0},
        {"name": "crm-speech-to-text-processor", "rtype": "compute_instance", "sku": {"aws": "c6i.2xlarge", "azure": "Standard_F8s_v2", "gcp": "c2-standard-8"}, "base_cost": 290.0, "healthy_cpu": 54.0},
        {"name": "crm-loyalty-rewards-service", "rtype": "compute_instance", "sku": {"aws": "t3.large", "azure": "Standard_B2ms", "gcp": "e2-standard-2"}, "base_cost": 72.0, "healthy_cpu": 32.0},
    ],
    "ai_and_analytics": [
        {"name": "retail-ai-associate-copilot", "rtype": "ai_platform", "sku": {"aws": "Bedrock-Claude", "azure": "AzureOpenAI-PTU", "gcp": "VertexAI-Gemini"}, "base_cost": 3400.0, "healthy_cpu": 45.0},
        {"name": "retail-enterprise-data-warehouse", "rtype": "data_warehouse", "sku": {"aws": "Redshift-RA3", "azure": "Synapse-DW3000c", "gcp": "BigQuery-Enterprise"}, "base_cost": 2800.0, "healthy_cpu": 18.0},
        {"name": "supplychain-analytics-databricks", "rtype": "data_platform", "sku": {"aws": "EMR-Cluster", "azure": "Databricks-Premium", "gcp": "Dataproc-HA"}, "base_cost": 2200.0, "healthy_cpu": 25.0},
        {"name": "realtime-fraud-detection-model", "rtype": "ml_endpoint", "sku": {"aws": "SageMaker-Endpoint", "azure": "AzureML-OnlineEndpoint", "gcp": "VertexAI-Endpoint"}, "base_cost": 950.0, "healthy_cpu": 62.0},
        {"name": "customer-clickstream-etl", "rtype": "etl_job", "sku": {"aws": "AWS-Glue-Worker", "azure": "Azure-Data-Factory", "gcp": "Cloud-Dataflow-Batch"}, "base_cost": 410.0, "healthy_cpu": 50.0},
    ],
    "store_edge_and_pos": [
        {"name": "pos-terminal-sync-gateway", "rtype": "compute_instance", "sku": {"aws": "m6i.large", "azure": "Standard_D2s_v5", "gcp": "n2-standard-2"}, "base_cost": 96.0, "healthy_cpu": 42.0},
        {"name": "store-inventory-cache-relay", "rtype": "cache_cluster", "sku": {"aws": "cache.t4g.medium", "azure": "Standard_C1", "gcp": "standard-ha-4"}, "base_cost": 75.0, "healthy_cpu": 28.0},
        {"name": "digital-price-tag-event-broker", "rtype": "message_topic", "sku": {"aws": "SNS-Topic", "azure": "EventGrid-Topic", "gcp": "PubSub-Topic"}, "base_cost": 35.0, "healthy_cpu": 0.0},
        {"name": "barcode-scanner-ingest-api", "rtype": "compute_instance", "sku": {"aws": "c6i.large", "azure": "Standard_F2s_v2", "gcp": "c2-standard-4"}, "base_cost": 105.0, "healthy_cpu": 39.0},
    ],
    "infrastructure_and_network": [
        {"name": "prod-vpc-nat-gateway", "rtype": "nat_gateway", "sku": {"aws": "NAT-Gateway", "azure": "VNet-NAT-Gateway", "gcp": "Cloud-NAT-Gateway"}, "base_cost": 125.0, "healthy_cpu": 0.0},
        {"name": "enterprise-secrets-vault", "rtype": "key_vault", "sku": {"aws": "AWS-KMS-HSM", "azure": "Azure-Key-Vault-Premium", "gcp": "Cloud-KMS-CryptoKey"}, "base_cost": 85.0, "healthy_cpu": 0.0},
        {"name": "container-artifact-registry", "rtype": "container_registry", "sku": {"aws": "ECR-Private", "azure": "ACR-Premium", "gcp": "Artifact-Registry"}, "base_cost": 45.0, "healthy_cpu": 0.0},
        {"name": "central-audit-log-group", "rtype": "log_group", "sku": {"aws": "CloudWatch-Logs", "azure": "Log-Analytics-Workspace", "gcp": "Cloud-Logging-Bucket"}, "base_cost": 180.0, "healthy_cpu": 0.0},
        {"name": "hybrid-direct-connect-gateway", "rtype": "virtual_network", "sku": {"aws": "DirectConnect-VGW", "azure": "ExpressRoute-Gateway", "gcp": "Cloud-Interconnect-VLAN"}, "base_cost": 310.0, "healthy_cpu": 0.0},
    ]
}

WASTE_SCENARIOS = [
    {
        "type": "underutilized_vm",
        "name_suffix": "-staging-worker",
        "rtype": "compute_instance",
        "cpu_range": (2.1, 7.8),
        "cost_multiplier": 1.35,
        "explanation": "Staging worker provisioned for QA release testing running 24/7 at low average CPU."
    },
    {
        "type": "idle_compute_instance",
        "name_suffix": "-dev-sandbox-node",
        "rtype": "compute_instance",
        "cpu_range": (0.2, 1.9),
        "cost_multiplier": 1.15,
        "explanation": "Developer test VM left active with zero meaningful workload; prime candidate for auto-stop."
    },
    {
        "type": "unattached_disk",
        "name_suffix": "-unattached-legacy-disk",
        "rtype": "block_storage",
        "cpu_range": (0.0, 0.0),
        "cost_fixed": 95.0,
        "explanation": "Detached high-performance storage volume retained after decommissioning a batch worker."
    },
    {
        "type": "idle_database_replica",
        "name_suffix": "-read-replica-oversized",
        "rtype": "database",
        "cpu_range": (3.5, 7.4),
        "cost_multiplier": 1.25,
        "explanation": "Dedicated call center read replica sized identically to writer; off-peak shifts register <8% CPU."
    },
    {
        "type": "unassociated_ip",
        "name_suffix": "-orphaned-public-ip",
        "rtype": "public_ip",
        "cpu_range": (0.0, 0.0),
        "cost_fixed": 7.30,
        "explanation": "Static external IP address reserved for a decommissioned partner API gateway accumulating idle charges."
    },
    {
        "type": "legacy_generation_instance",
        "name_suffix": "-legacy-gen-host",
        "rtype": "compute_instance",
        "cpu_range": (14.0, 28.0),
        "cost_multiplier": 1.45,
        "explanation": "Older generation compute instance (e.g. m4/c4) operating at 20% higher price-to-performance ratio."
    },
    {
        "type": "unexpired_log_group",
        "name_suffix": "-debug-logs-unbounded",
        "rtype": "log_group",
        "cpu_range": (0.0, 0.0),
        "cost_fixed": 62.0,
        "explanation": "Application debug log group with retention set to 'Never Expire', accumulating continuous storage costs."
    },
    {
        "type": "overprovisioned_cache",
        "name_suffix": "-oversized-memcache",
        "rtype": "cache_cluster",
        "cpu_range": (4.0, 9.5),
        "cost_multiplier": 1.30,
        "explanation": "Multi-gigabyte cache cluster with memory utilization consistently under 10%."
    }
]

PROVIDER_REGIONS = {
    "aws": ["us-east-1", "us-east-2", "us-west-2"],
    "azure": ["eastus2", "centralus", "westus3"],
    "gcp": ["us-central1", "us-east4", "us-west1"]
}

PROVIDER_ACCOUNTS = {
    "aws": {"id": "412907386215", "name": "retail-aws-prod-4102"},
    "azure": {"id": "sub-c8b14e91-72a3", "name": "retail-azure-prod-4102"},
    "gcp": {"id": "prj-retail-omni-prod", "name": "retail-gcp-prod-4102"}
}


class DynamicRetailFleetGenerator:
    """
    Generates dynamic multi-cloud retail fleet datasets with realistic diurnal curves,
    tag hierarchies, and intentional FinOps optimization opportunities.
    """

    @classmethod
    def generate_fleet(
        cls,
        user_id: str = "demo_retail_user",
        providers: Optional[List[str]] = None,
        count_per_provider: int = 100,
        scale_multiplier: float = 1.0,
        include_waste: bool = True,
        season: str = "holiday_surge",
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates realistic enterprise retail resources across AWS, Azure, and GCP.
        Ensures exactly `count_per_provider` resources per platform.
        """
        if seed is not None:
            random.seed(seed)

        if not providers:
            providers = ["aws", "azure", "gcp"]

        now = datetime.now(timezone.utc)
        generated_resources: List[Dict[str, Any]] = []
        season_boost = 1.45 if season == "holiday_surge" else 1.0

        # Collect flat pool of service specs
        flat_service_specs = []
        for domain, services in RETAIL_SERVICES_SPEC.items():
            for svc in services:
                flat_service_specs.append((domain, svc))

        for prov in providers:
            prov_lower = prov.lower()
            prov_regions = PROVIDER_REGIONS.get(prov_lower, ["us-east-1"])
            prov_account = PROVIDER_ACCOUNTS.get(prov_lower, {"id": f"acc-{prov_lower}", "name": f"retail-{prov_lower}"})

            # Determine healthy vs waste split (e.g. ~82 healthy, ~18 waste for 100 count)
            waste_count = int(count_per_provider * 0.18) if include_waste else 0
            healthy_count = count_per_provider - waste_count

            # 1. Generate Healthy Enterprise Resources
            for i in range(healthy_count):
                domain, svc = flat_service_specs[i % len(flat_service_specs)]
                instance_index = (i // len(flat_service_specs)) + 1

                sku_name = svc["sku"].get(prov_lower, "Standard_Tier")
                base_monthly = svc["base_cost"] * scale_multiplier * season_boost
                fluctuation = random.uniform(0.92, 1.15)
                monthly_cost = round(base_monthly * fluctuation, 2)

                avg_cpu = round(svc["healthy_cpu"] * random.uniform(0.85, 1.10), 1) if svc["healthy_cpu"] > 0 else 0.0
                p95_cpu = round(min(avg_cpu * random.uniform(1.25, 1.55), 98.5), 1) if avg_cpu > 0 else 0.0
                avg_mem = round(avg_cpu * 1.25 + 15.0, 1) if avg_cpu > 0 else round(random.uniform(20.0, 45.0), 1)
                p95_mem = round(min(avg_mem * 1.2 + 8.0, 95.0), 1)

                res_region = prov_regions[i % len(prov_regions)]
                res_suffix = f"{i+1:03d}"
                res_id = f"{prov_lower}-{svc['rtype'][:3]}-{svc['name']}-{res_suffix}"

                env_tag = "production" if instance_index == 1 else "staging" if instance_index == 2 else "production"

                resource_doc = {
                    "user_id": user_id,
                    "cloud_account_id": f"ca_{prov_lower}_retail",
                    "provider": prov_lower,
                    "account_id": prov_account["id"],
                    "resource_id": res_id,
                    "resource_type": svc["rtype"],
                    "region": res_region,
                    "name": f"{svc['name']}-{prov_lower}-{res_suffix}",
                    "configuration": {
                        "sku": sku_name,
                        "instance_type": sku_name,
                        "domain": domain,
                        "state": "running" if svc["rtype"] in ["compute_instance", "database"] else "active",
                        "retention_days": 90 if svc["rtype"] == "log_group" else None,
                        "tier": "Standard"
                    },
                    "tags": {
                        "Environment": env_tag,
                        "Application": domain.replace("_", "-").title(),
                        "BusinessUnit": "Retail-Omnichannel",
                        "CostCenter": "CC-RETAIL-4102",
                        "Owner": f"{domain}-lead@retailcorp.com"
                    },
                    "metrics": {
                        "cpu_average": avg_cpu,
                        "cpu_p95": p95_cpu,
                        "memory_average": avg_mem,
                        "memory_p95": p95_mem
                    },
                    "cost": {
                        "monthly": monthly_cost,
                        "currency": "USD"
                    },
                    "last_synced_at": now.isoformat()
                }
                generated_resources.append(resource_doc)

            # 2. Generate Realistic FinOps Waste / Optimization Candidates
            for w_idx in range(waste_count):
                waste = WASTE_SCENARIOS[w_idx % len(WASTE_SCENARIOS)]
                w_num = w_idx + 1
                res_region = prov_regions[w_idx % len(prov_regions)]
                waste_res_id = f"{prov_lower}-waste-{waste['type'][:6]}-{w_num:03d}"

                cpu_val = round(random.uniform(*waste["cpu_range"]), 1)
                cost_val = waste.get("cost_fixed") or round(220.0 * waste.get("cost_multiplier", 1.0) * random.uniform(0.9, 1.1), 2)
                p95_cpu = round(cpu_val * random.uniform(1.3, 1.7), 1) if cpu_val > 0 else 0.0

                config_doc: Dict[str, Any] = {
                    "sku": "Standard",
                    "state": "available" if waste["rtype"] == "block_storage" else "unassociated" if waste["rtype"] == "public_ip" else "running",
                    "waste_type": waste["type"],
                    "explanation": waste["explanation"]
                }

                if waste["type"] == "unattached_disk":
                    config_doc["volume_type"] = "gp2" if prov_lower == "aws" else "Premium_LRS" if prov_lower == "azure" else "pd-standard"
                    config_doc["attachment_state"] = "unattached"
                    config_doc["size_gb"] = random.choice([250, 500, 1000])
                elif waste["type"] == "unexpired_log_group":
                    config_doc["retention_days"] = 0
                elif waste["type"] == "legacy_generation_instance":
                    legacy_skus = {"aws": "m4.xlarge", "azure": "Standard_D3_v2", "gcp": "n1-standard-4"}
                    config_doc["sku"] = legacy_skus.get(prov_lower, "legacy-standard")
                    config_doc["instance_type"] = config_doc["sku"]

                waste_doc = {
                    "user_id": user_id,
                    "cloud_account_id": f"ca_{prov_lower}_retail",
                    "provider": prov_lower,
                    "account_id": prov_account["id"],
                    "resource_id": waste_res_id,
                    "resource_type": waste["rtype"],
                    "region": res_region,
                    "name": f"{waste['type'].replace('_', '-')}{waste['name_suffix']}-{prov_lower}-{w_num:02d}",
                    "configuration": config_doc,
                    "tags": {
                        "Environment": "staging" if "staging" in waste["name_suffix"] else "dev" if "dev" in waste["name_suffix"] else "legacy",
                        "Application": "Omnichannel-Ops",
                        "BusinessUnit": "Retail-Omnichannel",
                        "CostCenter": "CC-RETAIL-9999",
                        "Owner": "finops-remediation@retailcorp.com"
                    },
                    "metrics": {
                        "cpu_average": cpu_val,
                        "cpu_p95": p95_cpu,
                        "memory_average": round(cpu_val * 1.4 + 5.0, 1) if cpu_val > 0 else 0.0,
                        "memory_p95": round(p95_cpu * 1.5 + 8.0, 1) if p95_cpu > 0 else 0.0
                    },
                    "cost": {
                        "monthly": cost_val,
                        "currency": "USD"
                    },
                    "last_synced_at": now.isoformat()
                }
                generated_resources.append(waste_doc)

        return generated_resources


def print_fleet_summary(resources: List[Dict[str, Any]]):
    """Prints a structured summary table of generated resources by provider."""
    from collections import defaultdict

    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "count": 0,
        "total_cost": 0.0,
        "waste_count": 0,
        "types": defaultdict(int),
        "envs": defaultdict(int)
    })

    for r in resources:
        p = r["provider"]
        stats[p]["count"] += 1
        stats[p]["total_cost"] += r["cost"]["monthly"]
        stats[p]["types"][r["resource_type"]] += 1
        env = r.get("tags", {}).get("Environment", "unknown")
        stats[p]["envs"][env] += 1
        if "waste" in r.get("resource_id", "") or r.get("configuration", {}).get("waste_type"):
            stats[p]["waste_count"] += 1

    print("\n" + "=" * 80)
    print("  DYNAMIC RETAIL MULTI-CLOUD SYNTHETIC FLEET GENERATION SUMMARY")
    print("=" * 80)
    print(f"{'Provider':<10} | {'Entries':<8} | {'Monthly Cost':<14} | {'Waste Items':<12} | {'Top Resource Types'}")
    print("-" * 80)

    total_count = 0
    total_cost = 0.0
    total_waste = 0.0

    for prov in sorted(stats.keys()):
        d = stats[prov]
        total_count += d["count"]
        total_cost += d["total_cost"]
        total_waste += d["waste_count"]
        top_types = ", ".join([f"{k}({v})" for k, v in sorted(d["types"].items(), key=lambda x: -x[1])[:3]])
        print(f"{prov.upper():<10} | {d['count']:<8} | ${d['total_cost']:>12,.2f} | {d['waste_count']:<12} | {top_types}")

    print("-" * 80)
    print(f"{'TOTAL':<10} | {total_count:<8} | ${total_cost:>12,.2f} | {total_waste:<12} | Across {len(stats)} platforms")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic retail fleet data for AWS, Azure, and GCP.")
    parser.add_argument("--count", type=int, default=100, help="Number of resources per provider (default: 100)")
    parser.add_argument("--providers", type=str, default="aws,azure,gcp", help="Comma-separated providers (default: aws,azure,gcp)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON filepath (default: synthetic data/demo_retail_100_per_platform.json)")
    parser.add_argument("--user-id", type=str, default="demo_retail_user", help="User ID for resources (default: demo_retail_user)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible generation (default: 42)")

    args = parser.parse_args()

    target_providers = [p.strip().lower() for p in args.providers.split(",") if p.strip()]

    fleet = DynamicRetailFleetGenerator.generate_fleet(
        user_id=args.user_id,
        providers=target_providers,
        count_per_provider=args.count,
        seed=args.seed
    )

    print_fleet_summary(fleet)

    # Resolve output path
    if args.output:
        out_path = args.output
    else:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        out_dir = os.path.join(repo_root, "synthetic data")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"demo_retail_{args.count}_per_platform.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fleet, f, indent=2)

    print(f"[SUCCESS] Saved {len(fleet)} resources to: {os.path.abspath(out_path)}")
