# Airmux RS

[简体中文](README.md) · **English**

Airmux RS is a configuration workspace for managing subscription sources, configuration plans, published versions, and client access links.

**Rust API · Vue 3 · PostgreSQL · Docker / linux/amd64**

[Download](https://github.com/jilinker/airmux-rs-public/releases/latest) · [Deployment guide](docs/DEPLOYMENT.md)

Source code is maintained privately. This public repository distributes deployment documentation, redacted screenshots, and release metadata.

## Features

Manage subscription sources and nodes, configuration plans and templates, routing and DNS, redacted previews and publications, client access links, and system updates.

## Screenshots

![Overview: personal resource statistics and recent activity, with sensitive fields masked](docs/images/overview.jpg)

![Configuration plans: proxy groups, default and fallback roles, and a residential group; plan names masked](docs/images/plans.jpg)

![Access links: version policies, switches, and management actions; names and timestamps masked](docs/images/links.jpg)

## Installation and updates

Releases are published in the public [jilinker/airmux-rs-public](https://github.com/jilinker/airmux-rs-public) repository. Deployment needs no GitHub repository setting or token. Follow the [English deployment guide](docs/DEPLOYMENT.md) or [中文部署指南](docs/DEPLOYMENT.zh-CN.md) to install Python 3 and PyYAML, then run:

```sh
python3 deploy/manage.py init --config /srv/airmux/config.yaml
cd /srv/airmux
docker compose --env-file .compose.env --env-file runtime.env up -d --wait
```

Edit only the standard YAML `config.yaml`. API startup automatically applies pending SQLx migrations and initializes the first admin under a transaction lock, so no manual migrate/bootstrap commands or editable `.env` are needed. Change the generated admin password on first login and preserve the original encryption key. For offline installation, pass an image digest to init with `--image`.
