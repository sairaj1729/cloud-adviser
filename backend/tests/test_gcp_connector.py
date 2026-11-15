import pytest
from app.providers.gcp.connector import GCPConnector, GCPConnectionResult
from app.normalization.metrics import MetricsNormalizer
from app.normalization.cost import CostNormalizer


def test_gcp_connection_result_truthiness():
    success_res = GCPConnectionResult({"success": True, "message": "All good", "provider": "gcp"})
    fail_res = GCPConnectionResult({"success": False, "error": "Invalid auth", "provider": "gcp"})

    # Test dict indexing
    assert success_res["success"] is True
    assert fail_res["success"] is False
    assert fail_res["error"] == "Invalid auth"

    # Test boolean evaluation (used in FastAPI backend)
    assert bool(success_res) is True
    assert bool(fail_res) is False
    assert success_res.success is True
    assert fail_res.success is False


def test_gcp_connector_init_and_args():
    # Valid init
    conn = GCPConnector(
        project_id="test-cloud-project-123",
        billing_table="my-proj.dataset.gcp_billing_export_v1_000_000",
        region="us-central1"
    )
    assert conn.project_id == "test-cloud-project-123"
    assert conn.billing_table == "my-proj.dataset.gcp_billing_export_v1_000_000"
    assert conn.region == "us-central1"

    # Missing project_id raises ValueError
    with pytest.raises(ValueError):
        GCPConnector(project_id="")


def test_gcp_connector_service_account_json_parsing():
    json_str = '{"type": "service_account", "project_id": "test-p", "private_key": "dummy"}'
    conn = GCPConnector(
        project_id="test-p",
        credentials_info=json_str
    )
    assert conn._credential_info is not None
    assert conn._credential_info["project_id"] == "test-p"


def test_gcp_connector_metrics_and_cost_normalization():
    import asyncio

    async def _async_test():
        conn = GCPConnector(project_id="test-p")

        # When metrics unavailable or non-numeric
        raw_metrics = await conn.get_metrics("non-numeric-id")
        norm_metrics = MetricsNormalizer.normalize_metrics(raw_metrics)
        assert norm_metrics["cpu_average"] == 0.0
        assert norm_metrics["cpu_p95"] == 0.0

        # When billing table not configured
        raw_cost = await conn.get_costs("res-1")
        norm_cost = CostNormalizer.normalize_cost(raw_cost)
        assert norm_cost["monthly"] == 0.0
        assert norm_cost["currency"] == "USD"

        # Context manager
        with conn:
            pass

    asyncio.run(_async_test())


def test_gcp_rules_evaluation():
    from app.normalization.resource import ResourceNormalizer
    from app.rule_engine.evaluator import RuleEvaluator

    # 1. Test GCP Underutilized VM rule (GCP-VM-001)
    gcp_vm = {
        "resource_id": "876543210987654321",
        "resource_type": "compute_instance",
        "name": "data-cruncher-vm",
        "region": "us-central1",
        "configuration": {"instance_type": "n2-standard-4", "state": "RUNNING"},
        "tags": {"environment": "analytics"}
    }
    norm_metrics = MetricsNormalizer.normalize_metrics({"cpu_average": 8.5, "cpu_p95": 14.2})
    norm_cost = CostNormalizer.normalize_cost({"monthly": 98.40, "currency": "USD"})

    norm_vm = ResourceNormalizer.normalize_resource(
        raw_resource=gcp_vm,
        user_id="u1",
        cloud_account_id="acc1",
        provider="gcp",
        account_id="data-platform-prod",
        metrics=norm_metrics,
        cost=norm_cost
    )

    gcp_vm_rule = {
        "rule_id": "GCP-VM-001",
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average", "operator": "lt", "threshold": 15.0},
                {"field": "metrics.cpu_average", "operator": "gt", "threshold": 0.0}
            ]
        }
    }
    is_match, evidence = RuleEvaluator.evaluate_conditions(norm_vm, gcp_vm_rule["conditions"])
    assert is_match is True
    assert evidence[0]["actual_value"] == 8.5
    assert evidence[0]["passed"] is True

    # 2. Test GCP Unattached Disk rule (GCP-DISK-001)
    gcp_disk = {
        "resource_id": "disk-987123",
        "resource_type": "storage_volume",
        "name": "orphan-disk-backup",
        "region": "us-central1",
        "configuration": {"size_gb": 100, "disk_state": "Unattached", "is_attached": False},
        "tags": {}
    }
    norm_disk = ResourceNormalizer.normalize_resource(
        raw_resource=gcp_disk,
        user_id="u1",
        cloud_account_id="acc1",
        provider="gcp",
        account_id="data-platform-prod",
        metrics={"cpu_average": 0.0, "cpu_p95": 0.0},
        cost=CostNormalizer.normalize_cost({"monthly": 15.0, "currency": "USD"})
    )
    gcp_disk_rule = {
        "rule_id": "GCP-DISK-001",
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "cost.monthly", "operator": "gt", "threshold": 0.0}
            ]
        }
    }
    is_disk_match, disk_evidence = RuleEvaluator.evaluate_conditions(norm_disk, gcp_disk_rule["conditions"])
    assert is_disk_match is True

