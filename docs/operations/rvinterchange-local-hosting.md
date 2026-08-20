# RV Interchange local hosting operations

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
