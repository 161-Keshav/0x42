import asyncio
import logging
import os
import tempfile
import unittest
from pathlib import Path
from tests.unit.helpers import history
from skill_erosion.config import load_taxonomy
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.storage.sqlite_repo import SQLiteRepository
from skill_erosion.embeddings.chroma import ChromaStore
from skill_erosion.orchestration.pipeline import Pipeline
class MCPTests(unittest.TestCase):
    def test_all_six_tools_and_remote_orchestration(self):
        from fastmcp import Client
        from skill_erosion.mcp_server import mcp,runtime
        with tempfile.TemporaryDirectory() as tmp:
            prior=os.environ.get("SKILL_EROSION_DATA_DIR"); os.environ["SKILL_EROSION_DATA_DIR"]=str(Path(tmp)/"server")
            runtime.cache_clear()
            vectors=ChromaStore(Path(tmp)/"client-chroma");repo=SQLiteRepository(Path(tmp)/"client.sqlite")
            try:
                collect_traces(history((.3,.5,.7)),repo,load_taxonomy())
                async def names():
                    async with Client(mcp) as client: return {t.name for t in await client.list_tools()}
                self.assertEqual(asyncio.run(names()),{"collect_traces","score_divergence","verify_flag","cluster_misconceptions","recommend_remediation","explain_flag"})
                remote_pipeline=Pipeline(repo,vectors,mcp_url=mcp)
                remote=remote_pipeline.run("s1","python.loops")
                repo.set_decision("s1","python.loops","intervene")
                alternative=remote_pipeline.alternative(remote,remote.remediation[0].resource_ids)
                self.assertEqual(alternative.status,"ready")
                self.assertNotEqual(alternative.resource_ids,remote.remediation[0].resource_ids)
                local=Pipeline(repo,vectors,mcp_url="").run("s1","python.loops")
                self.assertEqual(remote,local)
            finally:
                vectors.client.close()
                if runtime.cache_info().currsize: runtime().vectors.client.close()
                runtime.cache_clear()
                logger=logging.getLogger("skill_erosion")
                for h in logger.handlers[:]: logger.removeHandler(h);h.close()
                if prior is None: os.environ.pop("SKILL_EROSION_DATA_DIR",None)
                else: os.environ["SKILL_EROSION_DATA_DIR"]=prior
