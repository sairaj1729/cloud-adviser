import logging
from typing import Dict, Any, Optional

from app.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM Provider for local development, automated testing, and offline modes.
    Returns deterministic, high-quality FinOps recommendations without making network calls.
    """
    def __init__(self, model_name: str = "mock-finops-v1", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model_name=model_name, api_key=api_key, base_url=base_url)

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        
        # Determine recommendation based on keywords in context
        if "stop" in prompt_lower or "idle" in prompt_lower or "ec2-002" in prompt_lower or "vm-002" in prompt_lower:
            return {
                "action": "STOP",
                "target_sku": None,
                "estimated_monthly_savings": 120.0,
                "estimated_savings_percentage": 100.0,
                "risk_level": "LOW",
                "justification": "Resource telemetry displays sustained 0% CPU utilization and zero I/O over the lookback window. Stopping this idle instance avoids compute spend without data loss.",
                "remediation_steps": [
                    "Verify with system owner that instance is not scheduled for batch jobs",
                    "Take a snapshot backup of associated root and data disks",
                    "Execute instance stop command via CLI or Cloud Console"
                ],
                "remediation_command": "aws ec2 stop-instances --instance-ids ${RESOURCE_ID}"
            }
        elif "ebs-001" in prompt_lower or "unattached" in prompt_lower or "disk-001" in prompt_lower:
            return {
                "action": "TERMINATE",
                "target_sku": None,
                "estimated_monthly_savings": 45.0,
                "estimated_savings_percentage": 100.0,
                "risk_level": "LOW",
                "justification": "Block storage volume has remained unattached to any virtual machine for over 14 days, accumulating unutilized storage fees.",
                "remediation_steps": [
                    "Confirm volume is not part of a detached snapshot restore strategy",
                    "Create an archival snapshot before deletion",
                    "Delete unattached block volume"
                ],
                "remediation_command": "aws ec2 delete-volume --volume-id ${RESOURCE_ID}"
            }
        elif "storage" in prompt_lower or "low-i/o" in prompt_lower or "ebs-002" in prompt_lower:
            return {
                "action": "STORAGE_DOWNGRADE",
                "target_sku": "gp3",
                "estimated_monthly_savings": 35.0,
                "estimated_savings_percentage": 30.0,
                "risk_level": "LOW",
                "justification": "Volume IOPS and throughput remain well below provisioned tier limits. Migrating to standard gp3 storage provides identical baseline performance at lower cost.",
                "remediation_steps": [
                    "Review 30-day peak IOPS requirements",
                    "Modify volume type to gp3 with baseline 3,000 IOPS and 125 MB/s",
                    "Monitor volume performance for 48 hours"
                ],
                "remediation_command": "aws ec2 modify-volume --volume-id ${RESOURCE_ID} --volume-type gp3"
            }
        else:
            # Default: Rightsizing compute or database
            return {
                "action": "RIGHTSIZE",
                "target_sku": "t4g.xlarge",
                "estimated_monthly_savings": 75.0,
                "estimated_savings_percentage": 45.0,
                "risk_level": "LOW",
                "justification": "Resource exhibits average CPU utilization under 20% with low memory demand. Downsizing to a modern generation instance yields 45% savings while maintaining adequate headroom.",
                "remediation_steps": [
                    "Schedule a brief maintenance window for instance restart",
                    "Update instance type attribute in Terraform or cloud configuration",
                    "Verify application health and metrics after resize"
                ],
                "remediation_command": "aws ec2 modify-instance-attribute --instance-id ${RESOURCE_ID} --instance-type t4g.xlarge"
            }

