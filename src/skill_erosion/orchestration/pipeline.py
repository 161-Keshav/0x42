import asyncio
import os
from skill_erosion.contracts.models import TrendReport, FlagVerification, MisconceptionCluster, RemediationPlan, FlagExplanation, JourneyResult
from skill_erosion.agents.divergence_scoring.agent import score_divergence
from skill_erosion.agents.verification.agent import verify_flag
from skill_erosion.agents.misconception_clustering.agent import cluster_misconceptions
from skill_erosion.agents.remediation.agent import recommend_remediation
from skill_erosion.agents.explanation.agent import explain_flag
from skill_erosion.metrics import calculate_metrics
from skill_erosion.config import skill_map

class Pipeline:
    def __init__(self,repo,vectors,mcp_url=None):
        self.repo=repo; self.vectors=vectors
        self.mcp_url=mcp_url if mcp_url is not None else os.environ.get("SKILL_EROSION_MCP_URL")
    def run(self,student_id,skill_id):
        attempts=self.repo.history(student_id,skill_id)
        if not attempts: raise ValueError("No assessment evidence for this student and skill")
        if self.mcp_url: journey=asyncio.run(self._remote(student_id,skill_id))
        else:
            self.vectors.ensure_resources()
            trend=score_divergence(attempts,student_id,skill_id)
            verification=verify_flag(trend)
            clusters=cluster_misconceptions(attempts,self.vectors,student_id,skill_id)
            plans=[] if self.repo.get_decision(student_id,skill_id)=="dismiss" else [recommend_remediation(c,self.vectors) for c in clusters]
            explanation=explain_flag(trend,verification,clusters)
            journey=JourneyResult(trend=trend,verification=verification,clusters=clusters,remediation=plans,explanation=explanation)
        self.repo.save_analysis(journey)
        return journey
    def metrics(self,student_id,skill_id):
        primary=self.repo.history(student_id,skill_id)
        related=skill_map()[skill_id]["related_skills"]
        # Pass the related evidence through the PUBLIC aggregator, not just the inner helper.
        related_id=next((s for s in related if self.repo.history(student_id,s)),None)
        return calculate_metrics(primary,related_skill_id=related_id,
          related_skill_attempts=self.repo.history(student_id,related_id) if related_id else None)
    def student_plans(self,journey):
        t=journey.trend
        return journey.remediation if self.repo.get_decision(t.student_id,t.skill_id)=="intervene" else []
    def alternative(self,journey,excluded_resource_ids):
        if self.repo.get_decision(journey.trend.student_id,journey.trend.skill_id)!="intervene":
            return RemediationPlan(status="insufficient_evidence")
        # The portal displays the first ready plan, which need not be cluster zero.
        index=next((i for i,p in enumerate(journey.remediation) if p.status=="ready"),None)
        if index is None or index>=len(journey.clusters): return RemediationPlan(status="insufficient_evidence")
        cluster=journey.clusters[index]
        if self.mcp_url: return asyncio.run(self._remote_alternative(cluster,excluded_resource_ids))
        return recommend_remediation(cluster,self.vectors,excluded_resource_ids)
    async def _remote_alternative(self,cluster,excluded_resource_ids):
        from fastmcp import Client
        async with Client(self.mcp_url) as client:
            result=await client.call_tool("recommend_remediation",{"cluster":cluster.model_dump(),"excluded_resource_ids":list(excluded_resource_ids)})
            return RemediationPlan.model_validate(result.data)
    def for_parent(self,parent_account_id,skill_id,requested_student_id=None):
        self.repo.history_for_parent(parent_account_id,requested_student_id)
        return self.run(self.repo.get_linked_student(parent_account_id),skill_id)
    async def _remote(self,student_id,skill_id):
        from fastmcp import Client
        async with Client(self.mcp_url) as client:
            async def call(name,payload):
                result=await client.call_tool(name,payload)
                return result.data
            # Replay full versions so a fresh MCP server receives consecutive revisions.
            records=[a.model_dump() for a in self.repo.versions(student_id,skill_id)]
            await call("collect_traces",{"records":records})
            trend=TrendReport.model_validate(await call("score_divergence",dict(student_id=student_id,skill_id=skill_id)))
            verification=FlagVerification.model_validate(await call("verify_flag",{"trend":trend.model_dump()}))
            cluster_data=await call("cluster_misconceptions",dict(student_id=student_id,skill_id=skill_id))
            clusters=[MisconceptionCluster.model_validate(c) for c in cluster_data["clusters"]]
            plans=[]
            if self.repo.get_decision(student_id,skill_id)!="dismiss":
                for c in clusters:
                    plans.append(RemediationPlan.model_validate(await call("recommend_remediation",{"cluster":c.model_dump(),"excluded_resource_ids":[]})))
            explanation=FlagExplanation.model_validate(await call("explain_flag",{"trend":trend.model_dump(),"verification":verification.model_dump(),"clusters":[c.model_dump() for c in clusters]}))
            return JourneyResult(trend=trend,verification=verification,clusters=clusters,remediation=plans,explanation=explanation)
