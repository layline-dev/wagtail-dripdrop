# Security Policy

## Supported versions

Security fixes are applied to the latest released version of `wagtail-dripdrop`.
We recommend always running the most recent release.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report them privately using GitHub's
[private vulnerability reporting](https://github.com/layline-dev/wagtail-dripdrop/security/advisories/new),
or by email to **dev@layline.dev**.

Include as much as you can:

- A description of the vulnerability and its impact
- Steps to reproduce, or a proof of concept
- Affected version(s)

We aim to acknowledge reports within 3 business days and to provide a fix or
mitigation plan within 30 days. We will credit you in the advisory unless you
would rather stay anonymous.

## Scope

This package stores a DripDrop API key in your Django settings and sends form
submission data to the DripDrop API. Issues that involve leaking that key,
sending data to an unintended host, or bypassing the Wagtail admin permission
checks on the DripDrop cache view are all in scope.
