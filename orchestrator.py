"""Top-level manager for the hierarchical autonomous agent team."""
from __future__ import annotations
import argparse, json, logging, os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any
from zoneinfo import ZoneInfo
from openai import OpenAI
from agents import BusinessManager, ContentAgent, CreativeLearningManager, EcommerceAgent, ExecutionAgent, LearningAgent, ResearchAgent, TravelAgent, VideoAgent

DIVISION_MAP={"creative_learning":CreativeLearningManager,"business":BusinessManager,"general":ExecutionAgent}
DIVISION_SPECIALISTS={"creative_learning":{"content":ContentAgent,"video":VideoAgent,"learning":LearningAgent,"research":ResearchAgent},"business":{"travel":TravelAgent,"ecommerce":EcommerceAgent,"research":ResearchAgent},"general":{"execution":ExecutionAgent,"research":ResearchAgent}}
ROUTER_SYSTEM_PROMPT='''You are the GENERAL MANAGER of a hierarchical autonomous agent team. Route each request first to ONE division manager, then to the smallest useful set of specialists. Calendar, appointments, meetings, and personal schedule requests MUST route to business with travel specialist. Return JSON only: {"division":"creative_learning|business|general","specialists":["..."],"reason":"..."}. Allowed specialists: creative_learning: content,video,learning,research; business: travel,ecommerce,research; general: execution,research. MANDATORY GLOBAL FINANCIAL RULE: any financial action requires explicit approval for that specific action.'''
SYNTHESIS_SYSTEM_PROMPT='''You are the GENERAL MANAGER. Combine only confirmed results. Never invent calendar events or claim an external action occurred unless a tool confirmed it. For calendar tasks, the specialist output beginning CONFIRMED GOOGLE CALENDAR is the authoritative source and overrides any division-manager speculation. If that confirmed result contains one or more events, NEVER say there are no events. If it says no events, do not invent any. Preserve confirmed dates, times, locations and reminders exactly. If a calendar tool confirms an action, state that it was completed and do not tell the user to do it manually. Financial actions require explicit specific approval.'''
CALENDAR_CREATE_PROMPT='''Extract a Google Calendar event from the user's request. Current local date/time in Asia/Riyadh is supplied. Resolve Arabic relative dates. Return JSON only with: summary, location, start_local, end_local, reminder_minutes. start_local/end_local must be YYYY-MM-DDTHH:MM:SS. If duration is unstated use 60 minutes. Parse ساعة وربع=75, ساعة=60, نصف ساعة=30. Do not invent a different date or time.'''
CALENDAR_MUTATE_PROMPT='''You are selecting and modifying an existing Google Calendar event. You receive the user's request, current Asia/Riyadh time, and a numbered JSON list of actual events. Return JSON only with: event_index (zero-based integer of the ONE matching event), patch (object). For delete requests patch must be {}. For update requests patch may contain summary, location, start_local, end_local, reminder_minutes ONLY when requested. Resolve relative dates against current time. Preserve unspecified fields by omitting them from patch. If no unique match exists return event_index=-1 and patch={}. Never guess among multiple plausible events.'''

@dataclass
class WorkflowPlan: division:str; specialists:list[str]; reason:str

