from typing import Any

class RuleOperators:

    @staticmethod
    def eq(value: Any, threshold: Any) -> bool:
        return value == threshold

    @staticmethod
    def neq(value: Any, threshold: Any) -> bool:
        return value != threshold

    @staticmethod
    def gt(value: Any, threshold: Any) -> bool:
        try:
            return float(value) > float(threshold)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def gte(value: Any, threshold: Any) -> bool:
        try:
            return float(value) >= float(threshold)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def lt(value: Any, threshold: Any) -> bool:
        try:
            return float(value) < float(threshold)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def lte(value: Any, threshold: Any) -> bool:
        try:
            return float(value) <= float(threshold)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def in_op(value: Any, threshold: Any) -> bool:
        if isinstance(threshold, list):
            return value in threshold
        return str(value) in str(threshold)

    @staticmethod
    def not_in_op(value: Any, threshold: Any) -> bool:
        if isinstance(threshold, list):
            return value not in threshold
        return str(value) not in str(threshold)

    @classmethod
    def evaluate(cls, operator_name: str, value: Any, threshold: Any) -> bool:
        operator_map = {
            "eq": cls.eq,
            "neq": cls.neq,
            "gt": cls.gt,
            "gte": cls.gte,
            "lt": cls.lt,
            "lte": cls.lte,
            "in": cls.in_op,
            "not_in": cls.not_in_op
        }
        handler = operator_map.get(operator_name.lower())
        if not handler:
            raise ValueError(f"Unsupported operator: {operator_name}")
        return handler(value, threshold)
