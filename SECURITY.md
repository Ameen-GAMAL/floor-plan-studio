# Security and privacy

Run Floor Plan Studio through `run.py`, which binds to `127.0.0.1` by default. The application is designed for one local user. It has no public-hosting authentication or tenant isolation. Treat a reverse proxy or LAN deployment as a different security design.

Use synthetic briefs in screenshots, examples, and bug reports. Real floor plans can disclose access routes and building details. Keep exports on trusted storage and review them before sharing. The default generation path processes briefs locally and loads no third-party frontend assets.

Report a suspected vulnerability privately via the repository's [Security tab](https://github.com/Ameen-GAMAL/floor-plan-studio/security). If GitHub does not offer a private report form, request a private contact channel through a minimal public issue. Include a version or commit and a synthetic example. Keep sensitive layouts, secrets, and reproduction details out of public issues.
