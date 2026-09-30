# Docker Compose 部署

**简体中文** · [English](DEPLOYMENT.md) · [返回 README](../README.md)

适用于 Linux `amd64`、Docker Engine 与 Compose 插件。**Compose 负责服务编排，运行参数集中在 `config.yaml`，通过只读挂载交给 API 和更新程序。**首次安装无需手动执行 SQL、迁移或创建管理员。

## 1. 准备发行目录

安装 Docker Engine 与 Compose 插件，确认 `docker compose version` 可用。Debian / Ubuntu 可安装其余依赖：

```sh
sudo apt-get update
sudo apt-get install -y git python3 python3-yaml
sudo mkdir -p /srv/airmux
sudo chown "$USER":"$USER" /srv/airmux
git clone https://github.com/jilinker/airmux-rs-public.git airmux-distribution
cd airmux-distribution
```

其他系统使用 `python3 -m pip install -r deploy/requirements.txt` 安装 PyYAML。

## 2. 首次生成配置

```sh
python3 deploy/manage.py init --config /srv/airmux/config.yaml
```

此命令从固定的公共 Release 读取镜像摘要，生成数据库密码、初始管理员密码、32 字节加密密钥和更新凭据。文件已存在时拒绝覆盖。离线安装可以指定本机已有的镜像：

```sh
python3 deploy/manage.py init --config /srv/airmux/config.yaml --image registry.example.com/team/airmux@sha256:REPLACE_WITH_DIGEST
```

用编辑器打开 `/srv/airmux/config.yaml`，保存初始管理员密码，并修改访问来源和端口。配置文件保持 `0600`；不要把它提交到 Git。修改配置后，在发行目录重新生成编排参数：

```sh
python3 deploy/manage.py render --config /srv/airmux/config.yaml
```

## 3. 用 Compose 启动

```sh
cd /srv/airmux
docker compose --env-file .compose.env --env-file runtime.env up -d --wait
docker compose --env-file .compose.env --env-file runtime.env ps
```

访问配置的地址，默认 `http://localhost:8080`。使用 `administrator.username` 与生成的密码登录，首次登录必须改密码。管理员创建成功后，可以从配置中删除 `administrator.password`；已有管理员不会因重启或配置修改而被覆盖。

停止服务时保留数据卷：

```sh
docker compose --env-file .compose.env --env-file runtime.env down
```

API 启动先通过 SQLx 的迁移记录判断数据库状态：空库执行全部内置 SQL，已有库只应用待执行迁移，再校验迁移版本和校验和。随后在事务锁下初始化首个管理员，防止并发重复创建。初始化失败时 API 不开放业务接口。

## 配置说明

| 配置项 | 作用 |
| --- | --- |
| `database` | PostgreSQL URL、连接池上限；默认 Compose 内的 `postgres:5432`。 |
| `server` | API 监听地址、浏览器访问来源、Cookie 安全属性。Docker 使用 `0.0.0.0:3000`，端口可调整。 |
| `administrator` | 首次初始化的用户名与密码，仅在没有管理员时使用。 |
| `security` | `encryption_key` 为 32 字节密钥的 Base64；升级时必须保留原值。 |
| `auth` / `logging` | 会话时长、密码运算并发数、日志过滤级别。 |
| `fetch` / `worker` | 订阅获取大小与超时、受限端点、任务处理开关与轮询间隔。 |
| `deployment` | 部署目录、镜像仓库及摘要、HTTP 地址与端口、Compose 项目名、PostgreSQL 镜像。 |
| `updater` | 开关、内部地址与端口、凭据、状态和备份目录、最小剩余空间。 |

`compose.yaml` 是编排文件；`.compose.env` 是从配置生成的 Compose 参数，`runtime.env` 只记录在线更新选择的镜像覆盖值。它们不承载另一套人工维护的应用配置。`nginx.conf` 同样自动生成，跟随 API 端口。应用运行时只读取挂载的 `config.yaml`，`AIRMUX_CONFIG` 仅指定文件路径。

配置修改后，用下面的 Compose 命令重建应用容器，使只读挂载和启动时读取的配置生效：

```sh
cd /srv/airmux
docker compose --env-file .compose.env --env-file runtime.env up -d --force-recreate --wait
```

外网部署配置 HTTPS 来源并启用 `server.cookie_secure`，由反向代理提供 TLS。更改 HTTP 端口时同步修改 `server.allowed_origins`。可选 `security.encryption_key_file` 和 `updater.token_file` 必须位于部署目录内，权限 `0600`，且不能与对应的内联值同时配置。

已有 Docker PostgreSQL 使用 `database.url` 指向现有服务，并设置 `deployment.database_container` 和 `deployment.database_network`。渲染后不创建新的 PostgreSQL 服务；更新程序通过指定容器备份。远程数据库无法提供此容器时，关闭在线更新并自行管理备份与升级。

镜像仓库地址可配置，镜像固定为 `repository@sha256:digest`。需要登录时，先在主机执行 `docker login`；给更新程序的 `deployment.docker_config_file` 必须是含实际 `auths` 的私有凭据文件，不能仅依赖主机的 credential helper。无需 GitHub Token 或私有源码访问权限。

## 备份、升级与恢复

内置数据库的备份与备份有效性检查：

```sh
cd /srv/airmux
umask 077
docker compose --env-file .compose.env --env-file runtime.env exec -T postgres pg_dump -U airmux -Fc airmux > backup.dump
docker compose --env-file .compose.env --env-file runtime.env exec -T postgres pg_restore --list < backup.dump > /dev/null
```

同时保留原 `config.yaml` 和加密密钥。上述命令使用默认数据库与用户，修改过时按实际值调整。

日常在线更新在「系统设置 → 版本」中操作，顺序是准备镜像、停止 API、备份并校验、迁移、启动及健康检查。失败保留备份和恢复状态，不自动回滚已执行的数据库迁移。

手动升级先备份，修改配置中的 `deployment.app_image` 和 `deployment.updater_image`，运行 `render` 后使用 Compose 启动目标镜像。目标 API 自动应用待执行迁移。恢复时先停止 API，用旧版匹配的数据库备份恢复，再启动旧镜像；不要仅降级镜像而保留新版数据库。

v0.1.1 及更早部署先备份，再把旧环境变量中的数据库、来源、会话及密钥设置搬到 `config.yaml`，固定 v0.1.2 或更新镜像，并重新生成 Compose 参数。必须保留原数据库和原密钥，不要重新运行首次初始化来替换配置。
