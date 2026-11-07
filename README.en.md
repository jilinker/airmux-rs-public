# Airmux RS

[简体中文](README.md) · **English**

Manage subscription sources and manual nodes, then generate Mihomo YAML or native Loon configurations through common and client-specific plans. Includes private per-user resources, invitation login, remote rules, cached subscription links and Docker Compose updates.

**Rust API · Vue 3 · PostgreSQL 17 · Docker / linux/amd64**

[Releases](https://github.com/jilinker/airmux-rs-public/releases/latest) · [Docker Hub](https://hub.docker.com/r/jaelinker/airmux) · [Deployment](docs/DEPLOYMENT.md)

This repository distributes installation examples, version manifests and release notes. Source code is maintained privately.

Download matching compose.yaml, config.yaml and .env into a separate directory such as /srv/airmux. Replace the database and administrator passwords, stable encryption key, updater token, public URL and absolute deployment path.

```sh
cd /srv/airmux
chmod 600 config.yaml .env
docker compose config --quiet
docker compose up -d --wait
docker compose ps
```

The image is `docker.io/jaelinker/airmux:v0.5.4`; the default HTTP port is 8080. The first administrator must change the initial password. Use compose.external.yaml for an existing PostgreSQL server. See the deployment guide for configuration ownership and recovery.

Version 0.5.0 introduces a new database generation. Direct upgrades from 0.4.x are unsupported: install into a separate empty database and preserve the old database and encryption key. Later versions use incremental SQL migrations.

Administrators open the updater from the version badge beside the brand, prepare an image and choose when to restart. Failure stops the API and retains backup metadata for manual recovery; there is no automatic rollback.

Loon validation is deferred in this round. Verify actual SMTP delivery and SSH server connections in your deployment. Version-specific release notes state the verified scope.
