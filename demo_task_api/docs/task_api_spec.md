# Task API Spec

1. Preserve the existing success response envelope: `{"ok": true, "data": ...}`.
2. Preserve the existing error response envelope: `{"ok": false, "error": {"code": ..., "message": ...}}`.
3. Preserve public handler signatures in `task_api/api.py` unless explicitly approved.
4. Use `AppError` with explicit error codes for user-facing failures.
5. Keep new behavior additive where possible rather than changing existing route shapes.
6. For the summary endpoint, use a nested object keyed by status in the response data (e.g. `{"summary": {"todo": 5, "in_progress": 2, "done": 8}}`).
7. For new read-style handlers, preserve consistency with the existing API where reasonable. If there is a choice between following the existing query-based handler style and introducing a simpler one-off interface, stop and check in with assumptions and options before choosing.
8. If a feature requires changing an existing route shape, response envelope, or handler signature, stop and check in with assumptions and options.
