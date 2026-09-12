# Security contract draft

M1 exposes public liveness/readiness and a JWT-protected identity endpoint only.
JWT verification fixes the algorithm and requires issuer, audience, expiry, issued
time, UUID subject/institution and a known role. Tokens are never issued by M1.
Future login and server-side persisted user/status checks are required before private
data endpoints; a valid signature alone is not resource authorization.

M2+ queries must enforce institution and ownership from authenticated context,
including agent tools and audit/replay. Staff scope must be checked server-side.
Public error responses omit exception details; logs omit request bodies, raw paths,
queries, authorization headers and secrets. Correlation IDs are generated server-side.

Development Compose exposes only loopback Nginx HTTP. Dependencies have no host
ports. Production requires TLS, hardened secrets/roles, rate limits, file validation,
backup/restore evidence and the SRS production gates. Development is not production.
