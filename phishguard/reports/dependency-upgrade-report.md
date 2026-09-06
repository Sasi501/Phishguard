# Dependency Upgrade Report

Date: 2026-08-17T11:04:00+05:30

Summary
-------
Performed a conservative upgrade of patch/minor Python dependencies in the backend virtualenv and ran the backend test suite.

What was upgraded (selected set)
- uvicorn: 0.52.1 -> 0.52.3
- starlette: 1.4.1 -> 1.6.0
- djangorestframework: 3.17.2 -> 3.18.0
- selenium: 4.46.0 -> 4.47.0
- pydantic-core: 2.46.4 -> 2.48.0
- google-genai: 2.17.0 -> 2.18.1
- google-api-core: 2.33.0 -> 2.34.0
- googleapis-common-protos: 1.75.0 -> 1.75.1
- google-ai-generativelanguage: 0.6.15 -> 0.12.0
- charset-normalizer: 3.4.9 -> 3.5.1
- filelock: 3.32.2 -> 3.32.3
- tldextract: 5.3.1 -> 5.3.2

Test results
------------
- Installed/test environment: backend venv
- After upgrades, ran pytest: 15 passed, 1 warning (DeprecationWarning in screenshot pipeline)
- No test regressions observed in the current test suite.

Conflicts & Risks
-----------------
- google-generativeai 0.8.6 requires google-ai-generativelanguage==0.6.15. Upgrading google-ai-generativelanguage to 0.12.0 creates a mismatch.
  - Impact: any code or third-party package depending on google-generativeai pinned to 0.8.6 may break.
  - Recommendation: either pin google-ai-generativelanguage back to 0.6.15 OR upgrade google-generativeai to a compatible version or replace usage.

- protobuf upgraded to 7.35.1 (pulled in by google-api-core). This is a major version jump and may have ABI/compatibility effects for packages using protobuf/gRPC.
  - Impact: low-level serialization, gRPC clients/servers, or libraries depending on older protobuf APIs may break.
  - Recommendation: perform integration tests for any gRPC or protobuf-using codepaths; if issues arise, consider pinning to a compatible protobuf minor.

- Numerical/compiled stacks (numpy, llvmlite, numba, pyarrow) have newer versions available in the environment. These can sometimes require matching binary wheels — monitor CI and test model-loading paths (CatBoost, torch) after upgrades.

Next recommended actions
------------------------
1. Decide google-* strategy (priority):
   - Conservative: pin google-ai-generativelanguage==0.6.15 to satisfy google-generativeai 0.8.6. This is the fastest way to restore known compatibility.
   - Forward: upgrade google-generativeai and dependent callsites to use google-ai-generativelanguage 0.12.0 (or replace legacy client). This may require code changes and testing.

2. Pin the verified working versions in requirements.txt (or add a constraints file). Example: generate requirements-upgraded.txt using pip freeze > requirements-upgraded.txt and commit that file.

3. Run LLM/XAI smoke tests (analyze-ensemble) to ensure google-genai/google-ai-generativelanguage upgrade works in practice (note: LLM rate limits may still interfere).

4. Schedule major upgrades (protobuf, numpy, TypeScript) in separate, reviewed maintenance branches with full CI runs and integration tests.

Commands run (for reproducibility)
----------------------------------
# inside backend folder, using the project venv
.\venv\Scripts\python.exe -m pip install --upgrade uvicorn starlette djangorestframework selenium pydantic-core google-genai google-api-core googleapis-common-protos google-ai-generativelanguage charset-normalizer filelock tldextract
.\venv\Scripts\python.exe -m pip list --outdated --format=json
.\venv\Scripts\python.exe -m pytest -q

Files changed (local dev)
-------------------------
- No requirements.txt was modified automatically. Recommend creating a pinned requirements-upgraded.txt after CI verification.

Report prepared by: PhishGuard dev assistant (Copilot CLI runtime in VS Code)
