# Docker Compose 部署与配置

0.5.10 使用统一方案与配置库，通过一份基础配置和多份功能配置生成客户端配置。镜像为 docker.io/jaelinker/airmux，平台为 linux/amd64，最低升级版本为 0.5.0。旧 0.4.x 安装不能直接升级，必须使用独立空库。SMTP 实际投递由用户确认成功，SSH 默认身份已用临时真实服务器验证；外部服务器仍需按实际环境确认。Loon 本轮暂不验证。

0.5.10 未新增 SQL 从 0.5.9 升级保留现有组合方案

**从 0.5.9 之前升级会执行 0.5.9 的新增 SQL 清空旧公共方案、客户端方案、相关归档和全部访问链接，不进行迁移或兼容。** 账号、节点来源、节点、管理员地区与规则集、系统配置及历史迁移保留。升级前完成数据库备份并保管原加密主密钥。升级后重新创建配置、方案和访问链接；原链接失效。恢复旧方案需将升级前备份恢复到独立数据库，并使用原密钥和旧版镜像。

## 文件职责

| 文件 | 修改内容 |
| --- | --- |
| compose.yaml | 服务 网络 依赖 挂载 数据卷 健康检查与重启策略 |
| .env | 镜像 版本 平台 项目名 宿主端口 部署目录与 PostgreSQL 首次初始化值 |
| config.yaml | 数据库连接 程序监听 CORS 密钥 日志 首位管理员与更新器程序参数 |

API 环境变量只定位程序 YAML，不以 .env 覆盖程序参数。动态业务设置应由管理页写入数据库，不再复制到 YAML。config.yaml 不接受旧 deployment 段。

## 首次安装

1. 安装 Docker 和 Compose 插件，创建独立部署目录，例如 /srv/airmux。
2. 从同一兼容发行版本获取 compose.yaml config.yaml .env，放在该目录。使用源码示例时将 .env.example 复制为 .env。
3. 在 config.yaml 替换数据库密码 管理员初始密码 Base64 主密钥和更新凭据。可用 openssl rand -base64 32 生成主密钥，openssl rand -hex 32 生成更新凭据。保管原主密钥，后续更新不能随意更换。
4. 在 .env 设置镜像版本或固定摘要，使 POSTGRES_PASSWORD 与应用 database.url 中的密码一致。AIRMUX_DEPLOY_DIR 使用部署目录的绝对路径，AIRMUX_CONFIG_FILE 指向本份 YAML。
5. 按访问地址设置 server.allowed_origins 和 server.public_base_url。HTTPS 使用 server.cookie_secure 为 true。空库必须填写 administrator.email 和 administrator.password，邮箱视为已验证但首次登录必须改密。已有管理员时这些初始化值不覆盖数据库账号；旧 administrator.username 不再接受。管理员配置并启用 SMTP 后可邀请邮箱账号，临时密码或确认链接首次登录后必须设置新密码。

```sh
cd /srv/airmux
chmod 600 config.yaml .env
docker compose config --quiet
docker compose up -d --wait
docker compose ps
docker compose logs --tail=50 api
```

默认访问端口为 8080。宿主公开端口由 .env 的 AIRMUX_HTTP_PORT 控制，程序内部监听由 config.yaml 的 server.listen 控制。容器中使用 0.0.0.0 监听；前端代理 健康检查与更新就绪检查从 YAML 读取 API 端口。

更改 .env 不会修改已有 PostgreSQL 密码，实际轮换需先修改数据库并同步应用连接，不能只更改 POSTGRES_PASSWORD。

## 外置 PostgreSQL

用同版 compose.external.yaml 替换部署目录的 compose.yaml，再修改 config.yaml 的 database.url。应用不会创建外部数据库，账号需有建表和迁移权限。宿主机数据库可通过 host.docker.internal 访问；加入既有 Docker 网络时配置 .env 中的 AIRMUX_NETWORK_NAME 和 AIRMUX_NETWORK_EXTERNAL。

