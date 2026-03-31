# Security Policy

## Supported Versions

This is a benchmarking and research library. The following versions receive security updates:

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes     |

## Reporting a Vulnerability

**Do not open a public GitHub Issue for security vulnerabilities.**

Email the maintainer directly: **anthony@etherealogic.com**

Include:
- A description of the vulnerability
- Steps to reproduce
- The potential impact
- Any suggested mitigation (optional)

You will receive an acknowledgement within 72 hours. If a fix is warranted, a patched release will be published and you will be credited (unless you prefer to remain anonymous).

## Scope

This project is a pure Python research benchmark. It:
- Does not expose a network service
- Does not handle credentials or secrets
- Does not connect to external data sources at runtime

Vulnerabilities in **dependencies** (pandas, numpy, scipy) should be reported to those upstream projects. If a dependency vulnerability directly affects this benchmark's output integrity, please notify us as well.
