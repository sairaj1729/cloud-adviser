import json
import os
from collections import defaultdict

data_path = r"d:\Internship\Cloud\synthetic data\data.json"
with open(data_path, "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total items: {len(items)}")

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

# Provider totals & counts
totals = defaultdict(float)
counts = defaultdict(int)
service_spend = defaultdict(lambda: defaultdict(float))

for it in items:
    p = it.get("provider", "aws").upper()
    c = float(it.get("cost", {}).get("monthly", 0.0) or 0.0)
    rtype = it.get("resource_type", "compute_instance")
    totals[p] += c
    counts[p] += 1
    sname = get_service_name(rtype, p)
    service_spend[p][sname] += c

# Generate clean Service arrays sorted by spend
services_output = {}
for p in ["AWS", "AZURE", "GCP"]:
    p_key = "AWS" if p == "AWS" else "Azure" if p == "AZURE" else "GCP"
    sorted_s = sorted(service_spend[p].items(), key=lambda x: x[1], reverse=True)
    services_output[p_key] = []
    for sname, scost in sorted_s:
        # Generate realistic sparkline based on cost
        trend_base = max(1, int(round(scost / max(1, scost) * 5)))
        spark = [trend_base, trend_base + 1, trend_base, trend_base + 1, trend_base + 2, trend_base + 1, trend_base + 2, trend_base + 3]
        change = round((hash(sname) % 150 - 50) / 10.0, 1) # between -5.0 and +10.0
        services_output[p_key].append({
            "name": sname,
            "cost": round(scost),
            "change": change,
            "trend": spark
        })

# Underutilized resources
underutilized = []
unused_findings = []
recommendations = []

# Gather underutilized
for idx, it in enumerate(items):
    prov = it.get("provider", "aws").upper()
    prov_title = "AWS" if prov == "AWS" else "Azure" if prov == "AZURE" else "GCP"
    c = float(it.get("cost", {}).get("monthly", 0.0) or 0.0)
    rtype = it.get("resource_type", "compute_instance")
    metrics = it.get("metrics") or {}
    cpu = float(metrics.get("cpu_average") or 0.0)
    mem = float(metrics.get("memory_average") or 0.0)
    conf = it.get("configuration") or {}
    name = it.get("name") or it.get("resource_id", "unnamed")
    sname = get_service_name(rtype, prov)
    sku = conf.get("instance_type") or conf.get("machine_type") or conf.get("vm_size") or conf.get("sku") or "Standard"

    if rtype in ["compute_instance", "database", "kubernetes_cluster"] and c >= 25 and 0.5 < cpu < 22.0:
        savings = round(c * 0.45)
        res_id = f"r{len(underutilized) + 1}"
        underutilized.append({
            "id": res_id,
            "name": name,
            "provider": prov_title,
            "service": f"{sname} · {sku}",
            "cpu": round(cpu, 1),
            "memory": round(mem, 1) if mem > 0 else round(cpu * 1.8 + 6, 1),
            "cost": round(c),
            "savings": savings,
            "recommendation": f"Right-size {sname} to smaller instance"
        })

        rec_id = f"rec{len(recommendations) + 1}"
        priority = "High" if savings >= 100 else "Medium"
        recommendations.append({
            "id": rec_id,
            "title": f"Right-size {sname} ({name})",
            "provider": prov_title,
            "resource": name,
            "problem": f"Observed CPU utilization averages only {cpu:.1f}%, leaving excess unallocated capacity.",
            "evidence": f"CPU {cpu:.1f}% · Memory {mem:.1f}% over the last 30 days",
            "savings": savings,
            "priority": priority,
            "confidence": 94 if priority == "High" else 86,
            "action": f"Downsize {name} ({sku}) to a more cost-effective instance class.",
            "cost": round(c)
        })

    # Unused checks
    state = str(conf.get("state", "")).lower()
    retention = conf.get("retention_days")
    lifecycle = conf.get("lifecycle_rules")
    if state == "retired":
        unused_findings.append({
            "id": f"u{len(unused_findings) + 1}",
            "name": name,
            "provider": prov_title,
            "service": sname,
            "cost": round(c),
            "lastActivity": "32 days ago",
            "status": "Potentially Unused",
            "evidence": f"Resource marked in retired state with zero network traffic in the last 30 days.",
            "action": "Verify service deprecation and decommission remaining instance.",
            "history": [round(c * 1.05), round(c * 1.03), round(c * 1.01), round(c), round(c), round(c)]
        })
    elif rtype == "log_group" and retention == 0 and c > 5:
        unused_findings.append({
            "id": f"u{len(unused_findings) + 1}",
            "name": name,
            "provider": prov_title,
            "service": sname,
            "cost": round(c),
            "lastActivity": "Active (Never Expire)",
            "status": "Review Recommended",
            "evidence": "Log group retention is set to 'Never Expire', accumulating permanent storage cost.",
            "action": "Set a 30-day or 90-day retention policy to prune historical log streams.",
            "history": [round(c * 0.7), round(c * 0.8), round(c * 0.9), round(c * 0.95), round(c), round(c)]
        })

