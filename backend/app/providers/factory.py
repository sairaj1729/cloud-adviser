from typing import Dict, Any
from app.providers.base import CloudProviderConnector
from app.providers.aws.connector import AWSConnector
from app.providers.azure.connector import AzureConnector
from app.providers.gcp.connector import GCPConnector

class ProviderFactory:

    @staticmethod
    def get_connector(account_doc: Dict[str, Any]) -> CloudProviderConnector:
        provider = account_doc.get("provider", "").lower()
        provider_config = account_doc.get("provider_config", {})

        if provider == "aws":
            return AWSConnector(
                account_id=account_doc.get("account_identifier"),
                role_arn=provider_config.get("role_arn") or account_doc.get("role_arn", ""),
                external_id=provider_config.get("external_id") or account_doc.get("external_id"),
                region=account_doc.get("region") or provider_config.get("region", "us-east-1")
            )
        elif provider == "azure":
            return AzureConnector(
                tenant_id=provider_config.get("azure_tenant_id") or account_doc.get("azure_tenant_id", ""),
                subscription_id=account_doc.get("account_identifier", ""),
                client_id=provider_config.get("azure_client_id") or account_doc.get("azure_client_id", ""),
                client_secret=provider_config.get("azure_client_secret") or account_doc.get("azure_client_secret", "")
            )
        elif provider == "gcp":
            return GCPConnector(
                project_id=account_doc.get("account_identifier") or provider_config.get("gcp_project_id", ""),
                service_account_info=provider_config.get("gcp_credentials") or provider_config.get("service_account_info") or provider_config.get("credentials_info"),
                service_account_json=provider_config.get("service_account_json") or provider_config.get("service_account_path"),
                billing_table=provider_config.get("gcp_billing_table") or provider_config.get("billing_table"),
                billing_project_id=provider_config.get("billing_project_id"),
                region=account_doc.get("region") or provider_config.get("region"),
            )
        else:
            raise ValueError(f"Unsupported cloud provider: {provider}")
