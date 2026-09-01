"""Independent autonomous commerce manager."""
from __future__ import annotations
from typing import Any
from .specialist_agents import AGENT_CLASSES
from .tool_adapters import default_free_tools
from .state_store import CommerceStateStore

FINANCIAL_RULE="Never purchase inventory, pay a supplier, subscribe, launch paid ads, transfer money, issue refunds, or perform any financial transaction without the user's explicit approval for that specific amount and action."
WORKFLOW=['trend_scout','market_analyst','competitor_intel','sourcing','profit','store_builder','creative','growth','optimizer','customer_service','orders_payments']

class CommerceManager:
    def __init__(self,tools:dict[str,Any]|None=None,state_path='outputs/commerce/commerce.db'):
        self.tools=default_free_tools(); self.tools.update(tools or {})
        self.financial_rule=FINANCIAL_RULE; self.agents={n:c(self.tools) for n,c in AGENT_CLASSES.items()}; self.state=CommerceStateStore(state_path)
    def organization(self):
        return {'manager':'CommerceManager','independent':True,'agents':{n:{'class':a.name,'connections':a.connection_status(),'missing_connections':a.missing()} for n,a in self.agents.items()},'financial_rule':self.financial_rule}
    def workflow(self): return list(WORKFLOW)
    def route(self,stage):
        if stage not in self.agents: raise ValueError(f'Unknown commerce stage: {stage}')
        return self.agents[stage]
    def run_stage(self,stage,context=None):
        r=self.route(stage).run(context or {}); out={'agent':r.agent,'status':r.status,'output':r.output,'missing_connections':r.missing_connections}; self.state.record(stage,r.status,out); return out
    def readiness(self):
        statuses=self.organization()['agents']; missing=sorted({x for d in statuses.values() for x in d['missing_connections']})
        return {'manager_ready':True,'specialist_count':len(self.agents),'fully_connected':not missing,'connected_free_tools':sorted(self.tools.keys()),'missing_external_connections':missing}
    @staticmethod
    def require_financial_approval(action,amount=None,currency='SAR'):
        return {'status':'FINANCIAL_APPROVAL_REQUIRED','action':action,'amount':amount,'currency':currency,'approved':False,'message':'Explicit approval is required for this specific financial action before execution.'}
