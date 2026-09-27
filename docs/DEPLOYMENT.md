# Deployment

The repository is configured for local development:

1. Start the FastAPI backend from `phishguard/backend`.
2. Start the Vite frontend from `phishguard/frontend`.
3. Load `phishguard/extension` as an unpacked Manifest V3 extension where browser policy permits.

Configure model files and environment values according to the backend requirements. MongoDB and optional Redis are environment-dependent. The extension was runtime verified in an isolated Microsoft Edge profile; Chrome unpacked loading was blocked by managed developer-mode policy in the verification environment. MongoDB was unavailable during HITL runtime verification. These checks do not establish production deployment, enterprise readiness, or complete browser compatibility.
