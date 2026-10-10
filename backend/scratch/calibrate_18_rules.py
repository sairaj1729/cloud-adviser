import json
import os
from collections import defaultdict

data_path = r"d:\Internship\Cloud\synthetic data\data.json"
data = json.load(open(data_path, encoding="utf-8"))

print(f"Total data items: {len(data)}")

# Let's check distribution of CPU on compute_instance and database
for prov in ["aws", "azure", "gcp"]:
    ec2_cpus = [float(x.get("metrics", {}).get("cpu_average", 0)) for x in data if x.get("provider") == prov and x.get("resource_type") == "compute_instance"]
    db_cpus = [float(x.get("metrics", {}).get("cpu_average", 0)) for x in data if x.get("provider") == prov and x.get("resource_type") == "database"]
    db_costs = [float(x.get("cost", {}).get("monthly", 0)) for x in data if x.get("provider") == prov and x.get("resource_type") == "database"]
    print(f"\n{prov.upper()} compute_instance: {len(ec2_cpus)} items, min CPU={min(ec2_cpus) if ec2_cpus else 'N/A'}, max CPU={max(ec2_cpus) if ec2_cpus else 'N/A'}")
    print(f"  CPU < 20%: {sum(1 for c in ec2_cpus if 0 < c < 20)}")
    print(f"  CPU < 10%: {sum(1 for c in ec2_cpus if 0 < c < 10)}")
    print(f"  CPU < 5%:  {sum(1 for c in ec2_cpus if 0 < c < 5)}")
    print(f"{prov.upper()} database: {len(db_cpus)} items")
    print(f"  CPU < 20%: {sum(1 for c in db_cpus if 0 < c < 20)}")
    print(f"  CPU < 10%: {sum(1 for c in db_cpus if 0 < c < 10)}")
    print(f"  Cost > 200: {sum(1 for c in db_costs if c > 200)}")
    print(f"  Cost > 100: {sum(1 for c in db_costs if c > 100)}")
