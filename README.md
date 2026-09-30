# Airmux RS

**简体中文** · [English](README.en.md)

Airmux RS 是一个用于管理订阅源、配置方案、发布版本和客户端访问链接的配置工作空间。

**Rust API · Vue 3 · PostgreSQL · Docker / linux/amd64**

[下载版本](https://github.com/jilinker/airmux-rs-public/releases/latest) · [部署指南](docs/DEPLOYMENT.zh-CN.md)

源码由私有仓库维护；此公共仓库提供部署文档、脱敏截图和发行文件。

## 功能

支持订阅源与节点、配置方案与模板、路由与 DNS、脱敏预览与发布、客户端访问链接及系统更新。

## 界面预览

![概览：个人资源统计与最近活动，敏感信息已打码](docs/images/overview.jpg)

![配置方案：代理组、默认入口、兜底和独立家宽分组，方案名称已打码](docs/images/plans.jpg)

![访问链接：版本策略、滑动开关与管理操作，名称和时间已打码](docs/images/links.jpg)

## 安装与更新

发行版本固定发布在公共仓库 [jilinker/airmux-rs-public](https://github.com/jilinker/airmux-rs-public)。部署不需要 GitHub 仓库配置或 GitHub Token；请按[中文部署指南](docs/DEPLOYMENT.zh-CN.md)或 [English deployment guide](docs/DEPLOYMENT.md) 安装 Python 3、PyYAML，并使用管理脚本：

```sh
python3 deploy/manage.py init --config /srv/airmux/config.yaml
cd /srv/airmux
docker compose --env-file .compose.env --env-file runtime.env up -d --wait
```

用户只编辑标准 YAML `config.yaml`。API 启动时自动执行未完成 SQLx 迁移并在事务锁下初始化首 admin，无需手动 migrate/bootstrap 或编辑 `.env`。首次生成的 admin 密码必须修改，原加密 key 必须保留。离线安装可在 init 时使用 `--image` 指定镜像 digest。
