# Data-Driven Rule Engine - Cloud Advisor V1

This document explains the design, condition evaluation logic, evidence generation, and savings calculation layer of the Cloud Advisor Rule Engine.

---

## 1. Core Principles

1. **No Cloud SDK Dependencies**: The Rule Engine operates strictly on normalized resource models stored in MongoDB.
2. **Data-Driven Rules**: Rules are stored as JSON definitions in the `rules` collection.
3. **Evidence-Based Output**: Every finding includes a detailed evidence payload explaining why the rule triggered.
4. **Decoupled Savings**: Savings calculation is separated from condition evaluation.

---

## 2. Rule Definition Schema

```json
{
  "rule_id": "AWS-EC2-001",
  "name": "Underutilized EC2 Instance",
  "description": "EC2 instance running with average CPU utilization below 20% over a 14-day lookback window.",
  "provider": "aws",
  "resource_type": "compute_instance",
  "required_data": ["metrics.cpu_average", "metrics.cpu_p95", "cost.monthly"],
  "lookback_window": {
    "value": 14,
    "unit": "days"
  },
  "conditions": {
    "logic": "AND",
    "items": [
      {
        "field": "metrics.cpu_average",
        "operator": "lt",
        "threshold": 20.0
      },
      {
        "field": "configuration.state",
        "operator": "eq",
        "threshold": "running"
      }
    ]
  },
  "recommendation": {
    "type": "RIGHTSIZING_REVIEW",
    "action_template": "Downsize instance from {configuration.instance_type} to a smaller SKU after verifying peak workload."
  },
  "savings_calculation": {
    "type": "ESTIMATED_PERCENTAGE",
    "percentage": 50.0
  },
  "severity": "medium",
  "status": "active",
  "provenance": "DERIVED"
}
```

---

## 3. Supported Operators

### Comparison Operators
- `eq`: Equal (`==`)
- `neq`: Not Equal (`!=`)
- `gt`: Greater Than (`>`)
- `gte`: Greater Than or Equal (`>=`)
- `lt`: Less Than (`<`)
- `lte`: Less Than or Equal (`<=`)
- `in`: In List (`in`)
- `not_in`: Not In List (`not in`)

### Logical Operators
- `AND`: All items in condition list must evaluate to `True`.
- `OR`: At least one item in condition list must evaluate to `True`.

---

## 4. Execution Pipeline

```text
RuleEngine.evaluate_account(account_id)
   │
   ├── 1. Load active rules from MongoDB `rules` collection
   ├── 2. Query normalized resources matching (user_id, account_id)
   ├── 3. For each resource:
   │      ├── Match rules where rule.resource_type == resource.resource_type
   │      ├── Evaluate rule conditions against resource dot-notation fields
   │      └── If conditions evaluate to TRUE:
   │             ├── Generate Evidence payload (actual vs threshold)
   │             ├── Calculate Estimated Monthly & Annual Savings
   │             └── Upsert Finding in MongoDB `findings` collection
   └── 4. Return Scan Summary (scanned count, rules evaluated, findings generated, total savings)
```
