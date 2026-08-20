# RV Interchange local hosting operations

## Repository-owned local stack

The repository-owned Compose stack replaced the two legacy RV Interchange containers on 2026-08-20. The active local services are:

- `rvinterchange-api`, available only to the private Compose network on port `8484`.
- `rvinterchange-web`, with a diagnostic binding at `http://127.0.0.1:8485`.
- `rvinterchange-review`, with a diagnostic binding at `http://127.0.0.1:8486`.

The API's `Docs/Tools` mount is read-only. It expects the derived `Docs/Tools/components.db` read model to exist in the checkout that owns the Compose project. Rebuild that artifact with:

```bash
python3 Docs/Tools/edge_resolver.py --build Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db
```

The 2026-08-20 local acceptance run completed with zero ground-truth mismatches. Both health endpoints returned `{"status":"ok"}`, the public proxy returned the expected SW6DE search result, public debug/documentation/admin routes returned `404`, and the submission placeholder returned `503`. Ports `8485` and `8486` listened only on `127.0.0.1`; port `8484` had no host listener.

The remotely managed Cloudflare Tunnel connector became active on 2026-08-20. It registered four QUIC connections without authentication errors, and its DNS, UDP, TCP, and Cloudflare API connectivity pre-checks passed. The connector runs only on the private Compose network and publishes no host port.

The connector later received the two exact published application routes: `rvinterchange.com` to `http://rvinterchange-web:80` and `review.rvinterchange.com` to `http://rvinterchange-review:80`, followed by a `404` catch-all. Both authoritative Cloudflare nameservers and the public `1.1.1.1` resolver return proxied A and AAAA answers for the apex and review hostnames. A proxied `www` record and permanent redirect canonicalize `https://www.rvinterchange.com/*` to the same apex path and query string.

The public acceptance matrix passed on 2026-08-20. Apex health and SW6DE search returned `200`; public debug, API documentation, OpenAPI, and admin paths returned `404`; and the submission placeholder returned `503`. Plain HTTP redirects permanently to HTTPS. HTTPS `www` requests redirect permanently to the apex while preserving the path and query string; HTTP `www` requests first upgrade to HTTPS and then canonicalize to the apex.

An unauthenticated review request returns a `302` to Cloudflare Access and does not expose the local review HTML. The self-hosted Access application uses an eight-hour session, an Allow policy restricted to the exact `contact@rvinterchange.com` identity, and email one-time PIN authentication. The authenticated OTP acceptance test reached the review application successfully. The non-secret Application Audience tag is stored in the private operations record at `/data/DockerConfigs/RVInterchange/cloudflare-access.txt`; cookies, PINs, generated login URLs, and tokens are excluded.

An explicit Cache Rule bypasses caching for `/public/v1/*`, `/submission/v1/*`, and `/health/` across the zone. Post-deployment health, search, and submission responses reported `CF-Cache-Status: DYNAMIC` with no `Age` header and retained their expected `200`, `200`, and `503` statuses. Ordinary static caching remains available, and no Cache Everything rule was added for HTML. The Cloudflare Managed Ruleset was already active and remains enabled with its existing deployment settings.

Always Use HTTPS is enabled. After the public, Access, email, outage, and rollback checks passed, conservative HSTS was enabled on 2026-08-20 at approximately 17:08 America/New_York. Public and review responses now include `Strict-Transport-Security: max-age=2592000`. `includeSubDomains` and `preload` remain disabled. Reconsider a longer lifetime only after at least one month of stable HTTPS operation.

## Outage and rollback verification

The controlled tunnel-outage drill passed on 2026-08-20 at approximately 17:05 America/New_York. With only `rvinterchange-cloudflared` stopped, public health returned Cloudflare `530` while `http://127.0.0.1:8485/health/` remained healthy. Restarting the connector restored four QUIC registrations, all connectivity pre-checks passed, and public health returned `200` again.

The legacy rollback drill passed on 2026-08-20 at approximately 17:06 America/New_York. The repository-owned stack was stopped, the two shared-Compose services in the `rvinterchange-legacy` profile were built and started, and both the legacy API documentation on port `8484` and legacy web root on port `8485` responded successfully. The legacy pair was then stopped and removed.

The repository-owned production images were explicitly rebuilt before the new stack was restarted because the legacy and production definitions reuse the same local image tags. After restoration, API, public web, review web, and tunnel services were healthy; public health and SW6DE search returned `200`; unauthenticated review returned the expected Access `302`; ports `8485` and `8486` listened only on loopback; and the API had no host listener. A headless Chromium acceptance run also completed live search, result detail, discontinued-chain rendering, browser Back/Forward restoration, and coverage-table loading at the public origin. Keep `--build` in the return-to-production command after any legacy build.

The shared `/data/DockerConfigs/docker-compose.yaml` keeps both old RV Interchange services behind the `rvinterchange-legacy` profile. The shared repository contains unrelated pre-existing modifications and remains uncommitted.

## Cloudflare inbound email routing

Configuration was checked on 2026-08-20. Cloudflare Email Routing has two enabled literal-recipient forwarding rules:

- `contact@rvinterchange.com`
- `dmarc-reports@rvinterchange.com`

Both rules forward to the verified account-level destination. The destination address, provider tokens, and generated DNS values are intentionally excluded from this repository.

Catch-all routing is disabled with the drop action. Addresses other than the two explicit routes must not be forwarded.

Email Routing was enabled on 2026-08-20 and reported `ready`. Authoritative Cloudflare DNS and the public `1.1.1.1` resolver then both confirmed the root Email Routing MX records, root SPF TXT record, and `cf2024-1._domainkey` DKIM TXT record. These records direct inbound mail to Cloudflare and identify Cloudflare's forwarding service. Generated DNS values are intentionally excluded from this repository.

## DMARC policy

Public DNS confirms one reporting-only DMARC TXT record at `_dmarc.rvinterchange.com`:

```text
v=DMARC1; p=none; rua=mailto:dmarc-reports@rvinterchange.com; adkim=s; aspf=s
```

Do not move to `p=quarantine` or stronger enforcement until DMARC reports show every active sender passes alignment checks.

## Acceptance checks

Acceptance tests completed on 2026-08-20 from an unrelated mailbox. Forwarding to `contact@rvinterchange.com` passed. Forwarding to `dmarc-reports@rvinterchange.com` passed after the initial DNS and routing propagation delay resolved. A message to a random, unconfigured address did not forward, confirming the disabled catch-all policy.

Cloudflare Email Routing is inbound forwarding only. Replies can expose the personal destination until a branded outbound service is added. Arbitrary-recipient Cloudflare Email Sending remains gated on explicit Workers Paid authorization in the submission-intake plan.
