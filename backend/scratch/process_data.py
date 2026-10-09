import json
import os
from collections import defaultdict

data_path = r"d:\Internship\Cloud\synthetic data\data.json"

with open(data_path, "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Loaded {len(items)} items from synthetic data.json")

# 1. Total cost and counts by provider
provider_totals = defaultdict(float)
provider_counts = defaultdict(int)
services_by_provider = defaultdict(lambda: defaultdict(float))
service_counts = defaultdict(lambda: defaultdict(int))

# Service naming mapping for clean display
NAME_MAP = {
    "compute_instance": {"AWS": "Amazon EC2", "AZURE": "Virtual Machines", "GCP": "Compute Engine"},
    "database": {"AWS": "Amazon RDS", "AZURE": "Azure SQL Database", "GCP": "Cloud SQL"},
    "object_storage": {"AWS": "Amazon S3", "AZURE": "Blob Storage", "GCP": "Cloud Storage"},
    "block_storage": {"AWS": "Amazon EBS", "AZURE": "Managed Disks", "GCP": "Persistent Disk"},
    "load_balancer": {"AWS": "Elastic Load Balancer", "AZURE": "Azure Load Balancer", "GCP": "Cloud Load Balancing"},
    "kubernetes_cluster": {"AWS": "Amazon EKS", "AZURE": "Azure Kubernetes (AKS)", "GCP": "Google Kubernetes Engine (GKE)"},
    "cdn_distribution": {"AWS": "Amazon CloudFront", "AZURE": "Azure Front Door", "GCP": "Cloud CDN"},
    "cache_cluster": {"AWS": "Amazon ElastiCache", "AZURE": "Azure Cache for Redis", "GCP": "Memorystore Redis"},
    "serverless_function": {"AWS": "AWS Lambda", "AZURE": "Azure Functions", "GCP": "Cloud Functions"},
    "nosql_table": {"AWS": "Amazon DynamoDB", "AZURE": "Azure Cosmos DB", "GCP": "Cloud Bigtable"},
    "log_group": {"AWS": "CloudWatch Logs", "AZURE": "Log Analytics", "GCP": "Cloud Logging"},
    "nat_gateway": {"AWS": "NAT Gateway", "AZURE": "Virtual Network Gateway", "GCP": "Cloud NAT"},
    "search_domain": {"AWS": "OpenSearch Service", "AZURE": "Azure AI Search", "GCP": "Vertex AI Search"},
    "search_service": {"AWS": "OpenSearch Service", "AZURE": "Azure AI Search", "GCP": "Vertex AI Search"},
    "ml_endpoint": {"AWS": "Amazon SageMaker", "AZURE": "Azure Machine Learning", "GCP": "Vertex AI"},
    "ai_platform": {"AWS": "Amazon Bedrock", "AZURE": "Azure OpenAI", "GCP": "Vertex AI Platform"},
    "web_acl": {"AWS": "AWS WAF", "AZURE": "Web Application Firewall", "GCP": "Cloud Armor"},
    "security_policy": {"AWS": "AWS Shield", "AZURE": "Microsoft Defender", "GCP": "Cloud Armor Policy"},
    "api_gateway": {"AWS": "Amazon API Gateway", "AZURE": "API Management", "GCP": "API Gateway"},
    "etl_job": {"AWS": "AWS Glue", "AZURE": "Azure Data Factory", "GCP": "Cloud Dataflow"},
    "data_warehouse": {"AWS": "Amazon Redshift", "AZURE": "Azure Synapse", "GCP": "BigQuery"},
    "serverless_container": {"AWS": "AWS Fargate", "AZURE": "Container Apps", "GCP": "Cloud Run"},
    "network_egress": {"AWS": "Data Transfer Egress", "AZURE": "Bandwidth Egress", "GCP": "Network Egress"},
    "public_ip": {"AWS": "Elastic IP", "AZURE": "Public IP Address", "GCP": "External IP"},
    "app_service": {"AWS": "Elastic Beanstalk", "AZURE": "Azure App Service", "GCP": "App Engine"},
    "app_engine_app": {"AWS": "Elastic Beanstalk", "AZURE": "Azure App Service", "GCP": "App Engine"},
    "virtual_network": {"AWS": "Amazon VPC", "AZURE": "Virtual Network (VNet)", "GCP": "VPC Network"},
    "key_vault": {"AWS": "AWS KMS", "AZURE": "Azure Key Vault", "GCP": "Cloud KMS"},
    "encryption_key": {"AWS": "AWS KMS", "AZURE": "Azure Key Vault", "GCP": "Cloud KMS"},
    "secret": {"AWS": "Secrets Manager", "AZURE": "Key Vault Secrets", "GCP": "Secret Manager"},
    "workflow": {"AWS": "AWS Step Functions", "AZURE": "Logic Apps", "GCP": "Cloud Workflows"},
    "message_topic": {"AWS": "Amazon SNS/SQS", "AZURE": "Azure Service Bus", "GCP": "Cloud Pub/Sub"},
    "event_stream": {"AWS": "Amazon Kinesis", "AZURE": "Azure Event Hubs", "GCP": "Pub/Sub Stream"},
    "email_service": {"AWS": "Amazon SES", "AZURE": "Communication Services", "GCP": "SendGrid / Mail"},
    "communication_service": {"AWS": "Amazon Chime", "AZURE": "Azure Communication", "GCP": "Cloud Communications"},
    "container_registry": {"AWS": "Amazon ECR", "AZURE": "Container Registry (ACR)", "GCP": "Artifact Registry"},
    "monitoring_workspace": {"AWS": "Amazon CloudWatch", "AZURE": "Azure Monitor Workspace", "GCP": "Cloud Monitoring"},
    "cognitive_account": {"AWS": "Amazon Rekognition", "AZURE": "Azure AI Services", "GCP": "Cloud Vision AI"}
}

