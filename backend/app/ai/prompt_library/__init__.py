"""Prompt Library for Cloud Advisor FinOps Recommendations."""

from app.ai.prompt_library.base import SYSTEM_FINOPS_INSTRUCTION
from app.ai.prompt_library.compute_rightsizing import COMPUTE_RIGHTSIZING_PROMPT
from app.ai.prompt_library.idle_cleanup import IDLE_CLEANUP_PROMPT
from app.ai.prompt_library.storage_optimization import STORAGE_OPTIMIZATION_PROMPT
from app.ai.prompt_library.database_tuning import DATABASE_TUNING_PROMPT
from app.ai.prompt_library.cost_usage_summary import COST_USAGE_SUMMARY_PROMPT

__all__ = [
    "SYSTEM_FINOPS_INSTRUCTION",
    "COMPUTE_RIGHTSIZING_PROMPT",
    "IDLE_CLEANUP_PROMPT",
    "STORAGE_OPTIMIZATION_PROMPT",
    "DATABASE_TUNING_PROMPT",
    "COST_USAGE_SUMMARY_PROMPT"
]

