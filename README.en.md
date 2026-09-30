# Airmux RS

[简体中文](README.md) · **English**

Airmux RS is a configuration workspace for managing subscription sources, configuration plans, published versions, and client access links.

**Rust API · Vue 3 · PostgreSQL · Docker / linux/amd64**

[Download](https://github.com/jilinker/airmux-rs-public/releases/latest) · [Deployment guide](docs/DEPLOYMENT.md)

Source code is maintained privately. This public repository distributes deployment documentation, redacted screenshots, and release metadata.

## Features

| Module | Capabilities |
| --- | --- |
| Sources and nodes | Import files, fetch URL subscriptions, refresh on a schedule, and manage custom nodes. |
| Plans and templates | Create plans with custom groups, region matching, residential groups, and group references. |
| Routing and DNS | Manage rule sets, routing rules, DNS policies, resolvers, and runtime settings. |
| Preview and publication | Review redacted previews and validation results, publish immutable versions, and download configurations. |
| Access links | Follow the latest version or pin one; copy, enable, pause, rotate, or delete links. |
| System updates | Validate public release manifests, separate preparation and restart, and back up the database; the image repository remains configurable. |

## Screenshots

Source, plan, link, and activity names in these screenshots were masked before capture.

![Overview: personal resource statistics and recent activity, with sensitive fields masked](docs/images/overview.jpg)

![Configuration plans: proxy groups, default and fallback roles, and a residential group; plan names masked](docs/images/plans.jpg)

![Access links: version policies, switches, and management actions; names and timestamps masked](docs/images/links.jpg)

## Installation and updates

Releases are published in the public [jilinker/airmux-rs-public](https://github.com/jilinker/airmux-rs-public) repository. Deployment does not require a GitHub repository setting or GitHub token; the image repository remains configurable in deployment settings.

- [English deployment guide](docs/DEPLOYMENT.md)
- [中文部署指南](docs/DEPLOYMENT.zh-CN.md)

The release image targets Linux `amd64` and runs with Docker Engine and the Compose plugin. Follow the deployment guide to configure the independent encryption key, updater token, and registry credentials.
