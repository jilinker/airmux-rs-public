# Docker Compose 部署：三步启动

**简体中文** · [English](DEPLOYMENT.md) · [返回 README](../README.md)

准备好 Docker Engine 和 Compose 插件即可，支持 `linux/amd64`。只需 **`config.yaml`、`compose.yaml`、`.env`** 三个文件，无需克隆仓库、安装 Python 或执行初始化脚本。

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

## 3. 检查启动结果

```sh
docker compose ps
docker compose logs --tail=50 api
```

`api`、`postgres` 应显示 `healthy`，`frontend`、`updater` 应显示 `Up`。打开 `http://服务器IP:8080`，使用配置的管理员账号登录，首次登录后修改密码。

如启动失败，优先检查配置文件权限、密钥格式、两个文件的数据库密码，以及实际访问地址是否加入 `allowed_origins`。

停止服务使用 `docker compose down`，保留数据时不要加 `-v`。日常更新点击侧栏版本号操作，更新程序会维护 `.env` 中的镜像覆盖值。修改配置后执行 `docker compose up -d --force-recreate --wait`；手动切换版本时先备份，并清空 `.env` 的 `AIRMUX_APP_IMAGE` 覆盖值。

已有部署升级时保留原数据库、加密密钥与目录；不要覆盖已有配置。v0.1.2 的旧 `.compose.env` / `runtime.env` 编排仍受支持，无需为文档变化重新初始化数据库。
