# Security Policy

## Supported versions

driftline is a 0.1.x demonstration library. Only the latest release on `main`
receives fixes.

| Version | Supported |
|---|---|
| 0.1.x (latest) | yes |
| earlier | no |

## Reporting a vulnerability

Report privately through GitHub Security Advisories: the "Report a
vulnerability" button on this repository's Security tab. You can expect an
acknowledgment within 7 days.

Scope note: the library is pure standard-library Python with no network
surface, no file I/O, and no dependencies, so the realistic vulnerability
classes are narrow (algorithmic or numerical defects rather than injection or
transport issues). Reports of incorrect statistical behavior with a
reproducible case are welcome through the same channel or as a public issue,
whichever fits the sensitivity.
