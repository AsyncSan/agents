# Security Audit Report: OWASP Juice Shop v19.2.1

**Date:** 2026-04-13  
**Repository:** https://github.com/juice-shop/juice-shop  
**License:** MIT  
**Auditor:** Automated SAST + Dependency Scan

---

## Executive Summary

OWASP Juice Shop is an **intentionally vulnerable** web application designed for security training. The vulnerabilities found below are **by design** — they exist to teach developers about common security flaws. This audit documents them as if evaluating a production codebase.

**Risk Level: CRITICAL** — Multiple severe vulnerabilities including hardcoded cryptographic keys, code injection via `eval()`, weak sanitization, and permissive CORS.

| Severity | Count |
|----------|-------|
| 🔴 Critical | 3 |
| 🟠 High | 4 |
| 🟡 Medium | 3 |
| 🔵 Low | 2 |

---

## Findings

### 🔴 CRITICAL

#### C1: Hardcoded RSA Private Key for JWT Signing
- **File:** `lib/insecurity.ts:25-28`
- **Detail:** The full RSA private key used for signing JWTs is embedded directly in source code. Anyone with access to the repo can forge valid authentication tokens for any user.
- **Impact:** Complete authentication bypass; any attacker can impersonate any user including admins.

#### C2: Server-Side Code Injection via `eval()` in User Profile
- **File:** `routes/userProfile.ts:62`
- **Detail:** User-controlled `username` field is passed directly to `eval()` when it matches the pattern `#{(...)}`. This allows arbitrary server-side JavaScript execution.
- **Impact:** Remote Code Execution (RCE) — full server compromise.

#### C3: `eval()` in Captcha Route (Lower Risk but Still Critical Pattern)
- **File:** `routes/captcha.ts:22`
- **Detail:** `eval(expression)` is used to compute captcha answers. While the expression is server-generated from random integers and operators, the `eval()` pattern is inherently dangerous and could become exploitable if input validation changes.
- **Impact:** Potential code execution if input validation is weakened.

### 🟠 HIGH

#### H1: Weak/Bypassable HTML Sanitization
- **File:** `lib/insecurity.ts:61`
- **Detail:** `sanitizeLegacy()` uses a trivial regex `/<(?:\w+)\W+?[\w]/gi` that is easily bypassed with crafted payloads. This is used for username sanitization (`models/user.ts:50`).
- **Impact:** Persistent Cross-Site Scripting (XSS) via username fields.

#### H2: Permissive CORS Configuration — Allow All Origins
- **File:** `server.ts:180-182`
- **Detail:** `app.options('*', cors())` and `app.use(cors())` with no origin restrictions. Comment in code: "Bludgeon solution for possible CORS problems: Allow everything!"
- **Impact:** Any malicious website can make authenticated cross-origin requests to the API, enabling CSRF-like attacks and data exfiltration.

#### H3: XSS Filter Intentionally Disabled
- **File:** `server.ts:187`
- **Detail:** `helmet.xssFilter()` is commented out with the note: "no protection from persisted XSS via RESTful API."
- **Impact:** Browser-level XSS mitigations are not applied.

#### H4: Hardcoded Test Credentials in Test Suite
- **Files:** `test/api/chatBotSpec.ts:215`, `test/api/erasureRequestApiSpec.ts:37`, and others
- **Detail:** Base64-encoded passwords (`bW9jLmxpYW1nQGhjaW5pbW1pay5ucmVvamI=`) are used across multiple test files. While test-only, these credentials may correspond to default application accounts.
- **Impact:** Credential exposure; default accounts may be accessible in deployed instances.

### 🟡 MEDIUM

#### M1: JWT Verification Uses Public Key from Filesystem
- **File:** `lib/insecurity.ts:22`
- **Detail:** `publicKey` falls back to `'placeholder-public-key'` if filesystem read fails, which could allow trivial token forgery in misconfigured environments.
- **Impact:** Authentication bypass in edge-case deployments.

#### M2: WebSocket CORS Hardcoded to localhost
- **File:** `lib/startup/registerWebsocketEvents.ts:20`
- **Detail:** Socket.IO CORS origin is hardcoded to `http://localhost:4200`, which may cause issues in production or allow bypass in specific configurations.
- **Impact:** Potential WebSocket hijacking in non-default deployments.

#### M3: No CSRF Protection
- **File:** No `csrf` middleware found in `server.ts`
- **Detail:** Combined with the permissive CORS policy (H2), the application has no protection against cross-site request forgery.
- **Impact:** State-changing actions can be triggered by malicious third-party sites.

### 🔵 LOW

#### L1: GitHub Actions Secrets Referenced (Not Leaked)
- **Files:** `.github/workflows/release.yml`, `.github/workflows/ci.yml`
- **Detail:** Secrets like `DOCKERHUB_USERNAME`, `SLACK_WEBHOOK_URL`, `CYPRESS_RECORD_KEY` are referenced via `${{ secrets.* }}` — properly handled by GitHub, not hardcoded.
- **Impact:** None currently. Noted for completeness.

#### L2: No `package-lock.json` in Repository
- **Detail:** Lock file not present, meaning dependency versions are not pinned. `npm audit` could not complete (no `node_modules` installed).
- **Impact:** Builds may pull different dependency versions, potentially introducing vulnerabilities via supply chain drift.

---

## Dependency Audit

⚠️ **npm audit could not complete** — no `node_modules` or `package-lock.json` present in the cloned repository. A full dependency audit requires running `npm install` first.

**Recommendation:** Run `npm install && npm audit` in a CI environment to get the full vulnerability report. Given that Juice Shop intentionally uses vulnerable dependencies (e.g., older versions of `express-jwt`, `sanitize-html`), expect a high number of findings.

---

## Recommendations

### Immediate (if this were production code)
1. **Remove hardcoded private key** (C1) — use environment variables or a secrets manager
2. **Eliminate all `eval()` usage** (C2, C3) — use safe alternatives (`Function` constructors are equally dangerous)
3. **Restrict CORS origins** (H2) — whitelist specific allowed domains
4. **Enable XSS filter** (H3) — uncomment `helmet.xssFilter()`
5. **Implement CSRF protection** (M3) — add `csurf` or similar middleware

### Short-term
6. **Replace regex-based sanitization** (H1) with a robust library like DOMPurify
7. **Add `package-lock.json`** (L2) to pin dependencies
8. **Remove test credentials** (H4) from source or use environment-injected test secrets
9. **Fix JWT public key fallback** (M1) — fail closed, don't fall back to a weak key

### Ongoing
10. Run `npm audit` in CI pipelines with `--audit-level=high` as a gate
11. Integrate a SAST tool (e.g., CodeQL, Semgrep) into CI
12. Conduct periodic manual penetration testing

---

## Disclaimer

OWASP Juice Shop is a **deliberately insecure application** for educational purposes. All findings above are **intentional vulnerabilities** designed to teach security concepts. This report treats them as if auditing production code to demonstrate proper security audit methodology.
