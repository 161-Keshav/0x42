import argparse
import json
from skill_erosion.config import ROOT,load_taxonomy
from skill_erosion.logging_utils import configure_logging
from skill_erosion.runtime import create_pipeline
from skill_erosion.data import read_attempts
from skill_erosion.agents.trace_collector.agent import collect_traces
from skill_erosion.agents.parent_chat.agent import parent_chat

def main():
    parser=argparse.ArgumentParser(description="GapTrace: local skill development tracker; no API keys")
    commands=parser.add_subparsers(dest="command",required=True)
    commands.add_parser("seed",help="Idempotently load fixtures and synthetic parent links")
    journey=commands.add_parser("journey",help="Analyze one student and skill")
    journey.add_argument("--student",default="S-W001");journey.add_argument("--skill",default="python.loops")
    commands.add_parser("counts",help="Inspect persistent Chroma item counts")
    chat=commands.add_parser("parent-chat",help="Ask for a scoped supportive update")
    chat.add_argument("--account",default="parent-S-W001");chat.add_argument("--question",default="How can I help with practice?")
    commands.add_parser("mcp",help="Serve the six tools on loopback port 8000")
    args=parser.parse_args();configure_logging("cli")
    if args.command=="mcp":
        from skill_erosion.mcp_server import mcp
        mcp.run(transport="http",host="127.0.0.1",port=8000);return
    p=create_pipeline()
    try:
        if args.command=="seed":
            result=collect_traces(read_attempts(ROOT/"data/synthetic/attempts.json"),p.repo,load_taxonomy())
            for student in p.repo.students(): p.repo.link_parent("parent-"+student,student)
            print(result.model_dump_json(indent=2))
        elif args.command=="journey":
            result=p.run(args.student,args.skill)
            print(result.model_dump_json(indent=2));print(json.dumps(p.metrics(args.student,args.skill),indent=2));print(json.dumps(p.vectors.counts()))
        elif args.command=="counts": print(json.dumps(p.vectors.counts(),indent=2))
        elif args.command=="parent-chat":
            attempts=p.repo.history_for_parent(args.account);skill=sorted({a.skill_id for a in attempts})[0]
            print(parent_chat(args.question,p.for_parent(args.account,skill),p.vectors));print(json.dumps(p.vectors.counts()))
    finally: p.vectors.client.close()
if __name__=="__main__": main()
