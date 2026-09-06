# Security Audit — PhishGuard Backend

Date: 2026-08-17T11:14:00+05:30

Scope
-----
Quick security review of the backend code (local dev) focusing on API endpoints, authentication, rate limiting, input validation, LLM API key handling, and artifact/model promotion surfaces.

Actions taken (automated & code changes)
---------------------------------------
- Marked security-audit todo in_progress and performed static reviews across backend files.
- Implemented small, low-risk hardening changes (development-focused):
  - Restricted CORS to local dev origins: http://localhost:5173 and http://127.0.0.1:5173 (was previously '*').
  - Added a simple in-memory rate limiter middleware (per-IP) with environment-configurable window and request limits (RATE_LIMIT_WINDOW, RATE_LIMIT_REQUESTS). This returns 429 when exceeded.
  - Added an admin dependency that protects sensitive endpoints via an X-ADMIN-KEY header checked against ADMIN_API_KEY environment variable.
  - Applied the admin dependency to sensitive registry endpoints:
    - GET /api/registry/models/{name}/versions/{version}/artifact
    - POST /api/registry/promote

  These are conservative, reversible changes that reduce accidental exposure on a dev server.

Findings (issues & risks)
------------------------
1. CORS is permissive by default (fixed to local origins)
   - Risk: when frontend dev server or other hosts are used, open CORS can expose unauthenticated endpoints to other origins.

2. Sensitive actions were previously unauthenticated
   - /api/registry/promote and artifact download were publicly callable without auth. This allowed anyone with network access to replace the active meta-learner or download model artifacts.
   - Action: these endpoints now require X-ADMIN-KEY header matching ADMIN_API_KEY env var.

3. No general authentication for admin/ops endpoints
   - There is a demo login endpoint with in-memory users (demo/demo) but no RBAC, no persistent users, no API token management.
   - Recommendation: implement JWT-based auth or an API key management system, and add role checks (admin vs. viewer).

4. No rate limiting before (added basic in-memory limiter)
   - Current in-memory limiter is per-process and will reset on restart; it's OK for dev but not for production. A distributed rate limiter (Redis) is recommended for production.

5. Input validation
   - Several endpoints accept form fields or files without strict validation (e.g., URL lengths, image size/type). The analyze endpoints should validate URL length, allowed schemes, maximum image size, and enforce timeouts on processing.

6. LLM API key handling
   - GEMINI_API_KEY is read from environment variables (good). Ensure the key is never logged or committed; move secrets into a secret manager (Vault/Azure Key Vault/GCP Secret Manager) for production.
   - LLM calls in fusion_engine are synchronous with a short (8s) timeout. Consider async queueing for XAI generation to avoid holding request threads and to provide retries and backoff.

7. Protobuf / google client dependency mismatches
   - Upgrades performed earlier uncovered a mismatch risk (google-generativeai vs google-ai-generativelanguage). Ensure dependency resolution and compatibility are tested in CI (already noted in dependency report).

8. Artifact serving safety
   - The artifact download endpoint checks that the artifact path is under registry/models (good). Continue to ensure path checks and avoid exposing arbitrary filesystem paths.

9. Logging & telemetry
   - Avoid logging full request bodies or any secrets. Redact or sanitize logs for any fields that may contain sensitive data (API keys, tokens, PII).

Recommendations (short-term, actionable)
----------------------------------------
1. Set ADMIN_API_KEY in environment (strong random value) and distribute securely to operators. Update frontend promotion flows to require admin auth if promotion is performed via UI.
2. Replace in-memory rate limiter with a Redis-backed limiter (e.g., using 'slowapi' or custom middleware) for reliable production rate limiting across processes/instances.
3. Implement proper auth + RBAC:
   - Add JWT or API-key based auth; require auth for registry promote/download and any management endpoints.
   - Add a read-only viewer role for UI listing endpoints, and an admin role for promotion/download.
4. Harden input validation:
   - Validate URL scheme and length; reject overly long or non-http(s) URLs.
   - Enforce maximum image upload size and validate content-type (only image/*).
   - Add request size limits at the ASGI/proxy (nginx/gunicorn) level.
5. LLM usage hardening:
   - Do not rely on synchronous LLM calls in request path. Consider queuing XAI jobs (Celery/Redis) and returning a pending result that UI polls or receives via WebSocket.
   - Implement circuit breaker / quota-aware behavior: when LLM quota is low, degrade gracefully and avoid repeated failing calls.
6. Secrets & keys:
   - Move GEMINI_API_KEY and ADMIN_API_KEY to a secret manager.
   - Auditing: ensure keys are not present in repo or logs; scan with secrets-audit job.
7. CI & testing:
   - Add dependency & security scanning to CI (pip-audit, safety, npm audit).
   - Add smoke tests for auth-protected endpoints to CI once API keys/secrets are available via CI secrets.

Recommendations (long-term / production)
---------------------------------------
- Serve backend behind a reverse proxy (nginx) with TLS termination, WAF rules, and IP allow/deny lists as needed.
- Use managed secret storage, audit logging, and alerting on suspicious operations (e.g., repeated promote attempts).
- Require human review before promoting models to production (HITL flow) with audit logs and change approvals.

Next steps I can take now (pick one)
------------------------------------
- A) Configure ADMIN_API_KEY and update frontend promote flow to include X-ADMIN-KEY (implement UI change). (Recommended next to enable promotion via UI safely)
- B) Replace in-memory rate limiter with a Redis-backed limiter (requires Redis infra). I can scaffold code and CI changes.
- C) Add input validation checks to analyze-ensemble (URL validation, size limits) and return 400 for invalid inputs.
- D) Run secrets-audit (scan repo for committed secrets) — recommended to run soon.

Files changed
-------------
- backend/main.py — added rate limiter middleware, admin dependency, restricted CORS, and protected registry artifact/promote endpoints.

Report generated by: PhishGuard dev assistant (Copilot CLI runtime in VS Code)
