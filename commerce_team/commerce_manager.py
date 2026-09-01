"""Independent autonomous commerce manager."""
from __future__ import annotations
from typing import Any
from .specialist_agents import AGENT_CLASSES

FINANCIAL_RULE = (
    "Never purchase inventory, pay a supplier, subscribe, launch paid ads, transfer money, "
    "issue refunds, or perform any financial transaction without the user's explicit approval "
    "for that specific amount and action."
)

WORKFLOW = [
    "trend_scout", "market_analyst", "competitor_intel", "sourcing", "profit",
    "store_builder", "creative", "growth", "optimizer", "customer_service", "orders_payments"
]


class CommerceManager:
    """Manager that owns all commerce specialists and their shared tool adapters."""

    def __init__(self, tools: dict[str, Any] | None = None) -> None:
        self.tools = tools or {}
        self.financial_rule = FINANCIAL_RULE
        self.agents = {name: cls(self.tools) for name, cls in AGENT_CLASSES.items()}

    def organization(self) -> dict[str, Any]:
        return {
            "manager": "CommerceManager",
            "independent": True,
            "agents": {
                name: {
                    "class": agent.name,
                    "connections": agent.connection_status(),
                    "missing_connections": agent.missing(),
                }
                for name, agent in self.agents.items()
            },
            "financial_rule": self.financial_rule,
        }

    def workflow(self) -> list[str]:
        return list(WORKFLOW)

    def route(self, stage: str):
        if stage not in self.agents:
            raise ValueError(f"Unknown commerce stage: {stage}")
        return self.agents[stage]

    def run_stage(self, stage: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.route(stage).run(context or {})
        return {
            "agent": result.agent,
            "status": result.status,
            "output": result.output,
            "missing_connections": result.missing_connections,
        }

    def readiness(self) -> dict[str, Any]:
        statuses = self.organization()["agents"]
        missing = sorted({item for data in statuses.values() for item in data["missing_connections"]})
        return {
            "manager_ready": True,
            "specialist_count": len(self.agents),
            "fully_connected": not missing,
            "missing_external_connections": missing,
        }

    @staticmethod
    def require_financial_approval(action: str, amount: float | None = None, currency: str = "SAR") -> dict[str, Any]:
        return {
            "status": "FINANCIAL_APPROVAL_REQUIRED",
            "action": action,
            "amount": amount,
            "currency": currency,
            "approved": False,
            "message": "Explicit approval is required for this specific financial action before execution.",
        }