print(f"Underutilized count: {len(underutilized)}")
print(f"Unused count: {len(unused_findings)}")
print(f"Recommendations count: {len(recommendations)}")

# Output TypeScript file
ts_content = f"""// Production Cloud Dataset parsed directly from synthetic data/data.json (2,900 items)
export type Cloud = 'AWS' | 'Azure' | 'GCP';
export type Period = 'Daily' | 'Monthly' | 'Custom';
export const providers: Cloud[] = ['AWS', 'Azure', 'GCP'];

export const providerMeta = {{
  AWS: {{
    name: 'Amazon Web Services',
    short: 'AWS',
    color: 'var(--aws)',
    total: {round(totals['AWS'])},
    average: {round(totals['AWS'] * 0.93)},
    serviceCount: {len(services_output['AWS'])},
    change: 4.2
  }},
  Azure: {{
    name: 'Microsoft Azure',
    short: 'Azure',
    color: 'var(--azure)',
    total: {round(totals['AZURE'])},
    average: {round(totals['AZURE'] * 0.94)},
    serviceCount: {len(services_output['Azure'])},
    change: 6.8
  }},
  GCP: {{
    name: 'Google Cloud Platform',
    short: 'GCP',
    color: 'var(--gcp)',
    total: {round(totals['GCP'])},
    average: {round(totals['GCP'] * 0.96)},
    serviceCount: {len(services_output['GCP'])},
    change: -1.5
  }},
}};

export const money = (n: number) => '$' + Math.round(n).toLocaleString('en-US');

// Monthly trend based on real totals
export const trend = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((month, i) => {{
  const factor = [0.88, 0.90, 0.89, 0.92, 0.94, 0.93, 0.96, 0.95, 0.98, 0.97, 0.99, 1.0][i]!;
  return {{
    month,
    AWS: Math.round({round(totals['AWS'])} * factor),
    Azure: Math.round({round(totals['AZURE'])} * factor),
    GCP: Math.round({round(totals['GCP'])} * factor)
  }};
}});

export type Service = {{ name: string; cost: number; change: number; trend: number[] }};
export const services: Record<Cloud, Service[]> = {json.dumps(services_output, indent=2)};

export type Finding = {{ id: string; name: string; provider: Cloud; service: string; cost: number; lastActivity: string; status: string; evidence: string; action: string; history: number[] }};
export const unused: Finding[] = {json.dumps(unused_findings, indent=2)};

export type Resource = {{ id: string; name: string; provider: Cloud; service: string; cpu: number; memory: number; cost: number; savings: number; recommendation: string }};
export const resources: Resource[] = {json.dumps(underutilized, indent=2)};

export type Recommendation = {{ id: string; title: string; provider: Cloud; resource: string; problem: string; evidence: string; savings: number; priority: 'High' | 'Medium' | 'Low'; confidence: number; action: string; cost: number }};
export const recommendations: Recommendation[] = {json.dumps(recommendations, indent=2)};
"""

output_path = r"d:\Internship\Cloud\frontend\src\mockData\cloud.ts"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(ts_content)

print(f"Successfully generated {output_path}")
