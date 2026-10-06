# Docker Compose 部署：三步启动

**简体中文** · [English](DEPLOYMENT.md) · [返回 README](../README.md)

准备好 Docker Engine 和 Compose 插件即可，支持 `linux/amd64`。只需 **`config.yaml`、`compose.yaml`、`.env`** 三个文件，无需克隆仓库、安装 Python 或执行初始化脚本。

**默认由 Compose 启动 PostgreSQL 17**，无需另外安装数据库。使用已有数据库见[外置 PostgreSQL](#外置-postgresql)。

## 1. 下载配置，按中文注释修改

在服务器创建部署目录，下载公共仓库的两个 YAML 文件：

```sh
mkdir -p /srv/airmux
cd /srv/airmux
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/config.yaml -o config.yaml
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/compose.yaml -o compose.yaml
```

也可以直接下载：[config.yaml](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/config.yaml) · [compose.yaml](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/compose.yaml)。文件已提供中文注释，`compose.yaml` 默认不需要修改。

编辑 `config.yaml`：

| 配置 | 要修改的内容 |
| --- | --- |
| `database.url` | 替换 `CHANGE_ME_DATABASE_PASSWORD`，建议密码只用字母、数字、下划线或连字符；下一步在 `.env` 填同一密码。 |
| `administrator.username` / `password` | 设置首次管理员账号与密码。密码至少 8 位，包含大小写字母；账号默认 `admin`。 |
| `security.encryption_key` | 填入 `openssl rand -base64 32` 的输出，升级时保留此值。 |
| `updater.token` | 填入 `openssl rand -hex 32` 的输出，用于应用内部更新鉴权。 |
| `server.allowed_origins` | 远程访问时填写实际地址，如 `http://192.168.1.10:8080`。HTTPS 填写域名地址并把 `cookie_secure` 改为 `true`。 |

其余保持默认。若更换部署目录，修改 `deployment.directory`，并与下一步 `.env` 的目录保持一致。

## 2. 下载 .env，启动 Compose

```sh
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/.env -o .env
```

直接下载：[.env](https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/.env)。**修改 `POSTGRES_PASSWORD`，与 `config.yaml` 中的数据库密码一致。** 以下参数仅在有需要时替换：

| 参数 | 默认值 / 用途 |
| --- | --- |
| `AIRMUX_IMAGE_REPOSITORY` | 已填写公开镜像地址，通常无需修改，也无需 Docker 登录。 |
| `AIRMUX_VERSION` | 已填写发行版本，可替换为其他兼容版本。 |
| `AIRMUX_HTTP_PORT` / `AIRMUX_HTTP_BIND` | `8080` / `0.0.0.0`；更换端口时同步修改 `allowed_origins`。 |
| `AIRMUX_DEPLOY_DIR` | `/srv/airmux`；必须是这三个文件所在的绝对路径，与 `deployment.directory` 一致。 |

保存后启动：

```sh
chmod 600 config.yaml .env
docker compose up -d --wait
```

数据库、API、前端与更新程序由 Compose 启动。API 从只读挂载的 `config.yaml` 读取配置，通过 SQLx 自动建表、执行待完成迁移并创建首次管理员；已有管理员和数据不会被覆盖。

默认数据库用户和库名均为 `airmux`，API 连接 `postgres:5432`，不向宿主机暴露数据库端口。数据保存在 `postgres-data` 卷；`.env` 的 `POSTGRES_PASSWORD` 只在空数据卷首次初始化时设置密码，修改它不会重置已有密码。

## 3. 检查启动结果

```sh
docker compose ps
docker compose logs --tail=50 api
```

`api`、`postgres` 应显示 `healthy`，`frontend`、`updater` 应显示 `Up`。打开 `http://服务器IP:8080`，使用配置的管理员账号登录，首次登录后修改密码。

如启动失败，优先检查配置文件权限、密钥格式、两个文件的数据库密码，以及实际访问地址是否加入 `allowed_origins`。

停止服务使用 `docker compose down`，保留数据时不要加 `-v`。日常更新点击侧栏版本号操作，更新程序会维护 `.env` 中的镜像覆盖值。修改配置后执行 `docker compose up -d --force-recreate --wait`；手动切换版本时先备份，并清空 `.env` 的 `AIRMUX_APP_IMAGE` 覆盖值。

已有部署升级时保留原数据库、加密密钥与目录；不要覆盖已有配置。v0.1.2 的旧 `.compose.env` / `runtime.env` 编排仍受支持，无需为文档变化重新初始化数据库。

## 外置 PostgreSQL

仍按上面三步部署，仅在第 1 步将外置版本下载为 **`compose.yaml`**，不需要叠加其他 Compose 文件：

```sh
curl -fL https://raw.githubusercontent.com/jilinker/airmux-rs-public/main/compose.external.yaml -o compose.yaml
```

此版本不创建、启动或管理 PostgreSQL。提前准备好已有数据库和账号，账号须能执行建表及迁移。API 自动初始化表和首次管理员，**不会创建数据库本身**。`.env` 的 `POSTGRES_PASSWORD` 不再使用；数据库连接信息集中填写在 `config.yaml`。

### 远程 PG 或宿主机 PG

修改 `config.yaml` 中的以下值，其余必改项与默认部署相同：

```yaml
database:
  url: "postgres://airmux:YOUR_PASSWORD@db.example.com:5432/airmux"
  max_connections: 10
updater:
  enabled: false
```

地址必须能从 API 容器访问。宿主机 PG 可将 `db.example.com` 替换为 `host.docker.internal`；`localhost` 指向 API 容器本身。按数据库要求设置 TLS，例如连接串追加 `?sslmode=require`，并允许来自容器的数据库连接。

`.env` 保持 `AIRMUX_NETWORK_EXTERNAL=false`、`COMPOSE_PROFILES=`。执行 `docker compose up -d --wait` 后，检查 `api` 为 `healthy`、`frontend` 为 `Up` 即可。当前在线更新需要通过 Docker 备份 PG，因此此模式关闭更新程序；升级前通过数据库自己的备份方式备份，再按上文手动切换镜像版本。

### 同一 Docker 中已有的 PG 容器

让应用加入已有 PG 所在的网络，并使用其容器名作为连接地址。例如已有容器 `local-postgres`、网络 `local-postgres_default`，在 `.env` 修改：

```dotenv
AIRMUX_NETWORK_NAME=local-postgres_default
AIRMUX_NETWORK_EXTERNAL=true
COMPOSE_PROFILES=updates
```

在 `config.yaml` 中将 `database.url` 指向实际数据库，并在已有配置节中设置：

```yaml
deployment:
  database_container: "local-postgres"
updater:
  enabled: true
```

保留 `deployment` 与 `updater` 的其他字段，包括更新凭据及部署目录。更新程序通过 `docker exec` 在此 PG 容器内执行备份；确认该容器的 `pg_dump` / `pg_restore` 能以连接串的用户访问数据库，再启用在线更新。若不启用在线更新，保持 `COMPOSE_PROFILES=` 并设置 `updater.enabled: false`。

先启动已有 PG，再执行相同的 `docker compose up -d --wait`。此时不会创建第二个 PG 或新数据库，`docker compose down` 也不会停止已有 PG。

Compose 的网络和可选服务行为参考 [Docker 网络说明](https://docs.docker.com/compose/how-tos/networking/)与 [Profiles 说明](https://docs.docker.com/compose/how-tos/profiles/)。
