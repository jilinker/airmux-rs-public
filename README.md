# Airmux RS

**简体中文** · [English](README.en.md)

Airmux RS 是一个用于管理订阅源、配置方案、发布版本和客户端访问链接的配置工作空间。

**Rust API · Vue 3 · PostgreSQL · Docker / linux/amd64**

[下载版本](https://github.com/jilinker/airmux-rs-public/releases/latest) · [部署指南](docs/DEPLOYMENT.zh-CN.md)

源码由私有仓库维护；此公共仓库提供部署文档、脱敏截图和发行文件。

## 安装与更新

部署只需 **三个文件、三步操作**，前提是已经安装 Docker 与 Compose 插件。

1. 下载 [config.yaml](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/config.yaml) 和 [compose.yaml](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/compose.yaml)，放在 `/srv/airmux`；按文件内中文注释修改管理员、数据库密码、密钥、更新凭据与访问地址。
2. 下载 [.env](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/.env)，填入相同数据库密码；镜像、端口与目录按需替换。执行：

   ```sh
   cd /srv/airmux
   chmod 600 config.yaml .env
   docker compose up -d --wait
   ```

3. 执行 `docker compose ps`、`docker compose logs --tail=50 api`，访问 `http://服务器IP:8080` 验证登录。

首次建表、迁移与管理员初始化由 Rust 启动自动完成。无需克隆仓库、安装 Python 或运行管理脚本。详细修改说明见[中文部署指南](docs/DEPLOYMENT.zh-CN.md) · [English](docs/DEPLOYMENT.md)。

## 功能

支持订阅源与节点、配置方案与模板、路由与 DNS、脱敏预览与发布、客户端访问链接及系统更新。

## 界面预览

![概览：个人资源统计与最近活动，敏感信息已打码](docs/images/overview.jpg)

![配置方案：代理组、默认入口、兜底和独立家宽分组，方案名称已打码](docs/images/plans.jpg)

![访问链接：版本策略、滑动开关与管理操作，名称和时间已打码](docs/images/links.jpg)
