"""Independent Commerce Manager and specialist-agent hierarchy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


FINANCIAL_RULE = (
    "Never purchase inventory, pay a supplier, subscribe, launch paid ads, "
    "transfer money, issue refunds, or perform any financial transaction without "
    "the user's explicit approval for that specific amount/action."
)


@dataclass(frozen=True)
class Specialist:
    name: str
    mission: str


SPECIALISTS = {
    "trend_scout": Specialist("TrendScoutAgent", "Detect rising/viral products and services and demand signals."),
    "market_analyst": Specialist("MarketAnalystAgent", "Validate demand, customer segments, pricing and market size; reject weak opportunities."),
    "competitor_intel": Specialist("CompetitorIntelAgent", "Track competitors, offers, pricing, positioning, creatives and gaps."),
    "sourcing": Specialist("SourcingAgent", "Find fastest, cheapest and lowest-risk sourcing routes and suppliers; calculate landed cost."),
    "profit": Specialist("ProfitAgent", "Calculate unit economics, fees, break-even, margin and risk before launch."),
    "store_builder": Specialist("StoreBuilderAgent", "Choose sales channel and prepare storefront/page structure, product listing and checkout/payment setup plan."),
    "creative": Specialist("CreativeAgent", "Produce sales copy, organic social content briefs and advertising creatives."),
    "growth": Specialist("GrowthAgent", "Plan and operate social campaigns, targeting, tests and budget allocation subject to financial approval."),
    "optimizer": Specialist("OptimizationAgent", "Measure traffic, conversion, CAC/ROAS and recommend or execute non-financial optimizations."),
}


class CommerceManager:
    """Top-level manager for an autonomous commerce operation.

    The manager owns routing and stage gates. Specialist tool implementations can
    be attached as callables while the financial gate remains centralized.
    """

    def __init__(self) -> None:
        self.specialists = SPECIALISTS
        self.financial_rule = FINANCIAL_RULE

    def organization(self) -> dict[str, Any]:
        return {
            "manager": "CommerceManager",
            "specialists": {key: {"name": value.name, "mission": value.mission} for key, value in self.specialists.items()},
            "financial_rule": self.financial_rule,
        }

    def workflow(self) -> list[str]:
        return [
            "trend_scout",
            "market_analyst",
            "competitor_intel",
            "sourcing",
            "profit",
            "store_builder",
            "creative",
            "growth",
            "optimizer",
        ]

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

    def route(self, stage: str) -> Specialist:
        if stage not in self.specialists:
            raise ValueError(f"Unknown commerce stage: {stage}")
        return self.specialists[stage]
