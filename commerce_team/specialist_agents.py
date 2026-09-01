"""Executable specialist agents for the independent commerce team."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentResult:
    agent:str; status:str; output:dict[str,Any]=field(default_factory=dict); missing_connections:list[str]=field(default_factory=list)

class CommerceSpecialistAgent:
    name='CommerceSpecialistAgent'; capabilities:tuple[str,...]=()
    def __init__(self,tools=None): self.tools=tools or {}
    def connection_status(self): return {c:c in self.tools for c in self.capabilities}
    def missing(self): return [c for c in self.capabilities if c not in self.tools]
    def run(self,context):
        missing=self.missing()
        if missing: return AgentResult(self.name,'CONNECTION_REQUIRED',{'context_received':bool(context)},missing)
        return AgentResult(self.name,'READY',{'context_received':bool(context)})

class TrendScoutAgent(CommerceSpecialistAgent):
    name='TrendScoutAgent'; capabilities=('web_search','social_trends','marketplace_search')
    def run(self,c):
        m=self.missing()
        if m:return AgentResult(self.name,'CONNECTION_REQUIRED',{},m)
        q=c.get('query') or c.get('goal') or 'منتجات وخدمات رائجة في السعودية'
        output={'web':self.tools['web_search'](q),'social':self.tools['social_trends'](q),'marketplaces':self.tools['marketplace_search'](q)}
        if not any(output.values()):
            return AgentResult(self.name,'NO_DATA',output)
        return AgentResult(self.name,'COMPLETED',output)
class MarketAnalystAgent(CommerceSpecialistAgent): name='MarketAnalystAgent'; capabilities=('web_search','marketplace_search')
class CompetitorIntelAgent(CommerceSpecialistAgent): name='CompetitorIntelAgent'; capabilities=('web_search','social_search','ad_library_search')
class SourcingAgent(CommerceSpecialistAgent): name='SourcingAgent'; capabilities=('supplier_search','shipping_quotes','web_search')
class ProfitAgent(CommerceSpecialistAgent):
    name='ProfitAgent'; capabilities=('calculator',)
    def run(self,c):
        m=self.missing()
        if m:return AgentResult(self.name,'CONNECTION_REQUIRED',{},m)
        cost=float(c.get('cost',0)); price=float(c.get('price',0)); fees=float(c.get('fees',0)); margin=price-cost-fees
        return AgentResult(self.name,'COMPLETED',{'cost':cost,'price':price,'fees':fees,'profit_per_unit':margin,'margin_percent':(margin/price*100 if price else 0)})
class StoreBuilderAgent(CommerceSpecialistAgent): name='StoreBuilderAgent'; capabilities=('storefront','catalog','payment_gateway')
class CreativeAgent(CommerceSpecialistAgent): name='CreativeAgent'; capabilities=('copywriting','design')
class GrowthAgent(CommerceSpecialistAgent): name='GrowthAgent'; capabilities=('social_publish','ads_manager','analytics')
class OptimizationAgent(CommerceSpecialistAgent): name='OptimizationAgent'; capabilities=('analytics','storefront')
class CustomerServiceAgent(CommerceSpecialistAgent): name='CustomerServiceAgent'; capabilities=('customer_messages','order_lookup','knowledge_base')
class OrdersPaymentsAgent(CommerceSpecialistAgent): name='OrdersPaymentsAgent'; capabilities=('orders','payment_gateway','shipping')
AGENT_CLASSES={'trend_scout':TrendScoutAgent,'market_analyst':MarketAnalystAgent,'competitor_intel':CompetitorIntelAgent,'sourcing':SourcingAgent,'profit':ProfitAgent,'store_builder':StoreBuilderAgent,'creative':CreativeAgent,'growth':GrowthAgent,'optimizer':OptimizationAgent,'customer_service':CustomerServiceAgent,'orders_payments':OrdersPaymentsAgent}
