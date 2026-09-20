from skill_erosion.logging_utils import logged_agent
from skill_erosion.contracts.models import MisconceptionCluster
SIMILARITY_THRESHOLD=.60

@logged_agent
def cluster_misconceptions(attempts, vectors, student_id, skill_id):
    latest={}
    for a in attempts:
        if a.student_id==student_id and a.skill_id==skill_id:
            if a.attempt_id not in latest or a.version>latest[a.attempt_id].version: latest[a.attempt_id]=a
    vectors.upsert_attempts(list(latest.values()))
    wrong=sorted([a for a in latest.values() if a.assistance=="unassisted" and a.correctness<.6 and a.response_text.strip()],key=lambda a:a.evidence_id)
    if len(wrong)<2: return []
    # Complete-link threshold grouping: every pair in a group is semantically similar.
    # Similarity comes from real Chroma embeddings; no keyword matching is used.
    scores={a.evidence_id:{i:s for i,s,_ in vectors.similar_attempts(a.response_text,student_id,skill_id)} for a in wrong}
    groups=[]
    for a in wrong:
        target=next((g for g in groups if all(scores[a.evidence_id].get(b.evidence_id,-1)>=SIMILARITY_THRESHOLD for b in g)),None)
        if target is None: groups.append([a])
        else: target.append(a)
    clusters=[]
    for group in groups:
        if len(group)<2: continue
        matches=vectors.find_resources(group[0].response_text)
        summary=(matches[0][0].title+". "+matches[0][0].description) if matches and matches[0][1]>=.35 else "Repeated independent reasoning difficulty: "+group[0].response_text[:240]
        clusters.append(MisconceptionCluster(student_id=student_id,skill_id=skill_id,concept_summary=summary,
          evidence_attempt_ids=[a.evidence_id for a in group],embedding_model_version=vectors.model_version))
    return clusters
