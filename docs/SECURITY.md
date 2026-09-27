# Security

The backend includes URL validation and SSRF-oriented restrictions in the redirect/domain path, including loopback/private/metadata destination checks, redirect validation, bounded redirect traversal, timeouts, and meta-refresh validation.

Authentication uses hashed passwords from `backend/db.py` and signed, expiring server-generated tokens in `backend/main.py`. CORS is restricted to local development origins and Chrome-extension origins. Rate limiting supports Redis with an in-memory fallback.

These controls are implementation evidence, not a claim of complete security. The project remains a prototype and should receive a production threat model, deployment hardening, and DNS-rebinding/TOCTOU review before exposure to hostile networks.

Runtime verification confirmed that a loopback destination was blocked for network-dependent domain/redirect operations while partial analysis continued. This is evidence for the tested case only, not a claim of complete security. No authentication or security behavior was changed as part of the final documentation cleanup.

The extension currently initializes an absent stored token to the literal `demo-token`; this is a placeholder, not a production credential. Do not interpret extension token handling as production-ready authentication.
