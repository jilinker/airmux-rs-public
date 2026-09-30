# Production deployment

[简体中文](DEPLOYMENT.zh-CN.md) · **English** · [Back to README](../README.en.md)

[First installation](#first-installation) · [Starting the stack](#starting-the-stack) · [Recovery](#recovery-and-verification) · [Release sources](#release-sources)

The release image is one `linux/amd64` image containing the API, migration and
bootstrap binaries, nginx, the static frontend, the Python updater, and the
Docker CLI with its Compose plugin. The updater image is pinned separately so
an application release does not replace the updater.

## First installation

### 1. Prepare the deployment directory

Create the deployment directory outside the repository. The commands below use
`/srv/airmux`; choose another absolute path if needed and replace it
consistently. Export it before running any Compose command. The updater mounts
this same host path at the same path in its container so its generated
`runtime.env` is available to Compose.
Download [compose.yaml](../deploy/compose.yaml) and [config.example.yaml](../config.example.yaml) from the public distribution repository and run the commands from that distribution directory.
The copied `config.yaml` uses `/srv/airmux` for these paths; update those four
paths if you choose a different deployment directory.

```sh
export AIRMUX_DEPLOY_DIR=/srv/airmux
mkdir -p "$AIRMUX_DEPLOY_DIR/secrets"
chmod 700 "$AIRMUX_DEPLOY_DIR/secrets"
install -m 0644 deploy/compose.yaml "$AIRMUX_DEPLOY_DIR/compose.yaml"
test -e "$AIRMUX_DEPLOY_DIR/config.yaml" || install -m 0644 config.example.yaml "$AIRMUX_DEPLOY_DIR/config.yaml"
test -e "$AIRMUX_DEPLOY_DIR/.env" || install -m 0600 /dev/null "$AIRMUX_DEPLOY_DIR/.env"
test -e "$AIRMUX_DEPLOY_DIR/runtime.env" || install -m 0600 /dev/null "$AIRMUX_DEPLOY_DIR/runtime.env"
for name in airmux_encryption_key airmux_updater_token docker_config.json; do
  test -e "$AIRMUX_DEPLOY_DIR/secrets/$name" || install -m 0600 /dev/null "$AIRMUX_DEPLOY_DIR/secrets/$name"
done
```

### 2. Fill the secret files

The `test -e` guards preserve existing files. Fill the empty files using your
secret manager or an editor; this document intentionally contains no real
credentials. `docker_config.json` must contain registry credentials usable by the
Docker CLI on the host. Keep the files mode `0600`. The encryption key must be 32 random bytes,
encoded as base64 (for a new empty file, `openssl rand -base64 32`). The
updater token should be independently generated, for example 32 random bytes
encoded as hex. Never regenerate either secret on routine upgrades.

The registry configuration must work inside the updater container and must not
depend on a host-only credential helper. `config.yaml` currently requires JSON
syntax; JSON is a YAML subset. Keep the example structure rather than converting
it to ordinary YAML key/value syntax.

### 3. Configure the environment

Set the deployment values in `.env` (the image references should be immutable
digests):

```dotenv
AIRMUX_DEPLOY_DIR=/srv/airmux
AIRMUX_IMAGE=registry.example.com/your-namespace/airmux
AIRMUX_APP_IMAGE=registry.example.com/your-namespace/airmux@sha256:...
AIRMUX_UPDATER_IMAGE=registry.example.com/your-namespace/airmux@sha256:...
POSTGRES_PASSWORD=generate-a-long-random-value
DATABASE_URL=postgres://airmux:URL_ENCODED_PASSWORD@postgres:5432/airmux
AIRMUX_ORIGIN=https://airmux.example.com
```

Replace the placeholder repositories, digests, domain and password. The password
in `DATABASE_URL` must match `POSTGRES_PASSWORD`, with special characters URL
encoded. The frontend host port defaults to `8080` and can be changed with
`AIRMUX_HTTP_PORT`. Production defaults to `COOKIE_SECURE=true` and needs an HTTPS
reverse proxy. For local HTTP validation, set `COOKIE_SECURE=false` and use the
corresponding HTTP origin.

### 4. Apply migrations and create an administrator

Before the first API start, apply the embedded SQLx migrations explicitly and
create the first administrator. Starting the API does not mutate the database.
PostgreSQL must be running first; `bootstrap-admin` reads the password from
stdin and refuses to run after an administrator already exists.
The password-entry command below requires Bash or Zsh. The first login requires
changing the initial password.

```sh
cd "$AIRMUX_DEPLOY_DIR"
docker compose --project-name airmux --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" up -d --wait postgres

docker compose --project-name airmux --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" run --rm --no-deps \
  --entrypoint /usr/local/bin/migrate api

read -r -s AIRMUX_ADMIN_PASSWORD
printf '%s\n' "$AIRMUX_ADMIN_PASSWORD" | docker compose --project-name airmux \
  --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" run --rm --no-deps -T \
  --entrypoint /usr/local/bin/bootstrap_admin api admin
unset AIRMUX_ADMIN_PASSWORD
```

## Starting the stack

Start the complete stack with the same explicit paths:

```sh
export AIRMUX_DEPLOY_DIR=/srv/airmux
docker compose --project-name airmux --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" up -d
```

Only nginx publishes a host port. The updater has no host port and is reachable
only inside the Compose network; its API and Docker socket are not exposed
through nginx. Updater requests require the token in
`secrets/airmux_updater_token`, passed as `AIRMUX_UPDATER_TOKEN_FILE`. Nginx
proxies `/api/` and `/sub/` to the API and does not log `/sub/` URLs because
they contain bearer tokens.

The updater checks a digest-pinned release manifest before pulling an image. A
restart stops the API, takes a PostgreSQL custom-format dump, runs release
migrations, recreates the API, and waits for readiness. A failed migration or
health check leaves the API stopped and records `needs_recovery`; review the
persisted dump and restore it manually before retrying.

Before first production use, configure registry credentials, fill the four
secret files, choose immutable app and updater image digests, set a public HTTPS
origin, and verify that the Docker socket policy permits the updater to run
Compose. Standard CI image builds require registry secrets; the prebuilt-image
release path below does not. This repository contains no deployment credentials.

## Recovery and verification

During API restart, the web dialog retries the authenticated status endpoint.
If migration or readiness fails and the API remains offline, recovery is performed
on the Docker host; the browser cannot retrieve administrator-only status until
the API is available again. Do not expose the updater port to work around this.

Read the durable operation and backup location from the updater container:

```sh
docker compose --env-file .env --env-file runtime.env -f compose.yaml exec -T updater \
  python3 -m json.tool /var/lib/airmux-updater/state.json
```

Preserve `state.json`, `runtime.env`, and the referenced dump before recovery.
Inspect container logs on the host. Decide whether to fix the target release and
complete its migration, or restore the backup with its matching previous image.
Never run an older application against a partially migrated database. Only after
the database, API readiness and frontend have been verified should the operator
archive the failed state and reset the updater to idle. Keep the backup until
that recovery is confirmed. Automatic upgrades intentionally cannot perform
this destructive restore or clear `needs_recovery`.

Local validation covers the state machine and mocked command ordering. Before
production rollout, exercise the full backup/restore and upgrade flow on a
separate staging deployment with the intended registry credentials.

## Release sources

Releases are always read from the public
[`jilinker/airmux-rs-public`](https://github.com/jilinker/airmux-rs-public)
repository. No GitHub repository setting or GitHub token is needed on the
deployment host. Compose requires `AIRMUX_IMAGE`
(`registry/namespace/image`, without tag/digest) in the deployment `.env`.
`AIRMUX_APP_IMAGE` and `AIRMUX_UPDATER_IMAGE` select the initially deployed
immutable images; they are separate so application updates do not replace the
running updater. Use the same image repository for `AIRMUX_IMAGE` and app releases.
The updater accepts only manifests whose image digest belongs to this configured
repository. Release-page links point to the public release repository.

Environment values override the optional `image` field in `config.yaml` when
running the updater outside Compose. Missing/invalid image sources fail
explicitly. Changing the image source requires recreating the updater service;
do not change it while an update is prepared or running.

For CI, set repository variables `REGISTRY_HOST` and `IMAGE_REPOSITORY`, and
secrets `REGISTRY_USERNAME` and `REGISTRY_PASSWORD`. Private CI builds and
validates the image, then publishes an allowlisted release package to the public
repository. The public repository's Actions workflow creates the Release with
its own `GITHUB_TOKEN`; deployment users do not configure or provide that token.

Maintainers run `python3 scripts/publish-public-release.py vX.Y.Z --publish` from
the private source checkout. The tool synchronizes allowlisted files and tags
through an independent public clone without copying private Git history.
Private CI can use `PUBLIC_RELEASE_SSH_KEY`, limited to writing to the public
repository, for automatic synchronization. Without it, CI saves the reviewable
public distribution Artifact. Deployment users do not need this credential.

## Prebuilt image releases and local Docker verification

A tag may use a manifest under `.github/release-manifests/<tag>.json` when the
image has already been built and pushed from an authorized local machine.
The workflow checks its version, platform and immutable digest, runs the
regression checks, and synchronizes the public tag. Public Actions publishes
`release-manifest.json` as a Release asset.
This path requires no registry login secrets in GitHub. Tags without this file
use the normal configurable registry build/push path described above.

`deploy/local/` is ignored by both Git and Docker builds. Its Compose stack can
join an existing PostgreSQL network and use the existing verification database.
For backups against a PostgreSQL container managed outside this Compose project,
set updater `AIRMUX_DATABASE_CONTAINER` to that container name. The updater uses
`docker exec` for dump validation, while all application operations still use the
configured Compose project. Do not initialize another verification database.
