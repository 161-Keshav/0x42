from datetime import datetime, timedelta, timezone

def record(i=0, **changes):
    r = dict(attempt_id=f"a{i}",version=1,student_id="s1",skill_id="python.loops",
        task_id=f"task-{i}",matched_task_set_id="set-1",checkpoint_id=f"cp-{i//2}",
        timestamp=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=7*(i//2))).isoformat(),
        assistance="assisted" if i%2==0 else "unassisted",task_type="written",
        response_text="The loop includes the ending number in range.",correctness=.9 if i%2==0 else .4,
        time_taken_seconds=90,hint_count=1 if i%2==0 else 0,rubric_version="v1",synthetic=True)
    return r | changes

def history(gaps=(.1,.3,.5), **changes):
    from skill_erosion.contracts.models import Attempt
    return [Attempt(**record(2*c+j,correctness=.9 if j==0 else .9-gap,**changes))
            for c,gap in enumerate(gaps) for j in range(2)]
