# RV Interchange moderation review operations

The moderation review service is a private, Access-protected surface for the
quarantined submission database. It is not the public catalog and it does not
promote evidence into `observations.db` or rebuild `components.db`.

## Runtime boundaries

- `rvinterchange-review-api` listens only on the Docker network at port `8488`.
- `rvinterchange-review` is the only review host entrypoint and binds locally at
  `127.0.0.1:8486`; Cloudflare Access protects `review.rvinterchange.com`.
- The review proxy permits only `/review/v1/session`, `/review/v1/queue`,
  `/review/v1/submissions/...`, `/health/`, and static assets. Catalog, debug,
  intake, documentation, and OpenAPI routes are denied on this host.
- Every API request requires a Cloudflare Access JWT. The JWT issuer, audience,
  signature, and expiry are validated before the normalized email is HMAC
  matched to an active local `trusted` or `admin` role. `publisher` is an
  optional capability that can authorize admin-level review actions.
- Trusted assessments (`endorse`, `dispute`, `spam`) are advisory and never
  change submission or claim workflow state. Admin or publisher decisions are
  append-only and idempotent.

## Configuration and secrets

Set these in `/data/DockerConfigs/.env` or an equivalent environment file:

```text
RVI_ACCESS_ISSUER=https://<tenant>.cloudflareaccess.com
RVI_ACCESS_AUDIENCE=<application-audience>
RVI_ACCESS_JWKS_URL=https://<tenant>.cloudflareaccess.com/cdn-cgi/access/certs
RVI_TOKEN_KEY_FILE=/data/DockerConfigs/RVInterchange/intake/secrets/token_key
```

The token-key default is retained for compatibility with the current local
deployment; use a dedicated reviewer digest key when the role store is first
provisioned. Never commit keys, JWT assertions, contributor contact data,
uploaded artifacts, or `submissions.db`.

The review migration is applied automatically when the API starts. Grant or
revoke roles by an authenticated operator using the `reviewer_roles` table;
store only the HMAC digest of the normalized email, never the email address.

## Deploy and verify locally

From the checkout that owns the Compose bind mounts:

```bash
python3 Docs/Tools/edge_resolver.py --build \
  Docs/Inital_Design/ground-truth.yaml Docs/Tools/components.db
docker compose --env-file /data/DockerConfigs/.env \
  -f deploy/docker-compose.yaml --profile tunnel up -d --build
```

The resolver output is a rebuildable read model and is mounted read-only into
the catalog API. Do not put `components.db` in the intake or review write path.

Check the service and boundary before opening the Access hostname:

```bash
docker compose --env-file /data/DockerConfigs/.env \
  -f deploy/docker-compose.yaml ps
curl -fsS http://127.0.0.1:8486/health/
curl -i http://127.0.0.1:8486/review/v1/queue       # 401 without Access JWT
curl -i http://127.0.0.1:8485/review/v1/           # 404 on public host
curl -fsS http://127.0.0.1:8485/public/v1/search?q=SW6DE
```

With a valid Access session, the browser review page must show a sanitized
queue. Confirm that contributor contact, abuse digests, storage keys, and
reviewer digests are absent. Replay a mutation with the same idempotency key to
confirm the same redacted response is returned. Confirm a Trusted identity can
endorse/dispute/flag spam but receives `403` for claim decisions.

The public intake profile remains off:

```bash
docker compose --env-file /data/DockerConfigs/.env \
  -f deploy/docker-compose.yaml --profile intake config --quiet
docker compose --env-file /data/DockerConfigs/.env \
  -f deploy/docker-compose.yaml --profile intake up -d --build rvinterchange-intake
```

Only enable intake after its separate authentication, abuse, privacy, backup,
mail, and promotion gates are approved. It has no host port and must never
mount `Docs/Tools` or `components.db`.

## Isolated drill and rollback

Use a temporary Compose project with temporary data, artifacts, logs, secrets,
and a locally signed test JWKS. Override `RVI_INTAKE_DATA_DIR` and
`RVI_INTAKE_ARTIFACT_DIR`, assign unique container/image names and a loopback
port, then run `up -d --build --wait` for `review-jwks`, the catalog API,
`rvinterchange-review-api`, and `rvinterchange-review`. Exercise health,
unauthenticated `401`, signed queue/detail reads, admin decision, idempotent
replay, Trusted authorization, and public-host `404`. Tear down the project
afterward; never point the drill at production intake storage.

For a failed deployment, keep the intake profile disabled, stop the tunnel
project, restore the previous checkout and generated `components.db`, then
restart the tunnel profile with `--build`. Verify catalog search and the public
`/submission/v1/*` maintenance boundary before restoring Access traffic.

## Release gates and deferred work

Run `python3 -m pytest tests/ Docs/Tools -q` and `git diff --check` before each
publish. Promotion, canonical observation writes, graph integration,
backup/restore automation, public contribution forms, and public evidence
ledger work remain separate Issue #47 follow-ons.
