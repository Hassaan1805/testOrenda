# TODO

## Supabase + frontend loading fix
- [ ] Identify why frontend fails to load after adding Supabase (static mounting vs API/runtime crash)
- [ ] Verify backend startup logs and environment variables in docker-compose
- [ ] Fix backend/db.py so it doesn’t crash when Supabase env vars are missing (fallback or lazy init)
- [ ] Add safe integration: only use Supabase for history if configured; otherwise return empty list (or existing sqlite)
- [ ] Ensure frontend fetches correct API base URL (prefer same-origin)
- [ ] Retest: open /journal.html and /history.html, verify at least placeholder renders and JS doesn’t abort
- [ ] Document required Supabase env vars and expected behavior

