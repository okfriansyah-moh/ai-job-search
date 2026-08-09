# PR Remediation

Use the `pr-remediation` skill for this task.

Process every supplied pull-request comment independently. Classify it, validate it against the repository instructions and relevant workflow, then decide `APPLY`, `REJECT`, or `DEFER`. Do not blindly implement comments.

For accepted comments, make the smallest safe change, add or update tests when behavior changes, and run the validation required by the skill. Do not commit secrets, generated automation state, candidate profile data, or application materials unless the review item explicitly requires them.

Return one decision block per comment followed by a concise remediation summary and remaining risks.
