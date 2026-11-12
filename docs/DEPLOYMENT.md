# Docker Compose deployment and configuration

Version 0.5.18 adds detailed update progress and retains unified plans that compose a unified plan from one base configuration and multiple feature configurations. The image is docker.io/jaelinker/airmux for linux/amd64, with a minimum upgrade version of 0.5.0. Existing 0.4.x installations require a separate empty database. The user confirmed live SMTP delivery. Default SSH identities were verified against a temporary real server; verify external server access in your environment. Loon validation remains deferred.

0.5.18 adds no SQL migrations and retains the fourteen immutable migrations. Upgrading from 0.5.17 preserves nodes, configurations, plans, links, and onboarding state.

**Upgrading from a version older than 0.5.9 runs the SQL migration introduced in 0.5.9, which deletes legacy common plans, client plans, related archives and all access links without migration or compatibility support.** Accounts, node sources, nodes, administrator regions and rule sets, system settings and migration history are retained. Back up the database and preserve the original encryption key before upgrading. Recreate configurations, plans and links afterward; previous links stop working. To recover legacy plans, restore the pre-upgrade backup into a separate database and use the original key and old image.

## Configuration ownership

| File | Responsibility |
| --- | --- |
| compose.yaml | Services, networks, dependencies, mounts, volumes, health checks and restart policy |
| .env | Images, versions, platform, project name, host ports, deployment paths and PostgreSQL initialization |
| config.yaml | Database connection, program listener, CORS, secrets, logging, initial administrator and updater settings |

The API environment only locates the program YAML. It does not override program settings from .env. Dynamic business settings belong in the database. The program rejects the previous deployment section.

## First installation

1. Install Docker and the Compose plugin. Create a dedicated directory such as /srv/airmux.
2. Obtain compose.yaml, config.yaml and .env from the same compatible release. Rename the source .env.example to .env when using source examples.
3. Replace the database password, initial administrator password, Base64 encryption key and updater token in config.yaml. Use openssl rand -base64 32 for the key and openssl rand -hex 32 for the token. Preserve the encryption key across updates.
4. Select the image version or digest in .env. Match POSTGRES_PASSWORD to the password in database.url. Set AIRMUX_DEPLOY_DIR to the absolute deployment directory and AIRMUX_CONFIG_FILE to this YAML file.
5. Set server.allowed_origins and server.public_base_url to the actual access address. Enable server.cookie_secure for HTTPS. A fresh database requires administrator.email and administrator.password. The initial email is verified but the first login must change its password. Existing administrators are never reset by bootstrap values. Legacy administrator.username is rejected. Configure and test SMTP in System settings before inviting other accounts. Invitation login verifies the email and requires a new password.

```sh
cd /srv/airmux
chmod 600 config.yaml .env
docker compose config --quiet
docker compose up -d --wait
docker compose ps
docker compose logs --tail=50 api
```

The default host port is 8080. AIRMUX_HTTP_PORT controls the published host port; server.listen in YAML controls the internal program listener. Use 0.0.0.0 inside containers. The frontend proxy, health check and updater readiness check read the API port from YAML.

Changing .env does not rotate an existing PostgreSQL password. Rotate the actual database credential and update the application connection together. POSTGRES_PASSWORD only controls initialization.

## External PostgreSQL

Replace compose.yaml with the matching compose.external.yaml and update database.url in config.yaml. Create the external database beforehand and grant schema and migration permissions. host.docker.internal can reach a host database. Set AIRMUX_NETWORK_NAME and AIRMUX_NETWORK_EXTERNAL when joining an existing Docker network.

Online updates require AIRMUX_DATABASE_CONTAINER to identify the PostgreSQL container that can run pg_dump and pg_restore. Direct backup of a remote database without a suitable container is unsupported. Disable updater.enabled, remove updates from COMPOSE_PROFILES and perform backups and updates manually for that deployment.

## Default SSH identities and host records

In 0.5.1, key authentication can omit the private key to use the API runtime user's default identity files or SSH agent. Password authentication still requires a password. Fingerprint and known_hosts records are optional. When omitted, SSH uses existing runtime records and the persistent file selected by fetch.ssh_known_hosts_file, records a first-seen host key and rejects subsequent key changes. Supply a fingerprint or explicit record to pin the host beforehand.