class Orchestrator:
    def __init__(self,model:str="gpt-4o-mini",client:Any|None=None,agent_model:str|None=None)->None:
        self.model=model; self.agent_model=agent_model or model; self.logger=logging.getLogger("general_manager"); self.client=client or OpenAI(api_key=self._get_api_key())
    @staticmethod
    def _get_api_key()->str:
        key=os.environ.get("OPENAI_API_KEY")
        if not key: raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
        return key
    def plan(self,task:str)->WorkflowPlan:
        r=self.client.chat.completions.create(model=self.model,response_format={"type":"json_object"},messages=[{"role":"system","content":ROUTER_SYSTEM_PROMPT},{"role":"user","content":task}]); d=json.loads(r.choices[0].message.content or "{}"); division=d.get("division","general"); division=division if division in DIVISION_MAP else "general"; allowed=DIVISION_SPECIALISTS[division]; specialists=[]
        for n in d.get("specialists",[]):
            if n in allowed and n not in specialists:specialists.append(n)
        if not specialists:specialists=[next(iter(allowed))]
        return WorkflowPlan(division,specialists,d.get("reason",""))
    def _run_agent(self,cls:Any,task:str)->str:return cls(model=self.agent_model,client=self.client).run(task)
    @staticmethod
    def _calendar_kind(task:str)->str|None:
        t=task.lower();cal=("تقويم","مواعيد","موعد","calendar","appointment","schedule","meeting")
        if not any(w in t for w in cal):return None
        if any(w in t for w in ("أضف","اضف","أنشئ","انشئ","سجل","create","add")):return "create"
        if any(w in t for w in ("احذف","ألغي","الغ","delete","cancel")):return "delete"
        if any(w in t for w in ("عدّل","عدل","غيّر","غير","update","change")):return "update"
        return "read"
    def _travel(self)->TravelAgent:return TravelAgent(model=self.agent_model,client=self.client)
    def _window_events(self,days_back:int=30,days_forward:int=365)->list[dict[str,Any]]:
        now=datetime.now(timezone.utc);return self._travel().calendar_events((now-timedelta(days=days_back)).isoformat(),(now+timedelta(days=days_forward)).isoformat(),max_results=250)
    def _calendar_read(self)->str:
        now=datetime.now(timezone.utc);events=self._travel().calendar_events(now.isoformat(),(now+timedelta(days=7)).isoformat())
        if not events:return "CONFIRMED GOOGLE CALENDAR RESULT: No events found in the next seven days."
        return "CONFIRMED GOOGLE CALENDAR RESULT:\n"+json.dumps([{"summary":e.get("summary"),"start":e.get("start",{}),"end":e.get("end",{}),"location":e.get("location")} for e in events],ensure_ascii=False)
    def _calendar_create(self,task:str)->str:
        tz=ZoneInfo("Asia/Riyadh");now=datetime.now(tz);r=self.client.chat.completions.create(model=self.model,response_format={"type":"json_object"},messages=[{"role":"system","content":CALENDAR_CREATE_PROMPT},{"role":"user","content":f"Current Asia/Riyadh time: {now.isoformat()}\nRequest: {task}"}]);d=json.loads(r.choices[0].message.content or "{}")
        if any(not d.get(k) for k in ("summary","start_local","end_local")):raise ValueError("Calendar event details are incomplete; event was not created.")
        start=datetime.fromisoformat(d["start_local"]).replace(tzinfo=tz);end=datetime.fromisoformat(d["end_local"]).replace(tzinfo=tz);body={"summary":d["summary"],"start":{"dateTime":start.isoformat(),"timeZone":"Asia/Riyadh"},"end":{"dateTime":end.isoformat(),"timeZone":"Asia/Riyadh"}}
        if d.get("location"):body["location"]=d["location"]
        if d.get("reminder_minutes") is not None:body["reminders"]={"useDefault":False,"overrides":[{"method":"popup","minutes":int(d["reminder_minutes"])}]}
        e=self._travel().add_calendar_event(body);return "CONFIRMED GOOGLE CALENDAR CREATE RESULT:\n"+json.dumps({"id":e.get("id"),"summary":e.get("summary"),"start":e.get("start"),"end":e.get("end"),"location":e.get("location"),"reminders":e.get("reminders"),"htmlLink":e.get("htmlLink")},ensure_ascii=False)
    def _select_existing(self,task:str)->tuple[dict[str,Any]|None,dict[str,Any]]:
        events=self._window_events();compact=[{"summary":e.get("summary"),"start":e.get("start",{}),"end":e.get("end",{}),"location":e.get("location")} for e in events];tz=ZoneInfo("Asia/Riyadh");now=datetime.now(tz);r=self.client.chat.completions.create(model=self.model,response_format={"type":"json_object"},messages=[{"role":"system","content":CALENDAR_MUTATE_PROMPT},{"role":"user","content":f"Current Asia/Riyadh time: {now.isoformat()}\nRequest: {task}\nEvents: {json.dumps(compact,ensure_ascii=False)}"}]);d=json.loads(r.choices[0].message.content or "{}");idx=d.get("event_index",-1)
        if not isinstance(idx,int) or idx<0 or idx>=len(events):return None,{}
        return events[idx],d.get("patch",{}) or {}
    def _calendar_update(self,task:str)->str:
        event,patch=self._select_existing(task)
        if not event:return "NO CALENDAR CHANGE: Could not uniquely identify the event to update."
        body={};tz=ZoneInfo("Asia/Riyadh")
        if "summary" in patch:body["summary"]=patch["summary"]
        if "location" in patch:body["location"]=patch["location"]
        if "start_local" in patch:body["start"]={"dateTime":datetime.fromisoformat(patch["start_local"]).replace(tzinfo=tz).isoformat(),"timeZone":"Asia/Riyadh"}
        if "end_local" in patch:body["end"]={"dateTime":datetime.fromisoformat(patch["end_local"]).replace(tzinfo=tz).isoformat(),"timeZone":"Asia/Riyadh"}
        if "reminder_minutes" in patch:body["reminders"]={"useDefault":False,"overrides":[{"method":"popup","minutes":int(patch["reminder_minutes"])}]}
        if not body:return "NO CALENDAR CHANGE: No requested update fields were found."
        e=self._travel().update_calendar_event(event["id"],body);return "CONFIRMED GOOGLE CALENDAR UPDATE RESULT:\n"+json.dumps({"id":e.get("id"),"summary":e.get("summary"),"start":e.get("start"),"end":e.get("end"),"location":e.get("location"),"reminders":e.get("reminders")},ensure_ascii=False)
    def _calendar_delete(self,task:str)->str:
        event,_=self._select_existing(task)
        if not event:return "NO CALENDAR CHANGE: Could not uniquely identify the event to delete."
        self._travel().delete_calendar_event(event["id"]);return "CONFIRMED GOOGLE CALENDAR DELETE RESULT: "+json.dumps({"id":event.get("id"),"summary":event.get("summary"),"start":event.get("start")},ensure_ascii=False)
    def _calendar_execute(self,task:str)->str:
        kind=self._calendar_kind(task)
        if kind=="read":return self._calendar_read()
        if kind=="create":return self._calendar_create(task)
        if kind=="update":return self._calendar_update(task)
        if kind=="delete":return self._calendar_delete(task)
        return "NO CALENDAR ACTION."
    def route(self,task:str,agent_name:str)->str:
        for specialists in DIVISION_SPECIALISTS.values():
            if agent_name in specialists:
                if agent_name=="travel" and self._calendar_kind(task):return self._calendar_execute(task)
                return self._run_agent(specialists[agent_name],task)
        if agent_name in DIVISION_MAP:return self._run_agent(DIVISION_MAP[agent_name],task)
        raise ValueError(f"Unknown agent: {agent_name}")
    def synthesize(self,task:str,results:dict[str,str])->str:
        packed="\n\n".join(f"--- {n.upper()} ---\n{v}" for n,v in results.items());r=self.client.chat.completions.create(model=self.model,messages=[{"role":"system","content":SYNTHESIS_SYSTEM_PROMPT},{"role":"user","content":f"Original Task: {task}\n\nResults:\n{packed}"}]);return r.choices[0].message.content or "No synthesis generated."
    def orchestrate(self,task:str)->tuple[WorkflowPlan,str]:
        plan=self.plan(task);manager=self._run_agent(DIVISION_MAP[plan.division],f"GENERAL MANAGER ASSIGNMENT:\n{task}\nSpecialists selected: {', '.join(plan.specialists)}\nCoordinate this division; do not claim unconfirmed execution.");results={f"{plan.division}_manager":manager};context=f"Original task:\n{task}\n\nDivision manager brief:\n{manager}"
        for name in plan.specialists:
            output=self._calendar_execute(task) if plan.division=="business" and name=="travel" and self._calendar_kind(task) else self._run_agent(DIVISION_SPECIALISTS[plan.division][name],context);results[name]=output;context+=f"\n\n{name.upper()} OUTPUT:\n{output}"
        return plan,self.synthesize(task,results)
    def run(self,task:str)->str:return self.orchestrate(task)[1]

def parse_args()->argparse.Namespace:
    p=argparse.ArgumentParser();p.add_argument("task");p.add_argument("--model",default="gpt-4o-mini");p.add_argument("--agent-model",default=None);return p.parse_args()
def main()->None:
    logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(name)s: %(message)s");a=parse_args();print("\n=== FINAL ANSWER ===");print(Orchestrator(model=a.model,agent_model=a.agent_model).run(a.task))
if __name__=="__main__":main()
