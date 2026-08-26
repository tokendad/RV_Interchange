# RV Interchange submission intake operations

## Release state

The intake backend is implemented as a quarantined, profile-gated service. It is
not a launched public feature. Public Nginx continues to return the controlled
`503` response for every `/submission/v1/*` request, and the intake service has
no host port or Cloudflare Tunnel route.

Do not proxy public traffic to this service or add it to the production tunnel
until every release gate at the end of this document is complete. Starting the
profile is for local verification only.

The service owns only:

- `/app/data/submissions.db`, including its SQLite WAL and shared-memory files.
- `/app/artifacts`, containing sanitized private image derivatives.
- read-only secret files under `/run/secrets`.

It has no `Docs/Tools`, `components.db`, `observations.db`, repository, or
canonical-data mount. Schema migrations run automatically during application
startup inside an immediate SQLite transaction.

## Host layout and secrets

The default host layout is:

```text
/data/DockerConfigs/RVInterchange/intake/
├── artifacts/
├── data/
│   └── submissions.db
└── secrets/
    ├── contact_key
    ├── ip_key
    ├── session_key
    ├── token_key
    └── turnstile_secret
```

Create the private directories and four independent 32-byte application keys
before the first local start:

```bash
install -d -m 0700 /data/DockerConfigs/RVInterchange/intake/data
install -d -m 0700 /data/DockerConfigs/RVInterchange/intake/artifacts
install -d -m 0700 /data/DockerConfigs/RVInterchange/intake/secrets
(
  umask 077
  openssl rand -out /data/DockerConfigs/RVInterchange/intake/secrets/contact_key 32
  openssl rand -out /data/DockerConfigs/RVInterchange/intake/secrets/token_key 32
  openssl rand -out /data/DockerConfigs/RVInterchange/intake/secrets/session_key 32
  openssl rand -out /data/DockerConfigs/RVInterchange/intake/secrets/ip_key 32
)
```

Install the real Cloudflare Turnstile secret separately as
`turnstile_secret`, mode `0600`. Never put it in this repository, shell history,
Compose YAML, or logs. The key files are also excluded from the repository and
must be included in the future encrypted backup procedure. Do not overwrite an
existing contact key: doing so makes stored contributor contact and pending mail
recipients undecryptable. Token/session/IP-key rotation needs a separately
reviewed invalidation and overlap procedure before launch.

The five `RVI_*_KEY_FILE`/`RVI_TURNSTILE_SECRET_FILE` environment variables may
override the default secret paths. `RVI_INTAKE_DATA_DIR` and
`RVI_INTAKE_ARTIFACT_DIR` may override the two host storage roots for isolated
drills.

## Local profile startup and health

Validate both dormant and tunnel configurations first. Neither command starts a
container:

```bash
docker compose -f deploy/docker-compose.yaml --profile intake config --quiet
docker compose -f deploy/docker-compose.yaml --profile tunnel config --quiet
```

Build and start only the profile-gated intake service:

```bash
docker compose -f deploy/docker-compose.yaml --profile intake up -d --build rvinterchange-intake
```

Because there is no host port, verify health from inside the service:

```bash
docker compose -f deploy/docker-compose.yaml --profile intake exec -T rvinterchange-intake \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8487/health/').read().decode())"
```

The expected response is `{"status":"ok"}`. Detailed intake state is not
published by the health route. Stop the service without taking down the public
stack:

```bash
docker compose -f deploy/docker-compose.yaml --profile intake stop rvinterchange-intake
```

The transactional outbox code intentionally has no production provider adapter,
worker container, credentials, or log-mailer fallback. Local verification and
submission receipts can enqueue rows, but nothing delivers them until a real
mailer is separately authorized and wired to the worker.

## Isolated startup drill

Use a separate Compose project and temporary storage so a drill cannot touch the
default intake database or artifact root. The Turnstile file only needs to be
non-empty for a health-only drill; it must not be used for submission testing.

```bash
drill_root=$(mktemp -d /tmp/rvinterchange-intake-drill.XXXXXX)
install -d -m 0700 "$drill_root/data" "$drill_root/artifacts" "$drill_root/secrets"
(
  umask 077
  openssl rand -out "$drill_root/secrets/contact_key" 32
  openssl rand -out "$drill_root/secrets/token_key" 32
  openssl rand -out "$drill_root/secrets/session_key" 32
  openssl rand -out "$drill_root/secrets/ip_key" 32
  openssl rand -hex -out "$drill_root/secrets/turnstile_secret" 32
)

env \
  RVI_INTAKE_DATA_DIR="$drill_root/data" \
  RVI_INTAKE_ARTIFACT_DIR="$drill_root/artifacts" \
  RVI_CONTACT_KEY_FILE="$drill_root/secrets/contact_key" \
  RVI_TOKEN_KEY_FILE="$drill_root/secrets/token_key" \
  RVI_SESSION_KEY_FILE="$drill_root/secrets/session_key" \
  RVI_IP_KEY_FILE="$drill_root/secrets/ip_key" \
  RVI_TURNSTILE_SECRET_FILE="$drill_root/secrets/turnstile_secret" \
  docker compose -p rvinterchange-intake-drill \
    -f deploy/docker-compose.yaml --profile intake \
    up -d --build rvinterchange-intake
```

Run the internal health command with the same environment overrides and Compose
project name. After inspection, remove only the drill project:

```bash
env \
  RVI_INTAKE_DATA_DIR="$drill_root/data" \
  RVI_INTAKE_ARTIFACT_DIR="$drill_root/artifacts" \
  RVI_CONTACT_KEY_FILE="$drill_root/secrets/contact_key" \
  RVI_TOKEN_KEY_FILE="$drill_root/secrets/token_key" \
  RVI_SESSION_KEY_FILE="$drill_root/secrets/session_key" \
  RVI_IP_KEY_FILE="$drill_root/secrets/ip_key" \
  RVI_TURNSTILE_SECRET_FILE="$drill_root/secrets/turnstile_secret" \
  docker compose -p rvinterchange-intake-drill \
    -f deploy/docker-compose.yaml --profile intake down
```

Delete the temporary drill root only after confirming it is the path returned by
the `mktemp` command and no evidence needs to be retained.

## Gates that remain closed

Public intake must remain unavailable until all of these are implemented and
verified:

- Authorized arbitrary-recipient transactional mail delivery and worker
  operation; Cloudflare Email Sending remains disabled pending Workers Paid
  approval.
- Encrypted daily backup, off-host copy, retention, and a clean restore drill for
  `submissions.db`, artifacts, configuration metadata, and required keys.
- Approved privacy notice, contribution terms, evidence license, retention, and
  deletion language.
- Application validation of the Cloudflare Access JWT plus local reviewer grants
  and revocation.
- The private moderation queue, claim decisions, append-only review audit,
  publisher-authorized promotion, and fixture-validated graph integration.
- Public contribution, receipt/status, and accessible error/recovery user
  interfaces.
- Explicit Nginx proxy enablement, abuse monitoring, live Turnstile validation,
  rate-limit acceptance, and a documented rollback exercise.

Acceptance, canonical promotion, and graph integration remain separate states.
Trusted assessments remain advisory; only an admin decides claims and only an
authorized publisher may promote accepted evidence.
