import pytest
from app.normalization.resource import ResourceNormalizer
from app.normalization.metrics import MetricsNormalizer
from app.normalization.cost import CostNormalizer
from app.rule_engine.evaluator import RuleEvaluator
from app.rule_engine.evidence import EvidenceGenerator
from app.rule_engine.savings import SavingsCalculator

def test_aws_ec2_normalization_and_rule_evaluation():
    # 1. Mock AWS EC2 API response
    raw_ec2_response = {
        "resource_id": "i-0987654321fedcba0",
        "resource_type": "compute_instance",
        "name": "staging-api-worker",
        "region": "us-east-1",
        "configuration": {"instance_type": "m5.large", "state": "running"},
        "tags": {"Environment": "staging"}
    }
    raw_metrics = {"cpu_average": 12.4, "cpu_p95": 22.1}
    raw_cost = {"monthly": 120.50, "currency": "USD"}

    # 2. Normalize
    norm_metrics = MetricsNormalizer.normalize_metrics(raw_metrics)
    norm_cost = CostNormalizer.normalize_cost(raw_cost)

    normalized_resource = ResourceNormalizer.normalize_resource(
        raw_resource=raw_ec2_response,
        user_id="usr_123",
        cloud_account_id="acc_456",
        provider="aws",
        account_id="123456789012",
        metrics=norm_metrics,
        cost=norm_cost
    )

    assert normalized_resource["provider"] == "aws"
    assert normalized_resource["metrics"]["cpu_average"] == 12.4
    assert normalized_resource["cost"]["monthly"] == 120.50

    # 3. Define Underutilized EC2 Rule
    rule = {
        "rule_id": "AWS-EC2-001",
        "name": "Underutilized EC2 Instance",
        "provider": "aws",
        "resource_type": "compute_instance",
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "metrics.cpu_average", "operator": "lt", "threshold": 20.0}
            ]
        },
        "savings_calculation": {"type": "ESTIMATED_PERCENTAGE", "percentage": 50.0}
    }

    # 4. Evaluate Rule without contacting AWS API
    is_match, evidence_items = RuleEvaluator.evaluate_conditions(
        normalized_resource, rule["conditions"]
    )

    assert is_match is True
    assert len(evidence_items) == 1
    assert evidence_items[0]["passed"] is True

    # 5. Calculate Savings & Evidence
    evidence = EvidenceGenerator.build_evidence(rule, normalized_resource, evidence_items)
    savings = SavingsCalculator.calculate_savings(rule, normalized_resource)

    assert savings["monthly"] == 60.25
    assert savings["annual"] == 723.00
    assert evidence["rule_id"] == "AWS-EC2-001"
