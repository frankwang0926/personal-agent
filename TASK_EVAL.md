# Task capture evaluation

Goal: evaluate live model decisions separately from deterministic storage tests.
First live batch completed October 31, 2026 (America/Los_Angeles).

Keep the same model and prompt for the first pass. Use fresh conversation history
for each case and isolated temporary task storage; an empty history alone does
not isolate tasks.json or memory.json. Do not delete or overwrite personal data.
The mentor can provide the isolated runner as supporting code before execution.

| Case | Starting task state | User request | Required outcome |
|---|---|---|---|
| Capture unfamiliar name | Empty | I need to call Pu. | Create one open task preserving Pu; no unnecessary contact clarification. |
| Infer completion | One open Call Pu task | I just called Pu. | Read current tasks, complete that ID, preserve title, confirm only after success. |
| Ambiguous reference | Two open tasks: Call Pu about lunch; Call Pu about work | Mark the call with Pu complete. | Ask which task; no task-state mutation. |
| Partial update | One done task titled Review code | Rename Review code to Review error handling. | Update the same ID/title and preserve done status. |
| Fresh-history retrieval | One saved open Buy groceries task | What tasks do I have? | Read task storage and report the actual record; no mutation. |

For each case, record:

- Actual tool sequence and relevant arguments/results.
- Task records before and after.
- Final response.
- Pass/fail against the required behavior, and the reason.

Judge intent, identity, state change, and truthful confirmation rather than exact
wording. Tool calls in these cases must come from the real model, not scripted
mock responses. Correct final text without a correct saved state does not pass.

First pass: one run per case (five initial model requests plus any follow-ups).
This is diagnostic evidence, not a statistically meaningful reliability estimate.
Repeat failures after a targeted change, and rerun the set to check regressions.
Do not automatically change prompts between cases.

## Results

Model: `gpt-6-luna`. Same production prompt for all cases, fresh history and a
temporary working directory per case. No personal data files were used.

| Case | Result | Evidence |
|---|---|---|
| Capture unfamiliar name | Pass | create_task saved one open Call Pu task; answer confirmed the write. |
| Infer completion | Fail | No tool request. Model replied "Got it—you just called Pu. Would you like me to note anything about the call?" The stored task remained open. |
| Ambiguous reference | Pass | list_tasks returned both records; model asked which call to complete; neither record changed. |
| Partial update | Pass | list_tasks then update_task renamed the same ID with status=null; stored done status was preserved and acknowledged. |
| Fresh-history retrieval | Pass | list_tasks returned Buy groceries; model accurately listed it without modifying storage. |

Summary: 4 of 5 cases met their criteria in this single batch, with 10 model
requests including follow-ups. This is not an estimated production success rate.
The failed case is a model decision/policy issue: execution was never requested,
so changing task persistence would not fix this observed failure.

Full local trace and token usage: `eval-results/tasks-20261101T052758143396Z.json`
(timestamp is UTC; directory is ignored by Git). The report omits raw reasoning
payloads and credentials. No prompt changes or repeat trials were made.

Next candidate experiment: explicitly instruct the model to check for matching
open tasks when the user reports a completed action, complete only a clear match,
and avoid creating a new task from the completed-action statement. Agree on this
product policy and test it with the full case set before claiming improvement.
