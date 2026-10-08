# Provider Integration Architecture - Cloud Advisor V1

This document details how AWS, Microsoft Azure, and Google Cloud Platform (GCP) are integrated into the Cloud Advisor backend via abstract provider connectors.

---

## 1. Provider Abstraction Interface

All cloud provider integrations implement the `CloudProviderConnector` abstract base class defined in `backend/app/providers/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class CloudProviderConnector(ABC):

    @abstractmethod
    async def verify_connection((self) -> bool:
        """Verify credential validity and read access."""
        pass

    @abstractmethod
    async def get_resources(self) -> List[Dict[str, Any]]:
        """Discover compute, database, and storage resources."""
        pass

    @abstractmethod
    async def get_metrics(self, resource_id: str) -> Dict[str, Any]:
        """Fetch utilization metrics (CPU, Memory, IOPS)."""
        pass

    @abstractmethod
    async def get_costs(self, resource_id: str) -> Dict[str, Any]:
        """Fetch monthly spending and daily cost trends."""
        pass

    @abstractmethod
    async def get_recommendations(self) -> List[Dict[str, Any]]:
        """Fetch cloud-native recommendations if available."""
        pass
```

---

## 2. AWS Connector (`app/providers/aws/`)

### Authentication Model
V1 AWS connection uses **Cross-Account IAM Role Assumption** (`sts:AssumeRole`).
- **User Inputs**: Account ID, Role ARN, External ID.
- **SDK**: `boto3.client('sts')`.
- Temporary credentials (`AccessKeyId`, `SecretAccessKey`, `SessionToken`) are fetched dynamically during scans and never persisted in database collections.

### Priority Services in V1
1. **EC2**: `boto3.client('ec2')` (`describe_instances`)
2. **EBS**: `boto3.client('ec2')` (`describe_volumes`)
3. **CloudWatch**: `boto3.client('cloudwatch')` (`get_metric_data`)
4. **Cost Explorer**: `boto3.client('ce')` (`get_cost_and_usage`)

---

## 3. Azure Connector (`app/providers/azure/`)

### Authentication Model
Uses Microsoft Entra ID (Service Principal credentials):
- **User Inputs**: Tenant ID, Subscription ID, Client ID, Client Secret.
- **SDK**: `azure.identity.ClientSecretCredential`, `azure.mgmt.compute`, `azure.mgmt.costmanagement`.

---

## 4. GCP Connector (`app/providers/gcp/`)

### Authentication Model
Uses Google Cloud Service Account Credentials / Workload Identity Federation:
- **SDK**: `google.cloud.billing_v1`, `google.cloud.asset_v1`, `google.cloud.monitoring_v3`.

---

## 5. Extensibility
To add a new cloud provider (e.g. DigitalOcean, Oracle Cloud):
1. Create a new directory in `app/providers/<provider>/`.
2. Implement `CloudProviderConnector`.
3. Implement a matching normalizer in `app/normalization/`.
4. Register the provider in `app/providers/factory.py`.
5. No changes are required in the Rule Engine.
