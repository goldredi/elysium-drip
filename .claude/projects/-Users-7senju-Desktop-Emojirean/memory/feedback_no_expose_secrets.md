---
name: no_expose_secrets
description: Never display .env contents or secrets in output to the user
type: feedback
---

Do not display .env file contents or secrets (API keys, passwords, admin secrets) in conversation output.

**Why:** .env contains sensitive data like bot tokens, admin secrets, database passwords.
**How to apply:** When reading .env, summarize what's there without showing actual values.
