from skill_erosion.logging_utils import logged_agent
from skill_erosion.contracts.models import RemediationPlan
MIN_RESOURCE_SIMILARITY=.35

@logged_agent
def recommend_remediation(cluster, vectors, excluded_resource_ids=()):
    if len(cluster.evidence_attempt_ids)<2: return RemediationPlan(status="insufficient_evidence")
    matches=vectors.find_resources(cluster.concept_summary,excluded_resource_ids)
    if not matches or matches[0][1]<MIN_RESOURCE_SIMILARITY: return RemediationPlan(status="no_matching_resource")
    resource,_=matches[0]
    return RemediationPlan(status="ready",teacher_summary=resource.teacher_summary,
        student_exercise=resource.student_exercise,resource_ids=[resource.resource_id])