Docker does not automatically read host identities. Add explicit read-only mounts for the required identity files, such as /root/.ssh/id_ed25519, to api in your private Compose configuration. Agent use requires an explicit socket mount and SSH_AUTH_SOCK. Never include private keys in distribution files. The default Compose persists /var/lib/airmux-ssh; retain that volume across upgrades.

## Updates and manual recovery

updater.enabled declares program configuration and COMPOSE_PROFILES=updates starts the updater service. Administrators open the update modal from the version badge beside the brand. Checking reads release metadata. Download and update prepares the image immediately without a second confirmation. Restarting requires a maintenance confirmation. Opening the modal only reads status. Local Docker update and manual recovery drills passed; release-specific checks are documented separately.

The updater needs the Docker socket and a writable deployment directory at the same absolute path on the host and inside the container. Compose explicitly passes only the image repository, deployment directory, project name and database container. It does not inject the entire .env into the API or updater.

Persist /var/lib/airmux-updater. If updater.state_directory changes, adjust the Compose volume target. Mount token_file and encryption_key_file read-only in each consuming service when using file secrets. Private registry Docker credentials also require an explicit Compose mount.

Preparation verifies database-generation labels on the running and target images and checks every target SQL checksum against the release manifest in a read-only container without network or database mounts. Legacy installations and mismatched SQL are rejected before downtime. Execution rechecks the running image identity.

The update flow validates the target image, stops the API, creates and validates a backup, changes the application image in .env, migrates, checks the API and updates the frontend. It preserves config.yaml and unrelated .env settings. Recreate the updater itself during a subsequent maintenance window to adopt its new image.

Execution failures enter needs_recovery and attempt to stop the API. A failed stop is recorded as uncertain rather than successful. With the matching new frontend and updater deployed, a task-scoped read-only channel remains available while the API is stopped. It reconnects after frontend replacement and keeps observing until failure cleanup confirms whether the API stopped. Older updaters retain the previous behavior and can only provide browser logs once the API returns. Preserve the update state, backup, encryption key and deployment files. Restore the database and original image according to the failed stage. An image rollback alone may be incompatible with migrations that already ran. Check readiness and business data after recovery. Do not bypass migration checksums or erase migration records.

The optional source tool deploy/manage.py initializes three files in a fresh directory. Its render command verifies consistency without rewriting .env. Compose users do not need this tool. docker compose config --quiet validates orchestration syntax, not the program YAML that is validated at startup.

For recovery inspect phase, steps, backup and sourceImage in the persistent state.json and confirm the real container state. Keep the original local image and validate the dump using pg_restore --list before restoring. If migrations ran, restore the verified dump to a separate empty database, verify it, then switch config.yaml and the original image in .env together. Preserve the failed database for investigation. After readiness, login and business checks succeed, the operator can archive the completed update state. Do not clear needs_recovery from the browser.

## Enabling detailed progress and read-only observation

Deploy the matching v0.5.18 API, frontend and updater together. Application updates still rebuild only the API and frontend; they do not replace the running updater. During a maintenance window with no active or recovery-required task, preserve the state volume and backup, set AIRMUX_UPDATER_IMAGE in .env to the verified release digest, and recreate updater and frontend. Never recreate the updater during backup or migration. Use the Release attachment for the exact digest.

The same-origin /updates/observe route only accepts a one-day, task-scoped read-only credential issued through the administrator API. It exposes no updater control token, image manifest or backup path and cannot check, download or restart updates. The same browser tab keeps this credential and its last safe snapshot in sessionStorage; refreshing while the API is unavailable restores /update-progress without granting management access. Logout and account changes clear local observation data. Expired credentials or evicted tasks require signing in again once the service returns.

Progress shows actual downloaded bytes, completed layers, cached layers and extraction activity. Unknown totals have no estimated percentage. Docker config.json and credential helpers remain the source of registry authentication. The existing state volume retains the latest five update records; release checks preserve them. High-frequency bytes update a snapshot instead of adding log rows. Each task retains at most 200 key events and marks truncation. Database backup retention and manual recovery remain unchanged.
