"""
GCP connector for Cloud Advisor.

Supported:
- GCP authentication and project verification
- Compute Engine VM and disk inventory
- Cloud Storage bucket inventory
- GKE cluster inventory
- Cloud SQL inventory
- Compute Engine CPU metrics from Cloud Monitoring
- Billing export costs from BigQuery

No dummy resources, synthetic metrics, or estimated billing amounts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import google.auth
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google.cloud import bigquery
from google.cloud import compute_v1
from google.cloud import monitoring_v3
from google.cloud import storage
from google.cloud import container_v1

from app.providers.base import CloudProviderConnector

logger = logging.getLogger(__name__)

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class GCPConnectionResult(dict):
    """
    Dictionary response representing GCP connection verification status.
    Implements boolean truthiness so `if verified:` and `if connection["success"]:`
    both evaluate seamlessly across both caller styles.
    """

    @property
    def success(self) -> bool:
        return bool(self.get("success", False))

    def __bool__(self) -> bool:
        return self.success


class GCPConnector(CloudProviderConnector):
    """Read-only connector for a single Google Cloud project."""

    provider = "gcp"

    def __init__(
        self,
        project_id: str,
        service_account_info: Optional[Union[Dict[str, Any], str]] = None,
        service_account_json: Optional[str] = None,
        billing_table: Optional[str] = None,
        billing_project_id: Optional[str] = None,
        region: Optional[str] = None,
        credentials_info: Optional[Union[Dict[str, Any], str]] = None,
        **kwargs: Any,
    ):
        raw_project = (
            project_id
            or kwargs.get("gcp_project_id")
            or kwargs.get("account_identifier")
            or ""
        )
        if not raw_project or not str(raw_project).strip():
            raise ValueError("GCP project_id is required.")

        self.project_id = str(raw_project).strip()

        # Handle service account credentials from multiple parameter conventions
        sa_info = service_account_info or credentials_info or kwargs.get("gcp_credentials")
        if isinstance(sa_info, str) and sa_info.strip().startswith("{"):
            try:
                sa_info = json.loads(sa_info)
            except Exception as e:
                logger.warning(f"Could not parse service account JSON string: {e}")

        sa_json = service_account_json or kwargs.get("service_account_json") or kwargs.get("service_account_path")
        # If sa_json is an inlined JSON string rather than a file path, treat as sa_info
        if isinstance(sa_json, str) and sa_json.strip().startswith("{"):
            try:
                sa_info = json.loads(sa_json)
                sa_json = None
            except Exception:
                pass

        if sa_info and sa_json:
            raise ValueError("Provide service_account_info OR service_account_json, not both.")

        self.billing_table = billing_table or kwargs.get("gcp_billing_table") or kwargs.get("billing_table")
        self.billing_project_id = billing_project_id or kwargs.get("billing_project_id") or self.project_id
        self.region = region or kwargs.get("region")

        self.credentials = None
        self._credential_info = sa_info if isinstance(sa_info, dict) else None
        self._credential_path = sa_json if isinstance(sa_json, str) and os.path.isfile(sa_json) else None

        # Map to resolve VM names to their numeric instance IDs for Cloud Monitoring queries
        self._instance_name_to_id: Dict[str, str] = {}

        # Lazy initialization: do not make cloud API calls in __init__.
        self._compute_instances = None
        self._compute_disks = None
        self._compute_zones = None
        self._monitoring = None
        self._storage = None
        self._bigquery = None
        self._container = None
        self._sqladmin = None

    def _get_credentials(self):
        if self.credentials is not None:
            return self.credentials

        try:
            if self._credential_info:
                self.credentials = service_account.Credentials.from_service_account_info(
                    self._credential_info,
                    scopes=[CLOUD_PLATFORM_SCOPE],
                )
            elif self._credential_path:
                self.credentials = service_account.Credentials.from_service_account_file(
                    self._credential_path,
                    scopes=[CLOUD_PLATFORM_SCOPE],
                )
            else:
                # Supports Application Default Credentials, including
                # Workload Identity Federation and service-account impersonation.
                self.credentials, detected_project = google.auth.default(
                    scopes=[CLOUD_PLATFORM_SCOPE]
                )

                if not self.project_id and detected_project:
                    self.project_id = detected_project

            return self.credentials
        except Exception as e:
            logger.warning(f"Could not load GCP credentials: {e}")
            return None

    def _init_clients(self):
        credentials = self._get_credentials()
        if not credentials:
            return

        if self._compute_instances is None:
            self._compute_instances = compute_v1.InstancesClient(
                credentials=credentials
            )
            self._compute_disks = compute_v1.DisksClient(
                credentials=credentials
            )
            self._compute_zones = compute_v1.ZonesClient(
                credentials=credentials
            )
            self._monitoring = monitoring_v3.MetricServiceClient(
                credentials=credentials
            )
            self._storage = storage.Client(
                project=self.project_id,
                credentials=credentials,
            )
            self._bigquery = bigquery.Client(
                project=self.billing_project_id,
                credentials=credentials,
            )
            self._container = container_v1.ClusterManagerClient(
                credentials=credentials
            )

            self._sqladmin = build(
                "sqladmin",
                "v1",
                credentials=credentials,
                cache_discovery=False,
            )

    async def _run(self, function, *args, **kwargs):
        """Run blocking Google SDK operations without blocking the event loop."""
        return await asyncio.to_thread(function, *args, **kwargs)

    async def verify_connection(self) -> GCPConnectionResult:
        """
        Verify authentication and access to the requested project.
        Returns a GCPConnectionResult (dict subclass) compatible with both:
        `if connection["success"]:` and `if verified:`.
        """
        try:
            self._init_clients()
            if not self.credentials or not self._compute_zones:
                return GCPConnectionResult({
                    "success": False,
                    "provider": self.provider,
                    "project_id": self.project_id,
                    "error": "Authentication failed: No valid service-account credentials or Application Default Credentials found.",
                })

            # A successful list call verifies access to Compute Engine.
            await self._run(
                lambda: list(
                    self._compute_zones.list(project=self.project_id)
                )
            )

            return GCPConnectionResult({
                "success": True,
                "provider": self.provider,
                "project_id": self.project_id,
                "message": "Authentication and Compute Engine access verified.",
                "billing_configured": bool(self.billing_table),
            })

        except Exception as exc:
            logger.warning(
                "GCP connection verification failed for project %s: %s",
                self.project_id,
                type(exc).__name__,
            )
            return GCPConnectionResult({
                "success": False,
                "provider": self.provider,
                "project_id": self.project_id,
                "error": self._friendly_error(exc),
            })

    async def get_resources(self) -> List[Dict[str, Any]]:
        """Discover resources and return a normalized resource list for Cloud Advisor."""
        self._init_clients()

        resources: List[Dict[str, Any]] = []

        # Discover zones first so VM and disk inventory can be collected.
        zones = await self._run(
            lambda: [
                zone.name
                for zone in self._compute_zones.list(
                    project=self.project_id
                )
                if zone.name
                and zone.status == "UP"
                and (
                    not self.region
                    or zone.name.startswith(self.region + "-")
                )
            ]
        )

        async def collect_zone(zone_name: str):
            def fetch():
                vms = list(
                    self._compute_instances.list(
                        project=self.project_id,
                        zone=zone_name,
                    )
                )
                disks = list(
                    self._compute_disks.list(
                        project=self.project_id,
                        zone=zone_name,
                    )
                )
                return vms, disks

            return await self._run(fetch)

        zone_results = await asyncio.gather(
            *(collect_zone(zone) for zone in zones),
            return_exceptions=True,
        )

        for zone_name, result in zip(zones, zone_results):
            if isinstance(result, Exception):
                logger.warning(
                    "Unable to list resources in zone %s (%s)",
                    zone_name,
                    type(result).__name__,
                )
                continue

            vms, disks = result

            for vm in vms:
                numeric_id = str(vm.id)
                self._instance_name_to_id[vm.name] = numeric_id
                machine_type = (
                    vm.machine_type.rsplit("/", 1)[-1]
                    if vm.machine_type
                    else None
                )

                resources.append({
                    "provider": "gcp",
                    "account_id": self.project_id,
                    "project_id": self.project_id,
                    "resource_id": numeric_id,
                    "resource_name": vm.name,
                    "name": vm.name,
                    "resource_type": "compute_instance",
                    "service": "Compute Engine",
                    "region": zone_name.rsplit("-", 1)[0],
                    "zone": zone_name,
                    "status": vm.status,
                    "configuration": {
                        "instance_type": machine_type,
                        "machine_type": machine_type,
                        "cpu_count": vm.guest_cpus,
                        "memory_mb": vm.memory_mb,
                        "state": vm.status,
                        "status": vm.status,
                        "self_link": vm.self_link,
                        "network_interfaces": len(vm.network_interfaces or []),
                        "disks_attached": len(vm.disks or []),
                    },
                    "tags": dict(vm.labels or {}),
                    "labels": dict(vm.labels or {}),
                    "created_at": (
                        vm.creation_timestamp
                        if vm.creation_timestamp
                        else None
                    ),
                    "metadata": {
                        "self_link": vm.self_link,
                        "network_interfaces": len(vm.network_interfaces or []),
                        "disks_attached": len(vm.disks or []),
                    },
                })

            for disk in disks:
                users = list(disk.users or [])
                is_attached = len(users) > 0
                disk_state = "Attached" if is_attached else "Unattached"
                disk_type = (
                    disk.type.rsplit("/", 1)[-1]
                    if disk.type
                    else None
                )

                resources.append({
                    "provider": "gcp",
                    "account_id": self.project_id,
                    "project_id": self.project_id,
                    "resource_id": str(disk.id),
                    "resource_name": disk.name,
                    "name": disk.name,
                    "resource_type": "storage_volume",
                    "service": "Compute Engine",
                    "region": zone_name.rsplit("-", 1)[0],
                    "zone": zone_name,
                    "status": "READY",
                    "configuration": {
                        "size_gb": disk.size_gb,
                        "disk_type": disk_type,
                        "is_attached": is_attached,
                        "disk_state": disk_state,
                        "users": users,
                        "self_link": disk.self_link,
                    },
                    "tags": dict(disk.labels or {}),
                    "labels": dict(disk.labels or {}),
                    "metadata": {
                        "self_link": disk.self_link,
                        "users": users,
                        "disk_type": disk_type,
                    },
                })

        # Cloud Storage bucket inventory
        try:
            buckets = await self._run(
                lambda: list(
                    self._storage.list_buckets(
                        project=self.project_id
                    )
                )
            )

            for bucket in buckets:
                resources.append({
                    "provider": "gcp",
                    "account_id": self.project_id,
                    "project_id": self.project_id,
                    "resource_id": bucket.name,
                    "resource_name": bucket.name,
                    "name": bucket.name,
                    "resource_type": "object_storage",
                    "service": "Cloud Storage",
                    "region": bucket.location,
                    "status": "ACTIVE",
                    "configuration": {
                        "storage_class": bucket.storage_class,
                        "versioning_enabled": bool(bucket.versioning_enabled),
                    },
                    "tags": dict(bucket.labels or {}),
                    "labels": dict(bucket.labels or {}),
                    "created_at": (
                        bucket.time_created.isoformat()
                        if bucket.time_created
                        else None
                    ),
                    "metadata": {
                        "storage_class": bucket.storage_class,
                        "versioning_enabled": bool(bucket.versioning_enabled),
                    },
                })
        except Exception as exc:
            logger.warning(
                "Cloud Storage inventory unavailable (%s)",
                type(exc).__name__,
            )

        # Google Kubernetes Engine clusters
        try:
            parent = f"projects/{self.project_id}/locations/-"

            cluster_response = await self._run(
                self._container.list_clusters,
                parent=parent,
            )

            for cluster in cluster_response.clusters or []:
                resources.append({
                    "provider": "gcp",
                    "account_id": self.project_id,
                    "project_id": self.project_id,
                    "resource_id": cluster.id or cluster.name,
                    "resource_name": cluster.name,
                    "name": cluster.name,
                    "resource_type": "kubernetes_cluster",
                    "service": "Google Kubernetes Engine",
                    "region": cluster.location,
                    "status": (
                        cluster.status.name
                        if cluster.status
                        else "UNKNOWN"
                    ),
                    "configuration": {
                        "node_count": cluster.current_node_count,
                        "endpoint": cluster.endpoint,
                        "autopilot": bool(cluster.autopilot),
                    },
                    "tags": dict(cluster.resource_labels or {}),
                    "labels": dict(cluster.resource_labels or {}),
                    "metadata": {
                        "node_count": cluster.current_node_count,
                        "endpoint": cluster.endpoint,
                        "autopilot": bool(cluster.autopilot),
                    },
                })
        except Exception as exc:
            logger.warning(
                "GKE inventory unavailable (%s)",
                type(exc).__name__,
            )

        # Cloud SQL inventory
        try:
            sql_response = await self._run(
                lambda: self._sqladmin.instances()
                .list(project=self.project_id)
                .execute()
            )

            for instance in sql_response.get("items", []):
                resources.append({
                    "provider": "gcp",
                    "account_id": self.project_id,
                    "project_id": self.project_id,
                    "resource_id": instance.get("name"),
                    "resource_name": instance.get("name"),
                    "name": instance.get("name"),
                    "resource_type": "database",
                    "service": "Cloud SQL",
                    "region": instance.get("region"),
                    "status": instance.get("state", "UNKNOWN"),
                    "configuration": {
                        "database_version": instance.get("databaseVersion"),
                        "tier": instance.get("settings", {}).get("tier"),
                        "availability_type": (
                            instance.get("settings", {}).get("availabilityType")
                        ),
                        "state": instance.get("state", "UNKNOWN"),
                    },
                    "tags": dict(instance.get("settings", {}).get("userLabels") or {}),
                    "metadata": {
                        "database_version": instance.get("databaseVersion"),
                        "tier": instance.get("settings", {}).get("tier"),
                        "availability_type": (
                            instance.get("settings", {}).get("availabilityType")
                        ),
                    },
                })
        except Exception as exc:
            logger.warning(
                "Cloud SQL inventory unavailable (%s)",
                type(exc).__name__,
            )

        logger.info(
            "Discovered %d GCP resources for project %s",
            len(resources),
            self.project_id,
        )
        return resources

    async def get_metrics(
        self,
        resource_id: str,
        lookback_days: int = 14,
    ) -> Dict[str, Any]:
        """
        Retrieve real Cloud Monitoring CPU metrics for a Compute Engine VM.

        resource_id should be the VM's numeric instance ID or known VM name.
        Other resource types return an explicit unsupported/unavailable result.
        """
        # If resource_id is a VM name, attempt mapping to numeric ID
        lookup_id = str(resource_id).strip()
        if not lookup_id.isdigit() and lookup_id in self._instance_name_to_id:
            lookup_id = self._instance_name_to_id[lookup_id]

        if not lookup_id or not lookup_id.isdigit():
            return {
                "provider": "gcp",
                "resource_id": resource_id,
                "available": False,
                "cpu_average": 0.0,
                "cpu_p95": 0.0,
                "cpu_avg_percent": 0.0,
                "cpu_p95_percent": 0.0,
                "memory_average": 0.0,
                "memory_p95": 0.0,
                "reason": (
                    "CPU metrics require a numeric Compute Engine instance ID."
                ),
            }

        self._init_clients()
        if not self.credentials or not self._monitoring:
            return {
                "provider": "gcp",
                "resource_id": resource_id,
                "available": False,
                "cpu_average": 0.0,
                "cpu_p95": 0.0,
                "cpu_avg_percent": 0.0,
                "cpu_p95_percent": 0.0,
                "memory_average": 0.0,
                "memory_p95": 0.0,
                "reason": "Monitoring client unavailable or unauthenticated.",
            }

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=lookback_days)

        interval = monitoring_v3.TimeInterval(
            {
                "end_time": end_time,
                "start_time": start_time,
            }
        )

        filter_expression = (
            'metric.type = "compute.googleapis.com/instance/cpu/utilization" '
            'AND resource.type = "gce_instance" '
            f'AND resource.labels.instance_id = "{lookup_id}"'
        )

        try:
            series = await self._run(
                lambda: list(
                    self._monitoring.list_time_series(
                        request={
                            "name": f"projects/{self.project_id}",
                            "filter": filter_expression,
                            "interval": interval,
                            "view": (
                                monitoring_v3.ListTimeSeriesRequest
                                .TimeSeriesView.FULL
                            ),
                        }
                    )
                )
            )

            values = []

            for time_series in series:
                for point in time_series.points:
                    value = point.value.double_value
                    if value is not None:
                        # GCP CPU utilization is a fraction (0.0 to 1.0).
                        values.append(float(value) * 100.0)

            if not values:
                return {
                    "provider": "gcp",
                    "project_id": self.project_id,
                    "resource_id": resource_id,
                    "available": False,
                    "cpu_average": 0.0,
                    "cpu_p95": 0.0,
                    "cpu_avg_percent": 0.0,
                    "cpu_p95_percent": 0.0,
                    "memory_average": 0.0,
                    "memory_p95": 0.0,
                    "reason": (
                        "No CPU time series was returned. Verify Monitoring "
                        "permissions, instance ID, and metric availability."
                    ),
                    "lookback_days": lookback_days,
                }

            sorted_values = sorted(values)
            p95_index = max(
                0,
                min(
                    len(sorted_values) - 1,
                    int(0.95 * (len(sorted_values) - 1)),
                ),
            )

            cpu_avg = sum(values) / len(values)
            cpu_max = max(values)
            cpu_p95 = sorted_values[p95_index]

            return {
                "provider": "gcp",
                "project_id": self.project_id,
                "resource_id": resource_id,
                "available": True,
                "lookback_days": lookback_days,
                "cpu_average": round(cpu_avg, 2),
                "cpu_p95": round(cpu_p95, 2),
                "cpu_avg_percent": round(cpu_avg, 2),
                "cpu_max_percent": round(cpu_max, 2),
                "cpu_p95_percent": round(cpu_p95, 2),
                "memory_average": 0.0,
                "memory_p95": 0.0,
                "sample_count": len(values),
                "memory_utilization_percent": None,
                "memory_note": (
                    "Memory utilization is not inferred. Configure the "
                    "appropriate guest metrics/agent before using it."
                ),
            }

        except Exception as exc:
            logger.warning(
                "Cloud Monitoring query failed (%s)",
                type(exc).__name__,
            )
            return {
                "provider": "gcp",
                "project_id": self.project_id,
                "resource_id": resource_id,
                "available": False,
                "cpu_average": 0.0,
                "cpu_p95": 0.0,
                "cpu_avg_percent": 0.0,
                "cpu_p95_percent": 0.0,
                "memory_average": 0.0,
                "memory_p95": 0.0,
                "reason": self._friendly_error(exc),
            }

    async def get_costs(
        self,
        resource_id: Optional[str] = None,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Query an existing Cloud Billing BigQuery export.

        Configure billing_table as:
        billing_project.dataset.gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX

        A resource-level cost is returned only when the export contains
        matching resource.name values. Otherwise project-level cost is
        returned and explicitly labeled.
        """
        if not self.billing_table:
            return {
                "provider": "gcp",
                "project_id": self.project_id,
                "resource_id": resource_id,
                "available": False,
                "scope": "unavailable",
                "cost": 0.0,
                "monthly": 0.0,
                "currency": "USD",
                "reason": (
                    "Billing export is not configured. Enable Cloud Billing "
                    "export to BigQuery and configure billing_table."
                ),
            }

        self._init_clients()
        if not self.credentials or not self._bigquery:
            return {
                "provider": "gcp",
                "project_id": self.project_id,
                "resource_id": resource_id,
                "available": False,
                "scope": "unavailable",
                "cost": 0.0,
                "monthly": 0.0,
                "currency": "USD",
                "reason": "BigQuery client unavailable or unauthenticated.",
            }

        # Only allow a fully qualified BigQuery table identifier.
        if not re.fullmatch(
            r"[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+",
            self.billing_table,
        ):
            raise ValueError(
                "billing_table must be project.dataset.table."
            )

        table = f"`{self.billing_table}`"
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=lookback_days)

        sql = f"""
            SELECT
                SUM(cost + IFNULL((
                    SELECT SUM(c.amount)
                    FROM UNNEST(credits) AS c
                ), 0)) AS net_cost,
                ANY_VALUE(currency) AS currency,
                COUNT(*) AS row_count
            FROM {table}
            WHERE project.id = @project_id
              AND DATE(usage_start_time) >= @start_date
              AND DATE(usage_start_time) < @end_date
              AND (
                    @resource_id IS NULL
                    OR resource.name = @resource_id
                  )
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "project_id", "STRING", self.project_id
                ),
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", start_date
                ),
                bigquery.ScalarQueryParameter(
                    "end_date", "DATE", end_date
                ),
                bigquery.ScalarQueryParameter(
                    "resource_id", "STRING", resource_id
                ),
            ]
        )

        try:
            job = await self._run(
                self._bigquery.query,
                sql,
                job_config=job_config,
            )
            rows = await self._run(lambda: list(job.result()))
            row = rows[0] if rows else None

            if not row or row["net_cost"] is None:
                return {
                    "provider": "gcp",
                    "project_id": self.project_id,
                    "resource_id": resource_id,
                    "available": False,
                    "scope": (
                        "resource" if resource_id else "project"
                    ),
                    "currency": "USD",
                    "cost": 0.0,
                    "monthly": 0.0,
                    "lookback_days": lookback_days,
                    "reason": (
                        "No billing rows matched this query. Check export "
                        "configuration, date range, permissions, and resource "
                        "name availability."
                    ),
                }

            net_cost = float(row["net_cost"])
            curr = row["currency"] or "USD"

            return {
                "provider": "gcp",
                "project_id": self.project_id,
                "resource_id": resource_id,
                "available": True,
                "scope": "resource" if resource_id else "project",
                "cost": net_cost,
                "monthly": net_cost,
                "currency": curr,
                "row_count": row["row_count"],
                "lookback_days": lookback_days,
                "start_date": start_date.isoformat(),
                "end_date_exclusive": end_date.isoformat(),
                "source": "Cloud Billing BigQuery export",
            }

        except Exception as exc:
            logger.warning(
                "BigQuery billing query failed (%s)",
                type(exc).__name__,
            )
            return {
                "provider": "gcp",
                "project_id": self.project_id,
                "resource_id": resource_id,
                "available": False,
                "scope": "resource" if resource_id else "project",
                "cost": 0.0,
                "monthly": 0.0,
                "currency": "USD",
                "reason": self._friendly_error(exc),
            }

    async def get_recommendations(
        self,
        resource_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Recommendations belong to Cloud Advisor's centralized Rule Engine."""
        return []

    def close(self) -> None:
        """Synchronously release supported client resources where applicable."""
        if self._bigquery is not None:
            try:
                self._bigquery.close()
            except Exception as e:
                logger.debug(f"Error closing BigQuery client: {e}")
            self._bigquery = None

        if self._storage is not None:
            try:
                self._storage.close()
            except Exception as e:
                logger.debug(f"Error closing Storage client: {e}")
            self._storage = None

    async def aclose(self) -> None:
        """Asynchronously release supported client resources where applicable."""
        await self._run(self.close)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        """Return a safe error message without credential material."""
        if isinstance(exc, GoogleAuthError):
            return (
                "Authentication failed. Check the service-account "
                "credentials or Application Default Credentials."
            )

        if isinstance(exc, HttpError):
            status = getattr(exc.resp, "status", None)

            if status == 403:
                return (
                    "Permission denied. Check the IAM roles and enabled "
                    "Google Cloud APIs for this project."
                )

            if status == 404:
                return (
                    "Project or API resource was not found. Check the "
                    "project ID and API configuration."
                )

            return f"Google API request failed (HTTP {status})."

        return f"{type(exc).__name__}: {str(exc)[:300]}"
