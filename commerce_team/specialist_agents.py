"""Executable specialist agents for the independent commerce team.

Each agent exposes a concrete job contract and the external capabilities it needs.
Adapters can be connected incrementally without changing the manager hierarchy.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    agent: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    missing_connections: list[str] = field(default_factory=list)


class CommerceSpecialistAgent:
    name = "CommerceSpecialistAgent"
    capabilities: tuple[str, ...] = ()

    def __init__(self, tools: dict[str, Any] | None = None) -> None:
        self.tools = tools or {}

    def connection_status(self) -> dict[str, bool]:
        return {cap: cap in self.tools for cap in self.capabilities}

    def missing(self) -> list[str]:
        return [cap for cap in self.capabilities if cap not in self.tools]

    def run(self, context: dict[str, Any]) -> AgentResult:
        missing = self.missing()
        return AgentResult(self.name, "READY" if not missing else "CONNECTION_REQUIRED", {"context_received": bool(context)}, missing)


class TrendScoutAgent(CommerceSpecialistAgent):
    name = "TrendScoutAgent"
    capabilities = ("web_search", "social_trends", "marketplace_search")


class MarketAnalystAgent(CommerceSpecialistAgent):
    name = "MarketAnalystAgent"
    capabilities = ("web_search", "marketplace_search")


class CompetitorIntelAgent(CommerceSpecialistAgent):
    name = "CompetitorIntelAgent"
    capabilities = ("web_search", "social_search", "ad_library_search")


class SourcingAgent(CommerceSpecialistAgent):
    name = "SourcingAgent"
    capabilities = ("supplier_search", "shipping_quotes", "web_search")


class ProfitAgent(CommerceSpecialistAgent):
    name = "ProfitAgent"
    capabilities = ("calculator",)


class StoreBuilderAgent(CommerceSpecialistAgent):
    name = "StoreBuilderAgent"
    capabilities = ("storefront", "catalog", "payment_gateway")


class CreativeAgent(CommerceSpecialistAgent):
    name = "CreativeAgent"
    capabilities = ("copywriting", "design")


class GrowthAgent(CommerceSpecialistAgent):
    name = "GrowthAgent"
    capabilities = ("social_publish", "ads_manager", "analytics")


class OptimizationAgent(CommerceSpecialistAgent):
    name = "OptimizationAgent"
    capabilities = ("analytics", "storefront")


class CustomerServiceAgent(CommerceSpecialistAgent):
    name = "CustomerServiceAgent"
    capabilities = ("customer_messages", "order_lookup", "knowledge_base")


class OrdersPaymentsAgent(CommerceSpecialistAgent):
    name = "OrdersPaymentsAgent"
    capabilities = ("orders", "payment_gateway", "shipping")


AGENT_CLASSES = {
    "trend_scout": TrendScoutAgent,
    "market_analyst": MarketAnalystAgent,
    "competitor_intel": CompetitorIntelAgent,
    "sourcing": SourcingAgent,
    "profit": ProfitAgent,
    "store_builder": StoreBuilderAgent,
    "creative": CreativeAgent,
    "growth": GrowthAgent,
    "optimizer": OptimizationAgent,
    "customer_service": CustomerServiceAgent,
    "orders_payments": OrdersPaymentsAgent,
}
