# Airmux RS

**简体中文** · [English](README.en.md)

Airmux RS 是一个用于管理订阅源、配置方案、发布版本和客户端访问链接的配置工作空间。

**Rust API · Vue 3 · PostgreSQL · Docker / linux/amd64**

[下载版本](https://github.com/jilinker/airmux-rs-public/releases/latest) · [部署指南](docs/DEPLOYMENT.zh-CN.md)

源码由私有仓库维护；此公共仓库提供部署文档、脱敏截图和发行文件。

## 功能

| 模块 | 能力 |
| --- | --- |
| 订阅源与节点 | 导入文件、获取 URL 订阅、定时刷新并管理自定义节点。 |
| 配置方案与模板 | 创建配置方案，自定义分组、地区匹配、家宽分组及组间引用。 |
| 路由与 DNS | 管理规则集、路由规则、DNS 策略、解析器及运行参数。 |
| 预览与发布 | 查看脱敏预览与校验结果，发布不可变版本并下载配置。 |
| 访问链接 | 跟随最新版本或固定版本，支持复制、启停、轮换和删除。 |
| 系统更新 | 校验公共发行清单，分步准备与重启，备份数据库；镜像仓库可配置。 |

## 界面预览

截图中的来源名称、方案名称、链接名称和活动时间均已脱敏。

![概览：个人资源统计与最近活动，敏感信息已打码](docs/images/overview.jpg)

![配置方案：代理组、默认入口、兜底和独立家宽分组，方案名称已打码](docs/images/plans.jpg)

![访问链接：版本策略、滑动开关与管理操作，名称和时间已打码](docs/images/links.jpg)

## 安装与更新

发行版本固定发布在公共仓库 [jilinker/airmux-rs-public](https://github.com/jilinker/airmux-rs-public)。部署不需要 GitHub 仓库配置或 GitHub Token；镜像仓库地址可在部署配置中指定。

- [中文部署指南](docs/DEPLOYMENT.zh-CN.md)
- [English deployment guide](docs/DEPLOYMENT.md)

部署镜像面向 Linux `amd64`，使用 Docker Engine 与 Compose 插件运行。请按部署指南配置独立的加密密钥、更新服务 Token 和镜像登录凭据。
