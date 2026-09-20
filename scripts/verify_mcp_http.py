"""Real HTTP transport proof, with isolated server/client stores."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from fastmcp import Client
from skill_erosion.config import ROOT,load_taxonomy
from skill_erosion.data import read_attempts
from skill_erosion.runtime import create_pipeline
from skill_erosion.agents.trace_collector.agent import collect_traces

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with socket.socket() as sock: sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
        endpoint=f"http://127.0.0.1:{port}/mcp"
        env=os.environ.copy();env["SKILL_EROSION_DATA_DIR"]=str(root/"server");env.pop("SKILL_EROSION_MCP_URL",None)
        log=(ROOT/"docs/verification/mcp-http-server.txt").open("w",encoding="utf-8")
        code=f"from skill_erosion.mcp_server import mcp; mcp.run(transport='http',host='127.0.0.1',port={port})"
        process=subprocess.Popen([sys.executable,"-c",code],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        pipeline=create_pipeline(root/"client")
        try:
            deadline=time.monotonic()+30
            while True:
                with socket.socket() as sock:
                    if sock.connect_ex(("127.0.0.1",port))==0: break
                if process.poll() is not None or time.monotonic()>deadline: raise RuntimeError("MCP server did not start")
                time.sleep(.1)
            async def tool_names():
                async with Client(endpoint) as client: return sorted(t.name for t in await client.list_tools())
            print("HTTP TOOLS",json.dumps(asyncio.run(tool_names())))
            rows=[r for r in read_attempts(ROOT/"data/synthetic/attempts.json") if r["student_id"]=="S-W001" and r["skill_id"]=="python.loops"]
            collect_traces(rows,pipeline.repo,load_taxonomy())
            # Verify the documented environment variable selects actual HTTP execution.
            os.environ["SKILL_EROSION_MCP_URL"]=endpoint
            from skill_erosion.orchestration.pipeline import Pipeline
            remote=Pipeline(pipeline.repo,pipeline.vectors)
            journey=remote.run("S-W001","python.loops")
            assert journey.trend.status=="widening" and journey.remediation[0].status=="ready"
            pipeline.repo.set_decision("S-W001","python.loops","intervene")
            alternative=remote.alternative(journey,journey.remediation[0].resource_ids)
            assert alternative.status=="ready" and alternative.resource_ids!=journey.remediation[0].resource_ids
            print("HTTP JOURNEY",journey.trend.status,journey.verification.verdict,"remediation",journey.remediation[0].status)
            print("HTTP ALTERNATIVE",alternative.status,alternative.resource_ids)
            print("SKILL_EROSION_MCP_URL execution: VERIFIED")
        finally:
            pipeline.vectors.client.close();process.terminate();process.wait(timeout=15);log.close()
            os.environ.pop("SKILL_EROSION_MCP_URL",None)
        from skill_erosion.embeddings.chroma import ChromaStore
        server_vectors=ChromaStore(root/"server/processed/chroma")
        counts=server_vectors.counts();print("HTTP SERVER COLLECTIONS",json.dumps(counts))
        assert counts=={"skill-erosion-attempts":10,"skill-erosion-resources":8}
        server_vectors.client.close()
if __name__=="__main__": main()