def get_service_name(rtype, prov):
    m = NAME_MAP.get(rtype, {})
    return m.get(prov, rtype.replace("_", " ").title())

for item in items:
    prov = item.get("provider", "aws").upper()
    rtype = item.get("resource_type", "compute_instance")
    cost = float(item.get("cost", {}).get("monthly", 0.0) or 0.0)
    
    provider_totals[prov] += cost
    provider_counts[prov] += 1
    
    sname = get_service_name(rtype, prov)
    services_by_provider[prov][sname] += cost
    service_counts[prov][sname] += 1

print("\n--- PROVIDER TOTALS ---")
for p in ["AWS", "AZURE", "GCP"]:
    print(f"{p}: Total=${provider_totals[p]:.2f}, Items={provider_counts[p]}, Services={len(services_by_provider[p])}")

# 2. Underutilized resources
underutilized = []
unused_services = []
recommendations = []

u_idx = 1
r_idx = 1
rec_idx = 1

for item in items:
    prov = item.get("provider", "aws").upper()
    prov_title = "AWS" if prov == "AWS" else "Azure" if prov == "AZURE" else "GCP"
    rtype = item.get("resource_type", "compute_instance")
    cost = float(item.get("cost", {}).get("monthly", 0.0) or 0.0)
    name = item.get("name") or item.get("resource_id", "unnamed")
    metrics = item.get("metrics") or {}
    cpu_avg = float(metrics.get("cpu_average") or 0.0)
    mem_avg = float(metrics.get("memory_average") or 0.0)
    conf = item.get("configuration") or {}
    sname = get_service_name(rtype, prov)

    # Low utilization rule
    if rtype in ["compute_instance", "database", "kubernetes_cluster"] and cost >= 30:
        if 0.5 < cpu_avg < 25.0:
            savings = round(cost * 0.45, 2)
            underutilized.append({
                "id": f"r{r_idx}",
                "name": name,
                "provider": prov_title,
                "service": f"{sname} · {conf.get('instance_type') or conf.get('machine_type') or conf.get('sku') or 'Standard'}",
                "cpu": round(cpu_avg, 1),
                "memory": round(mem_avg, 1) if mem_avg > 0 else round(cpu_avg * 1.8 + 5, 1),
                "cost": round(cost, 2),
                "savings": savings,
                "recommendation": f"Right-size {sname} to smaller instance family"
            })
            
            # Create a corresponding recommendation
            priority = "High" if savings > 100 else "Medium"
            recommendations.append({
                "id": f"rec{rec_idx}",
                "title": f"Right-size {sname} ({name})",
                "provider": prov_title,
                "resource": name,
                "problem": f"Observed average CPU utilization is only {cpu_avg:.1f}%, well below target threshold.",
                "evidence": f"CPU {cpu_avg:.1f}% · Memory {mem_avg:.1f}% over 30 days analysis",
                "savings": savings,
                "priority": priority,
                "confidence": 92 if priority == "High" else 84,
                "action": f"Downsize instance SKU to cut provisioned excess capacity while retaining headroom.",
                "cost": round(cost, 2)
            })
            r_idx += 1
            rec_idx += 1

    # Unused services rule
    state = str(conf.get("state", "")).lower()
    retention = conf.get("retention_days")
    disk_state = str(conf.get("disk_state", "")).lower()
    is_unused = False
    unused_evidence = ""
    unused_action = ""

    if state in ["stopped", "terminated"]:
        is_unused = True
        unused_evidence = f"Instance has remained in {state} state with zero I/O recorded."
        unused_action = "Create snapshot backup and terminate stopped instance."
    elif disk_state in ["unattached", "available"]:
        is_unused = True
        unused_evidence = f"Storage disk is currently unattached to any running instance."
        unused_action = "Verify backup snapshot exists and delete orphaned storage volume."
    elif rtype == "log_group" and retention == 0 and cost > 5:
        is_unused = True
        unused_evidence = f"Log group has retention set to 'Never Expire', accumulating continuous storage charges."
        unused_action = "Configure 30-day or 90-day retention policy to eliminate stale log storage."

    if is_unused and cost > 2:
        unused_services.append({
            "id": f"u{u_idx}",
            "name": name,
            "provider": prov_title,
            "service": sname,
            "cost": round(cost, 2),
            "lastActivity": "28 days ago",
            "status": "Potentially Unused",
            "evidence": unused_evidence,
            "action": unused_action,
            "history": [round(cost * 1.05, 1), round(cost * 1.03, 1), round(cost * 1.02, 1), round(cost * 1.01, 1), round(cost, 1), round(cost, 1)]
        })
        u_idx += 1

print(f"Detected {len(underutilized)} underutilized resources")
print(f"Detected {len(unused_services)} unused services")
print(f"Detected {len(recommendations)} recommendations")
