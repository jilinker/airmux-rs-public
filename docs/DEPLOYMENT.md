# Docker Compose deployment in three steps

[简体中文](DEPLOYMENT.zh-CN.md) · **English** · [Back to README](../README.en.md)

Install Docker Engine and the Compose plugin first. The image supports `linux/amd64`. Deployment needs only **`config.yaml`, `compose.yaml`, and `.env`**; no repository clone, Python installation, or initialization script.

**Compose starts PostgreSQL 17 by default**; no separate database installation is required. For an existing database, see [External PostgreSQL](#external-postgresql).

## 1. Download and edit the configuration

Create the deployment directory and download the two YAML files from the public repository:

```sh
mkdir -p /srv/airmux
cd /srv/airmux
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/config.yaml -o config.yaml
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/compose.yaml -o compose.yaml
```

Direct downloads: [config.yaml](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/config.yaml) · [compose.yaml](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/compose.yaml). Both files include Chinese comments. Keep the default Compose file.

Edit `config.yaml`:

| Setting | Required change |
| --- | --- |
| `database.url` | Replace `CHANGE_ME_DATABASE_PASSWORD`. Use letters, digits, underscores, or hyphens to avoid URL escaping; enter the same password in `.env` in step 2. |
| `administrator.username` / `password` | Choose the initial administrator credentials. The password needs at least 8 characters, including upper and lower case letters; the default username is `admin`. |
| `security.encryption_key` | Paste the output of `openssl rand -base64 32`. Preserve this key during upgrades. |
| `updater.token` | Paste the output of `openssl rand -hex 32` for internal update authentication. |
| `server.allowed_origins` | For remote access, add the actual origin, such as `http://192.168.1.10:8080`. For HTTPS, use your domain origin and set `cookie_secure` to `true`. |

Keep other defaults. If using another directory, set `deployment.directory` and use the same path in `.env` in the next step.

## 2. Download .env and start Compose

```sh
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/.env -o .env
```

Direct download: [.env](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/.env). **Set `POSTGRES_PASSWORD` to the database password in `config.yaml`.** Change the remaining parameters only if needed:

| Parameter | Default / purpose |
| --- | --- |
| `AIRMUX_IMAGE_REPOSITORY` | The public image repository is already filled in; no Docker login is needed. |
| `AIRMUX_VERSION` | A released version is already filled in; another compatible version may be selected. |
| `AIRMUX_HTTP_PORT` / `AIRMUX_HTTP_BIND` | `8080` / `0.0.0.0`; update `allowed_origins` when changing the port. |
| `AIRMUX_DEPLOY_DIR` | `/srv/airmux`; the absolute directory containing all three files, matching `deployment.directory`. |

Save and start:

```sh
chmod 600 config.yaml .env
docker compose up -d --wait
```

Compose starts PostgreSQL, the API, frontend, and updater. The API reads the mounted `config.yaml` in read-only mode, applies pending SQLx migrations, and creates the first administrator automatically. Existing accounts and data are preserved.

The default database and user are both `airmux`. The API connects to `postgres:5432`; the database port is not published to the host. Data persists in the `postgres-data` volume. `POSTGRES_PASSWORD` only sets the password when initializing an empty volume; editing it does not reset an existing password.

## 3. Check startup

```sh
docker compose ps
docker compose logs --tail=50 api
```

`api` and `postgres` should be `healthy`; `frontend` and `updater` should be `Up`. Open `http://SERVER_IP:8080` and sign in with the configured administrator credentials. Change the password after the first login.

For startup failures, check file permissions, encryption key format, matching database passwords, and the actual origin in `allowed_origins`.

Stop with `docker compose down`; omit `-v` to retain data. Click the sidebar version to update; the updater maintains the image override in `.env`. After editing configuration, run `docker compose up -d --force-recreate --wait`. Before switching versions manually, back up and clear the `AIRMUX_APP_IMAGE` override in `.env`.

Preserve the database, encryption key, and deployment directory when upgrading an existing installation. The v0.1.2 `.compose.env` / `runtime.env` layout remains supported; documentation changes do not require database reinitialization.

## External PostgreSQL

Follow the same three steps, but download the external variant as **`compose.yaml`** in step 1. No additional Compose override is needed:

```sh
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/compose.external.yaml -o compose.yaml
```

This variant does not create, start, or manage PostgreSQL. Prepare an existing database and an account with permission to create tables and apply migrations. The API initializes tables and the first administrator; **it does not create the database itself**. `POSTGRES_PASSWORD` in `.env` is unused; configure the database connection in `config.yaml`.

### Remote or host PostgreSQL

Change these values in `config.yaml`; other required settings are the same as the default deployment:

```yaml
database:
  url: "postgres://airmux:YOUR_PASSWORD@db.example.com:5432/airmux"
  max_connections: 10
updater:
  enabled: false
```

The address must be reachable from the API container. For host PostgreSQL, replace `db.example.com` with `host.docker.internal`; `localhost` refers to the API container itself. Configure TLS as required, for example by appending `?sslmode=require`, and allow database connections from the container.

Keep `AIRMUX_NETWORK_EXTERNAL=false` and `COMPOSE_PROFILES=` in `.env`. Run `docker compose up -d --wait`, then check that `api` is `healthy` and `frontend` is `Up`. Online updates currently require a PG backup through Docker, so this mode disables the updater. Before upgrading manually, back up using your database's backup tools, then switch image versions as described above.

### An existing PG container on the same Docker daemon

Join the PG container's existing network and use its container name as the database host. For example, with container `local-postgres` on network `local-postgres_default`, edit `.env`:

```dotenv
AIRMUX_NETWORK_NAME=local-postgres_default
AIRMUX_NETWORK_EXTERNAL=true
COMPOSE_PROFILES=updates
```

Point `database.url` in `config.yaml` at the actual database and set these values within the existing sections:

```yaml
deployment:
  database_container: "local-postgres"
updater:
  enabled: true
```

Preserve the other `deployment` and `updater` fields, including the update token and deployment directory. The updater backs up through `docker exec` in this PG container. Ensure its `pg_dump` / `pg_restore` can access the database as the connection-string user before enabling online updates. To leave online updates disabled, keep `COMPOSE_PROFILES=` and set `updater.enabled: false`.

Start the existing PG first, then run the same `docker compose up -d --wait`. No second PG or new database is created, and `docker compose down` does not stop the existing PG.

See Docker's [networking guide](https://docs.docker.com/compose/how-tos/networking/) and [profiles guide](https://docs.docker.com/compose/how-tos/profiles/) for networking and optional services.
