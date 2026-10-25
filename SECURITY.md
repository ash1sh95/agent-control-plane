# Security policy

## Reporting a vulnerability
Please do **not** open a public issue for a security flaw in the gate
itself (a policy bypass, a dedupe/rate-limit evasion, an approval-flow
flaw). Use GitHub's private vulnerability reporting ("Report a
vulnerability" under the Security tab) so a fix and an eval case can land
before disclosure.

## Scope & honest limits
This is a reference implementation and portfolio project, not a certified
security product. Its controls reduce agent risk measurably (see the eval
harness); they do not make a compromised host, a malicious tool
implementation, or a jailbroken model safe. Read the LIMITS section of
the README before deploying anything with real credentials behind it.

## Supported versions
Only the latest `main` / most recent release is supported with fixes.
