# Loop boundaries

Resource ID: loops-boundaries-01
Skill: python.loops
Misconception: treating the exclusive stop value in range as inclusive.
Source: team-authored synthetic pilot resource.

In Python, `range(start, stop)` includes `start` and excludes `stop`.
To visit 1, 2, and 3, use `range(1, 4)`.

Practice without tools: write a function that sums the integers from 1 through n,
including n. Trace your loop by hand for n = 1 and n = 4, then explain why the
stop bound is correct. Return to the task with a different n at the next checkpoint.
