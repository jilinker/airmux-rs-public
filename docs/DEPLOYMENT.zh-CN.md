# 生产部署

**简体中文** · [English](DEPLOYMENT.md) · [返回 README](../README.md)

[首次安装](#首次安装) · [启动服务](#启动服务) · [升级与恢复](#升级与恢复) · [发布源配置](#发布源配置) · [本机验证](#本机验证)

发布镜像的目标平台为 `linux/amd64`，包含 API、迁移和管理员初始化工具、nginx、前端静态资源、Python 更新服务及 Docker CLI/Compose 插件。应用镜像与更新服务镜像独立固定，应用升级不会替换正在运行的更新服务。

## 首次安装

### 1. 准备部署目录

将运行配置放在源码仓库之外。以下命令使用 `/srv/airmux`；使用其他目录时，需将配置中的路径统一替换为对应绝对路径。

先获取仓库中的 [compose.yaml](../deploy/compose.yaml) 与 [config.example.yaml](../config.example.yaml)，再从公共发行目录执行：

```sh
export AIRMUX_DEPLOY_DIR=/srv/airmux
mkdir -p "$AIRMUX_DEPLOY_DIR/secrets"
chmod 700 "$AIRMUX_DEPLOY_DIR/secrets"
install -m 0644 deploy/compose.yaml "$AIRMUX_DEPLOY_DIR/compose.yaml"
test -e "$AIRMUX_DEPLOY_DIR/config.yaml" || install -m 0644 config.example.yaml "$AIRMUX_DEPLOY_DIR/config.yaml"
test -e "$AIRMUX_DEPLOY_DIR/.env" || install -m 0600 /dev/null "$AIRMUX_DEPLOY_DIR/.env"
test -e "$AIRMUX_DEPLOY_DIR/runtime.env" || install -m 0600 /dev/null "$AIRMUX_DEPLOY_DIR/runtime.env"
for name in airmux_encryption_key airmux_updater_token docker_config.json; do
  test -e "$AIRMUX_DEPLOY_DIR/secrets/$name" || install -m 0600 /dev/null "$AIRMUX_DEPLOY_DIR/secrets/$name"
done
```

`test -e` 保留已有文件。更新服务将部署目录挂载到容器内的同一路径，保证它生成的 `runtime.env` 能被主机 Compose 使用。默认 `config.yaml` 中的四个部署路径均以 `/srv/airmux` 为基础，目录变更时需同步修改。

### 2. 填写密钥与仓库凭据

通过编辑器或密钥管理工具填写 `secrets/` 中的空文件，权限保持 `0600`：

| 文件 | 内容 |
| --- | --- |
| `airmux_encryption_key` | 32 字节随机加密密钥，建议使用 base64 编码。 |
| `airmux_updater_token` | 独立生成的更新服务鉴权 Token，例如 32 字节随机值的十六进制编码。 |
| `docker_config.json` | Docker CLI 可直接使用的镜像仓库登录配置。 |

新安装时可用 `openssl rand -base64 32` 生成加密密钥，用 `openssl rand -hex 32` 生成独立的更新 Token。只向新建的空文件写入，日常升级保留已有密钥。镜像登录配置必须能在更新服务容器内使用，不能依赖容器内不存在的主机凭据助手。

### 3. 填写环境配置

在 `.env` 中配置部署参数。下面的仓库、域名、密码和摘要均为占位值，需替换；镜像摘要可从目标 Release 的 `release-manifest.json` 获取。

```dotenv
AIRMUX_DEPLOY_DIR=/srv/airmux
AIRMUX_IMAGE=registry.example.com/your-namespace/airmux
AIRMUX_APP_IMAGE=registry.example.com/your-namespace/airmux@sha256:...
AIRMUX_UPDATER_IMAGE=registry.example.com/your-namespace/airmux@sha256:...
POSTGRES_PASSWORD=generate-a-long-random-value
DATABASE_URL=postgres://airmux:URL_ENCODED_PASSWORD@postgres:5432/airmux
AIRMUX_ORIGIN=https://airmux.example.com
```

`DATABASE_URL` 中的密码应与 `POSTGRES_PASSWORD` 对应，特殊字符需要 URL 编码。默认前端端口为 `8080`，可通过 `AIRMUX_HTTP_PORT` 修改。生产部署默认 `COOKIE_SECURE=true`，通过 HTTPS 反向代理访问；本地 HTTP 验证可设置 `COOKIE_SECURE=false` 并填写对应 HTTP 来源。

`config.yaml` 当前读取格式为 **JSON**，JSON 是 YAML 的子集。保留示例结构，不要直接改写为普通 YAML 键值格式。

### 4. 执行迁移并创建管理员

API 不会在启动时自动执行迁移。先启动 PostgreSQL，再显式运行迁移和一次性管理员初始化工具。以下密码输入命令适用于 Bash/Zsh；密码由标准输入传递。

```sh
cd "$AIRMUX_DEPLOY_DIR"
docker compose --project-name airmux --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" up -d --wait postgres

docker compose --project-name airmux --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" run --rm --no-deps \
  --entrypoint /usr/local/bin/migrate api

read -r -s AIRMUX_ADMIN_PASSWORD
printf '%s\n' "$AIRMUX_ADMIN_PASSWORD" | docker compose --project-name airmux \
  --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" run --rm --no-deps -T \
  --entrypoint /usr/local/bin/bootstrap_admin api admin
unset AIRMUX_ADMIN_PASSWORD
```

已有管理员时，初始化工具会拒绝再次运行。新管理员首次登录需要修改初始密码。

## 启动服务

后续 Compose 操作使用相同部署路径和两个环境文件：

```sh
export AIRMUX_DEPLOY_DIR=/srv/airmux
docker compose --project-name airmux --project-directory "$AIRMUX_DEPLOY_DIR" \
  --env-file "$AIRMUX_DEPLOY_DIR/.env" \
  --env-file "$AIRMUX_DEPLOY_DIR/runtime.env" \
  -f "$AIRMUX_DEPLOY_DIR/compose.yaml" up -d
```

只有 nginx 发布主机端口。它代理 `/api/` 和 `/sub/`，不记录包含访问 Token 的 `/sub/` URL。API 与更新服务不直接暴露到主机，更新接口不会通过 nginx 转发。

更新服务仅在 Compose 内部网络可达，请求必须携带 `secrets/airmux_updater_token` 中的 Token。生产使用前确认密钥、镜像凭据、HTTPS 来源及 Docker Socket 权限均已配置，并在独立预发布环境验证完整升级与备份恢复流程。

## 升级与恢复

### 升级流程

更新服务先验证带固定镜像摘要的发布清单，再拉取镜像。准备与重启分开执行；重启阶段依次停止 API、生成 PostgreSQL 自定义格式备份、验证备份、执行目标版本迁移、重建 API 并等待就绪。

迁移或健康检查失败时，API 保持停止，并记录 `needs_recovery`。检查状态和备份后，在主机上决定修复目标版本或恢复备份。不要让旧版本应用连接部分迁移的数据库。

### 查看持久状态

在部署目录执行：

```sh
docker compose --env-file .env --env-file runtime.env -f compose.yaml exec -T updater \
  python3 -m json.tool /var/lib/airmux-updater/state.json
```

状态包含执行步骤和备份位置。恢复前保留 `state.json`、`runtime.env` 和对应数据库备份，并查看容器日志。

API 重启期间，前端对需要管理员权限的状态接口进行重试。若 API 因失败持续离线，应在 Docker 主机恢复；不要为获取状态而暴露更新服务端口。

只有确认数据库、API 就绪与前端均正常后，才归档失败状态并将更新服务恢复为 idle。确认恢复成功前保留备份。自动更新不会代替人工执行破坏性恢复或清除 `needs_recovery`。

## 发布源配置

### 部署侧

| 配置项 | 说明 |
| --- | --- |
| `AIRMUX_IMAGE` | `registry/namespace/image`，不含标签或摘要；发布清单必须指向该仓库。 |
| `AIRMUX_APP_IMAGE` | 当前 API 与前端镜像，使用不可变摘要。 |
| `AIRMUX_UPDATER_IMAGE` | 独立固定的更新服务镜像，应用更新不会替换它。 |

发布版本固定从公共仓库 [`jilinker/airmux-rs-public`](https://github.com/jilinker/airmux-rs-public) 读取，无需在部署侧配置 GitHub 仓库或 GitHub Token。应用发布与 `AIRMUX_IMAGE` 使用同一镜像仓库，镜像地址仍需配置。

在 Compose 以外运行更新服务时，环境变量优先于 `config.yaml` 的可选 `image` 字段。配置缺失或格式错误会明确失败。修改镜像来源后需要重建更新服务，已有升级准备或执行中时不要切换来源。

### GitHub Actions

私有 CI 负责验证并构建镜像，配置仓库变量 `REGISTRY_HOST`、`IMAGE_REPOSITORY`，以及 Secret `REGISTRY_USERNAME`、`REGISTRY_PASSWORD`，再生成经过 allowlist 的公共发行包。公共仓库 Actions 使用自身的 `GITHUB_TOKEN` 创建 Release；部署用户无需配置或提供 GitHub Token。

维护者在私有源码仓库执行 `python3 scripts/publish-public-release.py vX.Y.Z --publish`，工具通过独立公共克隆同步文件与标签，不传递私有 Git 历史。私有 CI 可使用仅对公共仓库有写权限的 `PUBLIC_RELEASE_SSH_KEY` 自动同步；未配置时，工作流保存公共发行包 Artifact。部署用户无需这项发布凭据。

部署 Compose 的来源配置不会自动修改 GitHub Actions 的构建配置。

### 已构建镜像的发布

已由获授权的本机构建并推送镜像时，可在推送标签前提交 `.github/release-manifests/<tag>.json`。工作流验证版本、架构和不可变摘要，执行回归检查并同步公共标签后，公共 Actions 将清单发布为 `release-manifest.json` 附件。

此路径不需要在 GitHub 中配置镜像仓库登录凭据；没有对应清单的标签使用常规构建与推送流程。

## 本机验证

`deploy/local/` 同时被 Git 与 Docker 构建忽略。其 Compose 服务可加入已有 PostgreSQL 网络并复用现有验证数据库。

当 PostgreSQL 容器由此 Compose 项目以外的方式管理时，为更新服务设置 `AIRMUX_DATABASE_CONTAINER` 为现有容器名。更新服务通过 `docker exec` 执行备份及验证，应用操作仍使用配置的 Compose 项目。维护共享本地环境时不要重新初始化另一套验证数据库。
