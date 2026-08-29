# RV Interchange moderation review operations

The moderation review service is a private, Access-protected surface for the
quarantined submission database. It is not the public catalog. Its authorized
promotion workflow may append reviewed evidence to `observations.db`, but it
never rebuilds or writes `components.db`.

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
  change submission or claim workflow state. Admin decisions and
  publisher-authorized promotion are append-only and idempotent.
- Promotion requires active `admin` and `publisher` authority. It appends one
  canonical observation and its origin record, then leaves graph integration
  pending; it does not write the derived catalog database.

## Configuration and secrets

Set these in `/data/DockerConfigs/.env` or an equivalent environment file:

```text
RVI_ACCESS_ISSUER=https://<tenant>.cloudflareaccess.com
RVI_ACCESS_AUDIENCE=<application-audience>
RVI_ACCESS_JWKS_URL=https://<tenant>.cloudflareaccess.com/cdn-cgi/access/certs
RVI_TOKEN_KEY_FILE=/data/DockerConfigs/RVInterchange/intake/secrets/token_key
RVI_REVIEW_DIGEST_KEY_FILE=/data/DockerConfigs/RVInterchange/intake/secrets/review_digest_key
RVI_CANONICAL_DATA_DIR=/data/DockerConfigs/RVInterchange/canonical
```

Use a dedicated reviewer digest key distinct from the intake token key. Never
commit keys, JWT assertions, contributor contact data,
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

## Initialize the dedicated canonical store

Initialize the writable canonical directory only while the review API is
stopped, and only from a verified current `observations.db` snapshot. From the
repository checkout that will run the stack:

```bash
compose=(docker compose --env-file /data/DockerConfigs/.env -f deploy/docker-compose.yaml)
canonical_dir=/data/DockerConfigs/RVInterchange/canonical
snapshot="$PWD/Docs/Tools/observations.db"

"${compose[@]}" stop rvinterchange-review-api
test -f "$snapshot"
sudo install -d -o root -g root -m 0700 "$canonical_dir"
if sudo test -e "$canonical_dir/observations.db"; then
  echo "Refusing to overwrite initialized canonical database" >&2
  exit 1
fi
sudo install -o root -g root -m 0600 "$snapshot" "$canonical_dir/observations.db"
source_sha256=$(sha256sum "$snapshot" | awk '{print $1}')
target_sha256=$(sudo sha256sum "$canonical_dir/observations.db" | awk '{print $1}')
test "$source_sha256" = "$target_sha256"
sudo chown root:root "$canonical_dir" "$canonical_dir/observations.db"
sudo chmod 0700 "$canonical_dir"
sudo chmod 0600 "$canonical_dir/observations.db"
```

The `root:root` directory and database modes keep the canonical mount scoped to
the review API; the intake service has no canonical mount. Do not copy
`components.db` into this directory. It is a read-only, rebuildable catalog
artifact, not canonical promotion input. The canonical directory may contain
only `observations.db` and SQLite journal files created for that database.

After the checksum comparison succeeds, start or update the normal review
stack. Do not run this initialization against a live review API. Replacing an
initialized canonical database is not initialization: use a separate,
backup-verified restoration procedure that retains the original database for
investigation.

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

The public intake remains closed. Do not start the `intake` profile as part of
canonical initialization, a promotion drill, or a review rollback:

```bash
docker compose --env-file /data/DockerConfigs/.env \
  -f deploy/docker-compose.yaml --profile intake config --quiet
```

The public `/submission/v1/*` maintenance boundary remains closed. The intake
service has no host port and must never mount `Docs/Tools`, `components.db`, or
the canonical directory.

## Isolated drill and rollback

Run the deterministic promotion/reconciliation drill only with Pytest-created
temporary paths. It creates separate intake and canonical SQLite databases,
injects a post-canonical failure, retries reconciliation, and proves that no
`components.db` is created:

```bash
drill_dir=$(mktemp -d /tmp/rvinterchange-promotion-drill.XXXXXX)
python3 -m pytest tests/review/test_promotion_drill.py -q --basetemp "$drill_dir"
rm -rf "$drill_dir"
```

Never set the drill's temporary paths to
`/data/DockerConfigs/RVInterchange/intake` or
`/data/DockerConfigs/RVInterchange/canonical`, and never run it against any
production database.

For a failed review deployment, keep the intake profile disabled and preserve
both database directories for investigation. Stop only the review API, switch
to the known-good checkout or commit, and recreate that API without deleting
either database:

```bash
compose=(docker compose --env-file /data/DockerConfigs/.env -f deploy/docker-compose.yaml)
"${compose[@]}" stop rvinterchange-review-api
git switch --detach <known-good-review-api-commit>
"${compose[@]}" up -d --build --no-deps rvinterchange-review-api
```

Do not remove `/data/DockerConfigs/RVInterchange/intake/data` or
`/data/DockerConfigs/RVInterchange/canonical` during rollback. Verify review
health, catalog search, and the public `/submission/v1/*` maintenance boundary
before restoring Access traffic.

## Release gates and deferred work

Run `python3 -m pytest tests/ Docs/Tools -q` and `git diff --check` before each
publish. Promotion, canonical observation writes, graph integration,
backup/restore automation, public contribution forms, and public evidence
ledger work remain separate Issue #47 follow-ons.
