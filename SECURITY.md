# Security Policy

## Supported versions

Security fixes are provided for the latest release on the `main` branch.

## Reporting a vulnerability

Do not open a public issue for a vulnerability or exposed credential. Use GitHub private
vulnerability reporting when enabled, or contact the repository owner privately.

Include the affected version, reproduction steps, impact, and a suggested mitigation. Never
include production API keys, private prompts, or generated reports.

## Security model

- Secrets are loaded from local or deployment environment variables and are never committed.
- Web fetch rejects local, private, link-local, and reserved network destinations.
- Redirect destinations, response type, and response size are validated.
- Retrieved documents are treated as untrusted data, not agent instructions.
- Generated reports require human review before they are used for high-impact decisions.

## Deployment checklist

- Use a secret manager instead of a committed `.env` file.
- Restrict API keys by project, quota, and environment.
- Run the agent with minimal filesystem and network permissions.
- Retain sanitized audit logs and monitor API usage anomalies.
- Review third-party source licensing and privacy requirements.

