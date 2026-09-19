# Data contract

The starting types live in `src/skill_erosion/contracts/models.py`. They are Python
dataclasses; their annotations do not perform runtime validation. Implement strict
boundary validation in trace ingestion. Agree on shared changes before merging.

## Attempt fields

| Field | Intended constraint |
|---|---|
| `attempt_id`, `version` | Stable opaque ID; positive integer version; immutable pair |
| `student_id` | Synthetic/opaque learner ID; not a name or email |
| `skill_id` | Key in `config/skill_taxonomy.json` |
| `task_id` | Identifies the actual task variant |
| `matched_task_set_id` | Reviewed equivalence group across assistance conditions |
| `checkpoint_id` | One comparable timepoint, such as a weekly assessment |
| `timestamp` | ISO 8601 timestamp with timezone, normalized to UTC |
| `assistance` | `assisted` or `unassisted`, recorded rather than inferred from text |
| `task_type` | `code`, `written`, or `quiz` |
| `response_text` | Sensitive source content; never log by default |
| `correctness` | Finite normalized rubric score from 0 to 1 |
| `time_taken_seconds`, `hint_count` | Nonnegative integers |
| `rubric_version` | Comparable scoring rubric identifier |
| `synthetic` | True for all committed sample records |
| `similarity_to_prior` | Null until computed, otherwise normalized 0 to 1 |

JSON uses native numbers, booleans, and null. The sample CSV encodes `synthetic`
as `true`, null similarity as an empty field, and numeric values as text. The
future importer must explicitly convert and validate these fields.

## Output types

`IngestionResult` gives stored attempt IDs and version count. `TrendReport` gives
per-checkpoint assisted score, unassisted score, signed gap, evidence IDs,
explanation, and model version. Trend status is `widening`, `stable`, `narrowing`,
`insufficient_data`, or `contradictory`.

`MisconceptionCluster` retains student/skill scope, concept summary, evidence
references, and encoder version. Evidence IDs should encode immutable versions
(for example `attempt-01:v1`), not ambiguous latest-version aliases.
`RemediationPlan` ties teacher summary, student exercise, and resource IDs to the
specific cluster. `JourneyResult` combines the three result types.

## Synthetic fixtures

`data/synthetic/attempts.json` and `attempts.csv` contain the same 210 records
for 24 students, generated deterministically by `scripts/generate_synthetic.py`
(run with `--extra N` to add more 5-checkpoint students). The four original
`demo-*` scenarios are preserved exactly:

| Student | Paired checkpoints | Correctness gaps | Expected fixture label |
|---|---|---|---|
| demo-widening | 3 | 0.10, 0.25, 0.40 | widening |
| demo-narrowing | 3 | 0.40, 0.25, 0.10 | narrowing |
| demo-stable | 3 | 0.15, 0.15, 0.15 | stable |
| demo-sparse | 2 | 0.10, 0.25 | insufficient_data |

The remaining 20 `syn-*` students add 6 widening, 6 narrowing, 4 stable,
2 contradictory, and 2 insufficient_data scenarios over 5 weekly checkpoints.

Each checkpoint has two distinct task IDs from a shared matched task set. There
are three task sets for the pilot skill `python.loops`. Review task content and
difficulty before treating equivalence labels as validated assessments.

`expected_trends.json` holds test labels, separate from inputs. These are designed
examples based on correctness alone; they do not validate the planned ensemble
or prove real-world skill erosion. The response strings are deliberately simple
seed data, not a realistic clustering benchmark. Add varied, labeled explanations
and counterexamples during Phase 2.
