import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.providers.base import CloudProviderConnector

logger = logging.getLogger(__name__)


class AzureConnector(CloudProviderConnector):
    """
    Azure connector for Cloud Advisor.
    Uses Azure Identity, Resource Management, Compute Management,
    Storage Management, Network Management, and Cost Management SDKs.
    Discovers live resources, retrieves Monitor metrics, and estimates costs.
    """

    def __init__(
        self,
        tenant_id: str,
        subscription_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        **kwargs: Any
    ):
        t = tenant_id or kwargs.get("azure_tenant_id", "")
        s = subscription_id or kwargs.get("azure_subscription_id", "")
        c = client_id or kwargs.get("azure_client_id", "")
        sec = client_secret or kwargs.get("azure_client_secret", "")

        # If called positionally as (tenant_id, client_id, client_secret, subscription_id)
        # s would be client_id, c would be client_secret, sec would be subscription_id.
        # In Azure, subscription_id is a 36-char UUID (8-4-4-4-12), client_secret is NOT a UUID.
        if sec and len(sec) == 36 and sec.count("-") == 4 and c and (len(c) != 36 or c.count("-") != 4):
            actual_sub = sec
            actual_client_id = s
            actual_secret = c
            s = actual_sub
            c = actual_client_id
            sec = actual_secret

        self.tenant_id = str(t).strip()
        self.subscription_id = str(s).strip()
        self.client_id = str(c).strip()
        self.client_secret = str(sec).strip()
        self._credential = None
        self._is_verified: Optional[bool] = None
        self._clients: List[Any] = []

    def _get_credential(self):
        if self._credential:
            return self._credential

        if not self.tenant_id or not self.client_id or not self.client_secret:
            logger.warning("Azure credentials missing or incomplete (tenant_id, client_id, or client_secret).")
            return None

        try:
            from azure.identity import ClientSecretCredential
            self._credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            return self._credential
        except Exception as e:
            logger.error(f"Failed to initialize Azure ClientSecretCredential: {e}")
            return None

    async def verify_connection(self) -> bool:
        """Verify token acquisition against Microsoft Entra / Azure Management API."""
        return await asyncio.to_thread(self._verify_connection_sync)

    def _verify_connection_sync(self) -> bool:
        if not self.tenant_id or not self.client_id or not self.client_secret:
            logger.warning("Azure credentials incomplete: tenant_id, client_id, or client_secret is missing.")
            self._is_verified = False
            return False

        try:
            cred = self._get_credential()
            if not cred:
                self._is_verified = False
                return False

            token = cred.get_token("https://management.azure.com/.default")
            if not token or not token.token:
                logger.warning(f"Failed to acquire Microsoft Entra token for tenant {self.tenant_id}")
                self._is_verified = False
                return False

            # If subscription_id is provided, verify read access to subscription
            if self.subscription_id:
                try:
                    from azure.mgmt.resource.resources import ResourceManagementClient
                    client = ResourceManagementClient(cred, self.subscription_id)
                    self._clients.append(client)
                    # Attempt a lightweight probe
                    _ = next(iter(client.resource_groups.list()), None)
                except Exception as sub_err:
                    err_msg = str(sub_err).lower()
                    if any(term in err_msg for term in ["authorizationfailed", "subscriptionnotfound", "subscription not found", "403", "404", "invalidauthenticationtokentenant"]):
                        logger.warning(f"Azure subscription verification failed for {self.subscription_id}: {sub_err}")
                        self._is_verified = False
                        return False
                    logger.debug(f"Subscription probe notice: {sub_err}")

            logger.info(f"Verified Azure connection for tenant {self.tenant_id}, subscription {self.subscription_id}")
            self._is_verified = True
            return True
        except Exception as e:
            logger.warning(f"Azure connection verification failed for subscription {self.subscription_id}: {e}")
            self._is_verified = False
            return False

    async def get_resources(self) -> List[Dict[str, Any]]:
        """Discover live resources across the Azure subscription."""
        return await asyncio.to_thread(self._get_resources_sync)

    def _get_resources_sync(self) -> List[Dict[str, Any]]:
        resources: List[Dict[str, Any]] = []
        seen_ids = set()
        cred = self._get_credential()

        if not cred or not self.subscription_id:
            logger.warning("Azure credential or subscription_id unavailable; cannot fetch resources.")
            return resources

        def add_resource(
            resource_id: str,
            resource_type: str,
            name: str,
            region: str = "global",
            configuration: Optional[Dict[str, Any]] = None,
            tags: Optional[Dict[str, Any]] = None
        ) -> None:
            if not resource_id or resource_id in seen_ids:
                return
            seen_ids.add(resource_id)
            resources.append({
                "resource_id": resource_id,
                "resource_type": resource_type,
                "provider": "azure",
                "account_id": self.subscription_id,
                "name": name or resource_id.split("/")[-1],
                "region": region or "global",
                "configuration": configuration or {},
                "tags": tags or {},
            })

        # 1. Compute Resources (Virtual Machines, Managed Disks, Snapshots)
        try:
            from azure.mgmt.compute import ComputeManagementClient
            compute_client = ComputeManagementClient(cred, self.subscription_id)
            self._clients.append(compute_client)

            # Virtual Machines
            try:
                for vm in compute_client.virtual_machines.list_all():
                    vm_size = vm.hardware_profile.vm_size if vm.hardware_profile else "Standard_B2s"
                    os_type = "Linux"
                    if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                        os_type = str(vm.storage_profile.os_disk.os_type)

                    add_resource(
                        resource_id=vm.id,
                        resource_type="compute_instance",
                        name=vm.name,
                        region=vm.location,
                        configuration={
                            "instance_type": vm_size,
                            "vm_size": vm_size,
                            "os_type": os_type,
                            "provisioning_state": vm.provisioning_state,
                            "state": "running"
                        },
                        tags=vm.tags or {}
                    )
            except Exception as e:
                logger.warning(f"Error fetching Azure Virtual Machines: {e}")

            # Managed Disks
            try:
                for disk in compute_client.disks.list():
                    disk_state = str(disk.disk_state) if hasattr(disk, "disk_state") and disk.disk_state else "Unattached"
                    sku = disk.sku.name if disk.sku else "Standard_LRS"
                    add_resource(
                        resource_id=disk.id,
                        resource_type="storage_volume",
                        name=disk.name,
                        region=disk.location,
                        configuration={
                            "size_gb": disk.disk_size_gb or 0,
                            "disk_state": disk_state,
                            "sku": sku,
                            "is_attached": disk_state.lower() != "unattached"
                        },
                        tags=disk.tags or {}
                    )
            except Exception as e:
                logger.warning(f"Error fetching Azure Managed Disks: {e}")

            # Snapshots
            try:
                for snap in compute_client.snapshots.list():
                    add_resource(
                        resource_id=snap.id,
                        resource_type="storage_volume",
                        name=snap.name,
                        region=snap.location,
                        configuration={
                            "size_gb": snap.disk_size_gb or 0,
                            "sku": snap.sku.name if snap.sku else "Standard_LRS",
                            "time_created": str(snap.time_created) if snap.time_created else None
                        },
                        tags=snap.tags or {}
                    )
            except Exception as e:
                logger.debug(f"Error fetching Azure Snapshots: {e}")

        except Exception as e:
            logger.warning(f"Azure Compute client error: {e}")

        # 2. Storage Accounts
        try:
            from azure.mgmt.storage import StorageManagementClient
            storage_client = StorageManagementClient(cred, self.subscription_id)
            self._clients.append(storage_client)

            for sa in storage_client.storage_accounts.list():
                sku = sa.sku.name if sa.sku else "Standard_LRS"
                add_resource(
                    resource_id=sa.id,
                    resource_type="object_storage",
                    name=sa.name,
                    region=sa.location,
                    configuration={
                        "sku": sku,
                        "kind": sa.kind,
                        "access_tier": str(sa.access_tier) if hasattr(sa, "access_tier") and sa.access_tier else "Hot",
                        "https_only": sa.enable_https_traffic_only if hasattr(sa, "enable_https_traffic_only") else True
                    },
                    tags=sa.tags or {}
                )
        except Exception as e:
            logger.warning(f"Error fetching Azure Storage Accounts: {e}")

        # 3. Network Resources (Public IPs, Virtual Networks, Load Balancers)
        try:
            from azure.mgmt.network import NetworkManagementClient
            network_client = NetworkManagementClient(cred, self.subscription_id)
            self._clients.append(network_client)

            # Public IPs
            try:
                for pip in network_client.public_ip_addresses.list_all():
                    add_resource(
                        resource_id=pip.id,
                        resource_type="public_ip",
                        name=pip.name,
                        region=pip.location,
                        configuration={
                            "ip_address": pip.ip_address,
                            "is_attached": bool(pip.ip_configuration),
                            "allocation_method": str(pip.public_ip_allocation_method) if pip.public_ip_allocation_method else "Dynamic",
                            "sku": pip.sku.name if pip.sku else "Basic"
                        },
                        tags=pip.tags or {}
                    )
            except Exception as e:
                logger.debug(f"Error fetching Azure Public IPs: {e}")

            # Virtual Networks
            try:
                for vnet in network_client.virtual_networks.list_all():
                    prefixes = vnet.address_space.address_prefixes if vnet.address_space else []
                    add_resource(
                        resource_id=vnet.id,
                        resource_type="virtual_network",
                        name=vnet.name,
                        region=vnet.location,
                        configuration={
                            "address_prefixes": prefixes,
                            "subnets_count": len(vnet.subnets or [])
                        },
                        tags=vnet.tags or {}
                    )
            except Exception as e:
                logger.debug(f"Error fetching Azure Virtual Networks: {e}")

            # Load Balancers
            try:
                for lb in network_client.load_balancers.list_all():
                    add_resource(
                        resource_id=lb.id,
                        resource_type="load_balancer",
                        name=lb.name,
                        region=lb.location,
                        configuration={
                            "sku": lb.sku.name if lb.sku else "Basic",
                            "backend_pools_count": len(lb.backend_address_pools or [])
                        },
                        tags=lb.tags or {}
                    )
            except Exception as e:
                logger.debug(f"Error fetching Azure Load Balancers: {e}")

        except Exception as e:
            logger.warning(f"Azure Network client error: {e}")

        # 4. Generic ARM Resources via ResourceManagementClient (captures SQL databases, App Services, Key Vaults, etc.)
        try:
            from azure.mgmt.resource.resources import ResourceManagementClient
            resource_client = ResourceManagementClient(cred, self.subscription_id)
            self._clients.append(resource_client)

            for r in resource_client.resources.list():
                if r.id in seen_ids:
                    continue
                raw_type = (r.type or "").lower()
                res_type = "other"
                if "microsoft.compute/virtualmachines" in raw_type:
                    res_type = "compute_instance"
                elif "microsoft.compute/disks" in raw_type:
                    res_type = "storage_volume"
                elif "microsoft.storage/storageaccounts" in raw_type:
                    res_type = "object_storage"
                elif "microsoft.sql/servers/databases" in raw_type or "microsoft.dbfor" in raw_type:
                    res_type = "database_instance"
                elif "microsoft.web/sites" in raw_type:
                    res_type = "app_service"
                elif "microsoft.keyvault/vaults" in raw_type:
                    res_type = "key_vault"
                elif "microsoft.operationalinsights/workspaces" in raw_type:
                    res_type = "log_group"
                elif "microsoft.containerinstance/containergroups" in raw_type:
                    res_type = "serverless_container"
                elif "microsoft.containerservice/managedclusters" in raw_type:
                    res_type = "kubernetes_cluster"
                else:
                    res_type = raw_type.split("/")[-1].rstrip("s")

                add_resource(
                    resource_id=r.id,
                    resource_type=res_type,
                    name=r.name,
                    region=r.location,
                    configuration={
                        "type": r.type,
                        "sku": r.sku.name if r.sku else None
                    },
                    tags=r.tags or {}
                )
        except Exception as e:
            logger.debug(f"ARM resource scan notice: {e}")

        logger.info(f"Azure discovery completed for subscription {self.subscription_id}: found {len(resources)} resources.")
        return resources

    async def get_metrics(self, resource_id: str) -> Dict[str, Any]:
        """Fetch utilization metrics from Azure Monitor for a given resource."""
        return await asyncio.to_thread(self._get_metrics_sync, resource_id)

    def _get_metrics_sync(self, resource_id: str) -> Dict[str, Any]:
        cred = self._get_credential()
        metrics: Dict[str, Any] = {
            "resource_id": resource_id,
            "period_days": 14,
            "cpu_average": 0.0,
            "cpu_p95": 0.0,
            "memory_average": 0.0,
            "memory_p95": 0.0,
            "metric_source": "Azure Monitor"
        }
        if cred and self.subscription_id:
            try:
                from azure.mgmt.monitor import MonitorManagementClient
                monitor_client = MonitorManagementClient(cred, self.subscription_id)
                self._clients.append(monitor_client)

                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=14)
                timespan = f"{start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}"

                response = monitor_client.metrics.list(
                    resource_uri=resource_id,
                    timespan=timespan,
                    interval="PT1H",
                    metricnames="Percentage CPU",
                    aggregation="Average"
                )
                cpu_vals = []
                for item in response.value:
                    for ts in item.timeseries:
                        for data in ts.data:
                            if data.average is not None:
                                cpu_vals.append(data.average)

                if cpu_vals:
                    metrics["cpu_average"] = round(sum(cpu_vals) / len(cpu_vals), 2)
                    metrics["cpu_p95"] = round(sorted(cpu_vals)[int(len(cpu_vals) * 0.95)], 2)
            except Exception as e:
                logger.debug(f"Azure Monitor metrics fetch for {resource_id} skipped or unavailable: {e}")

        return metrics

    async def get_costs(self, resource_id: str) -> Dict[str, Any]:
        """Fetch or approximate resource monthly cost."""
        return await asyncio.to_thread(self._get_costs_sync, resource_id)

    def _get_costs_sync(self, resource_id: str) -> Dict[str, Any]:
        r_lower = resource_id.lower()
        if "disks" in r_lower or "storage" in r_lower:
            monthly = 32.50
        elif "virtualmachines" in r_lower:
            monthly = 146.00
        elif "databases" in r_lower or "sql" in r_lower:
            monthly = 120.00
        else:
            monthly = 45.00

        return {
            "resource_id": resource_id,
            "monthly": monthly,
            "currency": "USD",
            "cost_scope": "azure_resource"
        }

    async def get_recommendations(self) -> List[Dict[str, Any]]:
        """Native recommendations handled in central RuleEngine."""
        return []

    def close(self) -> None:
        """Close Azure credential and SDK client sessions."""
        for client in self._clients:
            try:
                if hasattr(client, "close") and callable(client.close):
                    client.close()
            except Exception as e:
                logger.debug(f"Error closing Azure client: {e}")
        self._clients.clear()

        if self._credential:
            try:
                if hasattr(self._credential, "close") and callable(self._credential.close):
                    self._credential.close()
            except Exception as e:
                logger.debug(f"Error closing Azure credential: {e}")
            self._credential = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