启用在线更新时必须设置 AIRMUX_DATABASE_CONTAINER，指向可执行 pg_dump 与 pg_restore 的 PostgreSQL 容器。当前更新器不直接备份远程非容器数据库；这种情况应关闭 updater.enabled，移除 COMPOSE_PROFILES 中的 updates，人工备份和更新。

## SSH 默认身份与主机记录

0.5.1 的 SSH 密钥认证允许私钥留空，使用 API 运行用户的默认身份文件或 SSH agent。密码认证仍需填写密码。指纹和 known_hosts 记录均可不填，此时使用运行环境已有记录及 fetch.ssh_known_hosts_file 指定的持久化文件，首次公钥会被记录，已记录公钥变化时拒绝连接。需要预先锁定主机时，可填写指纹或显式公钥记录。

Docker 不会自动使用宿主机密钥。需要宿主身份时，在私有 Compose 中给 api 显式只读挂载所需身份文件，例如 /root/.ssh/id_ed25519；使用 agent 时显式挂载套接字并设置 SSH_AUTH_SOCK。不要将私钥写入发行文件。默认 Compose 已持久化 /var/lib/airmux-ssh，升级时保留该卷。

## 更新与人工恢复

config.yaml 的 updater.enabled 和 .env 的 COMPOSE_PROFILES=updates 分别声明程序配置及更新器服务。管理员点击左上品牌旁版本徽标打开系统更新弹窗。检查更新只读取发行信息；下载并更新直接准备镜像，无二次确认；准备完成后点击立即重启，并确认维护后执行。打开弹窗只读取状态。

更新器需要 Docker socket 以及宿主和容器完全相同的可写部署目录。Compose 只显式传入镜像仓库 部署目录 项目名 目标数据库容器四个编排参数，不将完整 .env 注入 API 或更新器。

默认状态与备份路径 /var/lib/airmux-updater 必须持久化。修改 updater.state_directory 时同步调整 Compose 卷目标。使用 token_file 或 encryption_key_file 时，按各消费服务声明只读文件挂载；私有镜像仓库 Docker 凭据也通过 Compose 单独挂载。

准备时核对当前及目标镜像的数据库代际标签，并在无网络、只读且不挂载数据库的临时容器中核对目标 SQL 文件与公开发行清单的 SHA256。旧安装或清单不符在停机前阻断。执行前再次核对运行镜像未变化。

更新顺序为校验目标镜像 停止 API 备份并校验数据库 写入 .env 的新应用镜像 迁移 启动并检查 API 更新前端。更新不会重写 config.yaml 或覆盖 .env 其他字段；更新器自身镜像由运维在后续维护窗口重建。

执行失败进入 needs_recovery 并尝试停止 API，停止失败会明确记录无法确认停止状态。API 停止后网页无法代理读取更新器，界面只继续观察并提示维护者检查服务器，不将网络错误当作确定的失败阶段。先保留更新状态 数据库备份 原主密钥及部署文件，再按失败阶段恢复数据库与原镜像。若迁移已经执行，不可只回退镜像并假定旧程序兼容新表。恢复后检查健康和业务数据，不绕过迁移校验和或删除迁移记录。

源码辅助工具 deploy/manage.py 可在新目录初始化三份文件，render 只检查配置一致性，不重写 .env。直接使用 Compose 不需要该工具；docker compose config --quiet 只验证编排语法，不能代替启动时的程序 YAML 校验。

人工恢复时先读取持久化 state.json 的 phase、steps、backup 和 sourceImage，再核对 Docker 中的真实运行情况。sourceImage 是准备时实际运行的本地不可变镜像标识；恢复完成前不要清理该镜像或更新状态。对备份先执行 pg_restore --list 验证。无效或未完成的备份不能用于恢复。

若迁移尚未开始，核对数据库未改变后恢复原镜像。若迁移已经运行，将验证后的备份恢复到独立空数据库，先验证数据，再在 config.yaml 切换到恢复库，并将 .env 的 AIRMUX_APP_IMAGE 设为原镜像。保留失败库用于核查，不在业务库中执行隐含删除。启动 API 和前端，确认 /health/ready、登录与业务数据后，再由维护者归档本次更新状态。待恢复状态不可在网页强行清除。
