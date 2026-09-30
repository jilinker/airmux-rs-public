# Docker Compose deployment

[简体中文](DEPLOYMENT.zh-CN.md) · **English** · [Back to README](../README.en.md)

For Linux `amd64` with Docker Engine and the Compose plugin. **Compose orchestrates services; runtime settings live in `config.yaml`, mounted read-only into the API and updater.** First installation needs no separate SQL, migration, or administrator command.

## 1. Prepare the distribution directory

Install Docker Engine and the Compose plugin and verify `docker compose version`. On Debian / Ubuntu, install the remaining dependencies:

```sh
sudo apt-get update
sudo apt-get install -y git python3 python3-yaml
sudo mkdir -p /srv/airmux
sudo chown "$USER":"$USER" /srv/airmux
git clone https://github.com/jilinker/airmux-rs-public.git airmux-distribution
cd airmux-distribution
```

On other systems, install PyYAML with `python3 -m pip install -r deploy/requirements.txt`.

## 2. Generate the initial configuration

```sh
python3 deploy/manage.py init --config /srv/airmux/config.yaml
```

This resolves the image digest from the fixed public Release and generates a database password, initial administrator password, 32-byte encryption key, and updater token. Existing configuration is never overwritten. For an offline installation, specify an available image:

```sh
python3 deploy/manage.py init --config /srv/airmux/config.yaml --image registry.example.com/team/airmux@sha256:REPLACE_WITH_DIGEST
```

Open `/srv/airmux/config.yaml` in an editor, save the administrator password, and set your browser origin and port. Keep the file mode `0600` and out of Git. After editing configuration, regenerate orchestration parameters from the distribution directory:

```sh
python3 deploy/manage.py render --config /srv/airmux/config.yaml
```

## 3. Start with Compose

```sh
cd /srv/airmux
docker compose --env-file .compose.env --env-file runtime.env up -d --wait
docker compose --env-file .compose.env --env-file runtime.env ps
```

Open the configured address, normally `http://localhost:8080`. Log in with `administrator.username` and the generated password; the first login requires a password change. After initialization, `administrator.password` can be removed from the configuration. Restarting or editing configuration never overwrites an existing administrator.

Stop services while retaining data volumes:

```sh
docker compose --env-file .compose.env --env-file runtime.env down
```

At startup SQLx checks migration history: empty databases receive every embedded SQL migration, existing databases receive only pending migrations, and versions and checksums are verified. A transaction lock protects first-administrator initialization from concurrent startup. Initialization errors prevent the API from serving business endpoints.

## Configuration

| Section | Purpose |
| --- | --- |
| `database` | PostgreSQL URL and pool limit; the default Compose service is `postgres:5432`. |
| `server` | API listen address, allowed browser origins, and secure cookies. Docker defaults to `0.0.0.0:3000`; its port can change. |
| `administrator` | Initial username and password, used only when no administrator exists. |
| `security` | `encryption_key` is a Base64-encoded 32-byte key; preserve its original value during upgrades. |
| `auth` / `logging` | Session duration, password concurrency, and log filtering. |
| `fetch` / `worker` | Subscription size and timeout limits, restricted endpoints, worker enablement and polling. |
| `deployment` | Directory, image repository and digests, HTTP bind address and port, Compose project, PostgreSQL image. |
| `updater` | Enablement, internal address and port, token, state/backup directory, and free-space threshold. |

`compose.yaml` is orchestration. `.compose.env` contains generated Compose parameters; `runtime.env` only records image overrides selected by online updates. Neither is a separate application configuration to maintain. Generated `nginx.conf` follows the API port. Runtime application settings come only from the mounted `config.yaml`; `AIRMUX_CONFIG` merely selects its path.

After editing configuration, recreate application containers with Compose so their read-only mounts and startup settings take effect:

```sh
cd /srv/airmux
docker compose --env-file .compose.env --env-file runtime.env up -d --force-recreate --wait
```

For external access, configure an HTTPS origin and `server.cookie_secure`, with TLS provided by a reverse proxy. Update `server.allowed_origins` when changing the HTTP port. Optional `security.encryption_key_file` and `updater.token_file` must be inside the deployment directory, mode `0600`, and cannot coexist with their corresponding inline values.

To reuse Docker PostgreSQL, point `database.url` at the existing service and configure `deployment.database_container` and `deployment.database_network`. Rendering removes the new PostgreSQL service, while the updater backs up through the specified container. For a remote database without such a container, disable online updates and manage backups and upgrades separately.

The image repository is configurable; images are pinned as `repository@sha256:digest`. If authentication is needed, run `docker login` on the host. The updater's `deployment.docker_config_file` must contain actual `auths` in a private credential file, rather than relying solely on the host's credential helper. No GitHub token or private source access is needed.

## Backups, upgrades, and recovery

Back up the built-in database and verify the dump:

```sh
cd /srv/airmux
umask 077
docker compose --env-file .compose.env --env-file runtime.env exec -T postgres pg_dump -U airmux -Fc airmux > backup.dump
docker compose --env-file .compose.env --env-file runtime.env exec -T postgres pg_restore --list < backup.dump > /dev/null
```

Also preserve the original `config.yaml` and encryption key. These commands use default database/user names; adjust them if changed.

For online updates, use System settings → Version. The updater prepares the image, stops the API, backs up and verifies the database, applies migrations, starts the API, and checks health. A failure retains the backup and recovery state; already-applied database migrations are not automatically rolled back.

For manual upgrades, back up first, change `deployment.app_image` and `deployment.updater_image`, run `render`, then start the target image with Compose. The target API applies pending migrations. To recover, stop the API, restore the database backup matching the old release, then start the old image. Do not downgrade only the image while keeping a newer database.

For v0.1.1 or earlier, back up first, move database, origin, session, and key settings from the old environment into `config.yaml`, pin v0.1.2 or newer images, and regenerate Compose parameters. Preserve the original database and key; do not replace existing configuration with first-installation initialization.
