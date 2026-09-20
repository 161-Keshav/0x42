from skill_erosion.logging_utils import logged_agent
"""Scoped input only: no repository, account lookup or student selector."""
import logging
import os
import re
FORBIDDEN_PATTERN=re.compile(r"cheat\w*|flag\w*|score\w*|confidence|cluster\w*|peer\w*|compar\w*|rank\w*|other students?|\d|%",re.I)
SAFE_REPLY="Your child can benefit from a calm conversation about learning. Ask what felt manageable and what support would help, then agree on a next step with their teacher."
STATUS_NOTE={"widening":"Supported and independent work are moving further apart.",
  "narrowing":"Supported and independent work are moving closer together.",
  "stable":"The recent learning pattern is steady.",
  "contradictory":"Recent check-ins show a mixed pattern.",
  "insufficient_data":"There is not enough paired learning history for an update yet."}
log=logging.getLogger("skill_erosion")

def filter_parent_answer(answer):
    # A model can be made to answer on-topic; it cannot be trusted to police its
    # own leakage. This filter runs on every answer, template or model-written.
    return SAFE_REPLY if FORBIDDEN_PATTERN.search(answer) else answer

def _template_answer(question,journey,vectors):
    if any(word in question for word in ("help","practice","support","exercise")):
        answer="Invite your child to explain one small idea in their own words. Keep practice brief and encouraging, and ask their teacher which next step would fit best."
        if vectors is not None:
            matches=vectors.find_resources(journey.trend.skill_id.replace("."," ")+" practice "+question)
            if matches and matches[0][1]>=.35: answer+=" A relevant practice resource is available for their teacher to review."
        return answer
    if any(word in question for word in ("progress","status","learning","doing","update")):
        return STATUS_NOTE[journey.trend.status]+" A teacher conversation can help decide what support is useful."
    return SAFE_REPLY

def _retrieved_context(question,journey,vectors):
    """The corpus boundary for this agent: retrieved text comes back as scored
    matches, never as something the model is allowed to treat as instructions."""
    if vectors is None: return []
    matches=vectors.find_resources(journey.trend.skill_id.replace("."," ")+" "+question)
    return [r.title+": "+r.description for r,score in matches[:3] if score>=.35]

def _llm_answer(question,journey,context):
    """Optional generation step, local model first, then OpenRouter, then None
    (the deterministic template). Any failure at either step falls through
    rather than breaking the portal."""
    system=("You help a parent understand their child's learning pattern in one short, "
            "warm paragraph (3-4 sentences). Never mention a score, percentage, confidence "
            "level, ranking, or any comparison to other students. Do not name specific numbers. "
            "Use the CONTEXT only as background; if it does not answer the question, say so plainly.")
    user=(f"Parent question: {question}\n\n"
          f"Learning trend for this skill: {journey.trend.status.replace('_',' ')}\n\n"
          "CONTEXT (retrieved practice notes, may be empty):\n" + ("\n".join(context) or "(none retrieved)"))
    messages=[{"role":"system","content":system},{"role":"user","content":user}]

    local_url=os.environ.get("LOCAL_LLM_URL","").strip()
    if local_url:
        try:
            import httpx
            model=os.environ.get("LOCAL_LLM_MODEL","llama3.2:3b").strip()
            response=httpx.post(local_url,timeout=30.0,
                json={"model":model,"max_tokens":220,"temperature":.3,"messages":messages})
            if response.status_code==200:
                text=response.json()["choices"][0]["message"]["content"].strip()
                if text: return text
            log.warning("parent_chat local llm fallback status=%d",response.status_code)
        except Exception as exc:
            log.warning("parent_chat local llm fallback error_type=%s",type(exc).__name__)

    api_key=os.environ.get("OPENROUTER_API_KEY","").strip()
    if not api_key: return None
    try:
        import httpx
        model=os.environ.get("SLICE_MODEL","inclusionai/ling-3.0-flash").strip()
        response=httpx.post("https://openrouter.ai/api/v1/chat/completions",timeout=20.0,
            headers={"Authorization":f"Bearer {api_key}"},
            json={"model":model,"max_tokens":220,"temperature":.3,"messages":messages})
        if response.status_code!=200:
            log.warning("parent_chat llm fallback status=%d",response.status_code); return None
        return response.json()["choices"][0]["message"]["content"].strip() or None
    except Exception as exc:
        log.warning("parent_chat llm fallback error_type=%s",type(exc).__name__)
        return None

@logged_agent
def parent_chat(question, journey, vectors=None):
    question=question.lower().strip()
    context=_retrieved_context(question,journey,vectors)
    answer=_llm_answer(question,journey,context) or _template_answer(question,journey,vectors)
    return filter_parent_answer(answer)
