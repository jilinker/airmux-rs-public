# Airmux RS

**简体中文** · [English](README.en.md)

管理多订阅源与手动节点，通过公共方案和客户端方案生成 Mihomo YAML 或 Loon 原生配置。个人资源按用户隔离，支持邀请登录、远程规则、访问链接缓存和 Docker Compose 系统更新。

**Rust API · Vue 3 · PostgreSQL 17 · Docker / linux/amd64**

[发行下载](https://github.com/jilinker/airmux-rs-public/releases/latest) · [Docker Hub](https://hub.docker.com/r/jaelinker/airmux) · [部署指南](docs/DEPLOYMENT.zh-CN.md)

此仓库只分发安装示例、版本清单和发行说明。源码在私有仓库维护。

## 安装

下载同版本的 compose.yaml、config.yaml 与 .env 到独立目录，例如 /srv/airmux。示例由本仓库提供，必改数据库密码、管理员密码、稳定加密主密钥、更新凭据、公开访问地址及部署绝对路径。

```sh
cd /srv/airmux
chmod 600 config.yaml .env
docker compose config --quiet
docker compose up -d --wait
docker compose ps
```

默认镜像为 `docker.io/jaelinker/airmux:v0.5.1`，默认端口为 8080。首次管理员登录需修改密码。已有 PostgreSQL 使用 compose.external.yaml，具体配置和恢复方式见 [中文部署指南](docs/DEPLOYMENT.zh-CN.md)。程序参数归 config.yaml，Docker 发布参数归 Compose 和 .env，管理页动态设置归数据库。

`0.5.0` 是全新数据库模型，旧 `0.4.x` 不支持直接升级。使用独立空库安装并保管原库与原密钥；新基线后续版本使用增量 SQL。

管理员通过品牌旁版本徽标打开更新弹窗，检查发行、准备镜像并选择维护时机重启。失败后停止服务并保留备份供人工恢复，不自动回滚。

本轮暂不验证 Loon；真实邮件投递和 SSH 实服连接需在部署环境验证。具体已验收范围见对应版本发行说明。
