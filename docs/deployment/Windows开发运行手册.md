# Windows 开发运行手册

## 1. 准备环境

1. 启动 Docker Desktop，确认使用 Linux containers。
2. 打开 Git Bash。
3. 进入项目：

```bash
cd /d/媒体架构/1Cat-Marketing-OS
```

`Docker Desktop is running` 不代表 Engine 已就绪；要以 `docker info` 能成功返回 Server 信息为准。

### Docker Hub 无法直连时

项目支持本机级镜像源切换，不必修改 Docker Desktop 全局设置。在执行
`./bin/1cat init` 后，只修改不会进入 Git 的 `.env`：

```dotenv
DOCKER_HUB_REGISTRY=docker.1ms.run
HERMES_IMAGE_REGISTRY=dockerproxy.net
```

前者用于常规 Docker Hub 镜像，后者允许 Hermes 大镜像使用独立代理。镜像
名称仍带固定 SHA-256 摘要；代理缺层或内容不一致时构建会失败，不得删除摘要
绕过校验。官方源恢复后可将两项改回 `docker.io`。第三方代理只适合开发环境，
使用前应由项目所有者确认信任边界。

## 2. 第一次启动（合成执行）

```bash
./bin/1cat doctor
./bin/1cat init
./bin/1cat up
./bin/1cat status
./bin/1cat smoke
./bin/1cat e2e
```

打开 <http://localhost:8080>。该地址直接显示完整 Demo1 工作台。用户名为 `admin`，密码只在本机 `.env` 的 `INITIAL_ADMIN_PASSWORD` 中查看；不要把密码写入截图、文档或 Git。

默认 `HERMES_EXECUTION_ENABLED=false`。此时 Worker 会运行受控合成闭环，适合验证容器、OIDC、数据库、状态机和前端。

## 3. Demo1 与真实 Runtime

不再需要单独启动 4173。正式统一入口如下：

- 完整 Demo1 工作台：<http://localhost:8080>
- PMA Runtime 黄金链路：<http://localhost:8080/?view=runtime>
- Agent 配置与 DeepSeek Key：工作台左侧“Agent 配置”→“模型与权限”

Runtime 页面使用同一个 `admin` 账号。黄金链路的验收顺序是：

```text
创建 Commitment
→ accepted
→ queued AgentRun
→ Worker 创建 Attempt/Lease
→ running
→ evidence_accepted
→ 人工确认 Commitment fulfilled
```

完整工作台仍使用 localStorage 保存演示对象；PMA Runtime 页面使用服务端
Commitment/Run/Attempt/Timeline。两类状态会在界面中明确区分。

需要调试前端热更新时，可在 `apps/workspace` 中执行 `npm run dev`，4173 只作为开发端口，
并将 `/auth`、`/v1`、`/health`、`/local-admin` 代理到 8080。

## 4. 真实 Hermes Run

```bash
cd /d/媒体架构/1Cat-Marketing-OS
./bin/1cat auth deepseek
./bin/1cat restart-agents
./bin/1cat model-test
.venv/Scripts/python.exe scripts/real_agent_demo.py --role pma
.venv/Scripts/python.exe scripts/real_agent_demo.py --role bga
.venv/Scripts/python.exe scripts/real_agent_demo.py --role mo
```

`auth deepseek` 会在终端隐藏输入 Key，并先验证 Model Gateway 到 DeepSeek 的
`/v1/models`。只有验证成功才打开真实执行。三个验收脚本分别创建受控合成 Run，
输出 Runtime Run ID、Attempt ID、Hermes Run ID、correlation ID、模型、终态和实际
候选类型。脚本退出码为 0 才表示技术链路通过；`evidence_accepted` 不能表述为已发布
或已履约。需要复核日志时执行 `./bin/1cat logs`，不得把 API Key 复制到命令或日志中。

## 5. Worker 崩溃恢复演练

先确保统一站点和正式 Worker 健康，然后执行：

```bash
cd /d/媒体架构/1Cat-Marketing-OS
.venv/Scripts/python.exe scripts/runtime_failure_drill.py --scenario all
```

脚本只使用合成任务，不调用 Hermes、DeepSeek、MCP 或内容平台。它会：

1. 记录正式 Worker 是否正在运行并临时停止它。
2. 创建只允许专用 Worker claim 的目标 Run。
3. 在外部派发前杀死 victim Worker，验证 Lease 过期后产生新 Attempt。
4. 在外部派发边界后杀死 victim Worker，验证 Run 进入 `unknown` 且不自动重试。
5. 使用旧 Attempt 的 Lease Token 探测写回，必须得到 `false`。
6. 删除专用演练容器并恢复正式 Worker。

成功输出中必须同时出现：

```text
safe-recovery: lost → succeeded / evidence_accepted
unknown-after-dispatch: unknown / unsafe
old_lease_write_accepted: false
```

最新机器可读证据位于 `.runtime/evidence/runtime-failure-drill-latest.json`。Attempt API
不会返回 `lease_token`；该 token 只允许 Worker 和数据库事务内部使用。

### 5.1 综合可靠性验收

完成 Worker kill 演练后，执行第 5、6 周综合验收：

```bash
.venv/Scripts/python.exe scripts/runtime_reliability_drill.py \
  --scenario all --run-count 20 --worker-count 4 --database-outage-seconds 6
```

该脚本会：

1. 使用私有输入前缀，让 4 个专用 Worker 只处理本轮 20 条合成 Run。
2. 验证每条 Run 只有 1 个有效 Attempt，并记录实际 Worker 分布和 p95 claim delay。
3. 在 claim 前短暂停止 PostgreSQL，验证 Worker 不退出且恢复后正常领取任务。
4. 在运行中 Heartbeat 阶段短暂停止 PostgreSQL，验证同一 Attempt 恢复后重新验租。
5. 使用本地假 Hermes 验证超时进入 `unknown/unsafe` 且不重试。
6. 验证运行中取消只有在 Hermes `/stop` 明确确认后才进入 `cancelled`。

脚本仅操作 `1cat-hermes-os` 项目的 PostgreSQL、正式 Worker 和固定名称的专用临时容器；
结束时恢复正式 Worker，不删除数据卷。通过证据见
`docs/evidence/Runtime可靠性综合验收_2026-08-27.md`。

浏览器打开 `http://127.0.0.1:8080/?view=runtime`，登录后使用“最近服务端 Run”选择器：

- `run_1198cb9dd00249bea033073c4fd4f38e` 应显示“安全恢复已完成”和两个 Attempt。
- `run_409c33f35dfc4679afc9bc0fb4eb97bd` 应显示“不确定副作用已隔离”和 `unknown/unsafe`。

## 6. 可观测性

```bash
./bin/1cat observe up
```

- Jaeger：<http://localhost:16686>，按 `1cat-runtime-api` / `1cat-runtime-worker` 或 Run ID 查找 Trace。
- Prometheus：<http://localhost:9090>，检查 `onecat_*` 指标。
- Grafana：<http://localhost:3000>，打开 `1Cat Runtime / 1Cat Agent Runtime Overview`。

浏览器进入 `http://127.0.0.1:8080/?view=runtime` 后，每条新 Run 都会显示 Trace ID 和
三个观测入口。完整的真实 PMA 联查可执行：

```bash
cd /d/媒体架构/1Cat-Marketing-OS
.venv/Scripts/python.exe scripts/observability_acceptance.py --role pma
```

脚本会检查：Run 终态与持久时间线、API/Worker 主 Trace、MCP `FOLLOWS_FROM` Span Link、
六类 Prometheus 指标、Grafana v3 看板（含 Worker 数据库不可用 Panel），以及 API/Worker/MCP 三类结构化日志。复查现有
Run 时使用 `--run-id <runtime-run-id>`，不会再次调用 DeepSeek。

2026-08-26 的通过证据见 `docs/evidence/Runtime可观测性真实联查_2026-08-26.md`。

完成实验后：

```bash
./bin/1cat observe down
```

## 7. 测试

Runtime 单测与 SQLite 集成测试：

```bash
./bin/1cat test
```

统一 Workspace / Demo1：

```bash
cd /d/媒体架构/1Cat-Marketing-OS/apps/workspace
npm run build
npm run e2e
```

PostgreSQL 并发 claim 用例仅在测试数据库为 PostgreSQL 时执行；SQLite 不支持 `SKIP LOCKED`，会显式跳过，不能把跳过视为并发验收通过。要从宿主机运行真实 PostgreSQL 套件，可在 Git Bash 执行：

```bash
docker compose --env-file .env \
  -f compose.yaml \
  -f infra/testing/postgres-loopback.override.yaml \
  up -d postgres

runtime_pg_password="$(sed -n 's/^POSTGRES_PASSWORD=//p' .env)"
DATABASE_URL="postgresql+psycopg://onecat:${runtime_pg_password}@127.0.0.1:55432/onecat" \
  .venv/Scripts/python.exe -m pytest
unset runtime_pg_password

# 验收后恢复正式的内部网络边界，不再向宿主机发布数据库端口。
docker compose --env-file .env up -d --force-recreate postgres
```

覆盖文件只把数据库发布到 `127.0.0.1:55432`，并附加测试 bridge；不会向局域网开放，也不会改变正式 Compose 拓扑。

## 8. 常见问题

| 现象 | 优先检查 |
|---|---|
| `docker info` 无法连接 pipe | Docker Desktop Engine 尚未就绪，或当前不是 Linux containers |
| 拉取镜像时 `auth.docker.io` 超时或解析到异常地址 | 优先检查代理/DNS；开发机也可按本手册设置项目级 `DOCKER_HUB_REGISTRY` 与 `HERMES_IMAGE_REGISTRY`，保留摘要后重跑 `up` |
| `profile-init` 报 `illegal option` 或 Tinyproxy 第 1 行语法错误 | 检查仓库 `.gitattributes` 是否生效；Linux 容器内执行的 shell/config 必须为 LF |
| Keycloak 一直 unhealthy | PostgreSQL 健康、`.runtime/keycloak/realm-1cat.json`、本机 8080 端口 |
| Run 一直 queued | `runtime-worker` 容器、数据库连接、Worker 日志 |
| Run 进入 unknown | 是安全边界；核对 Hermes Run ID 和 Trace，不要盲目重试 |
| Runtime 登录后立即返回登录页 | 401；检查 Keycloak、Caddy `/auth`/`/v1` 路由和 Token 过期 |
| Agent 配置显示本机配置服务不可用 | 检查 `/local-admin/model-config`、Caddy 内部令牌、Runtime API 和 Model Gateway |
| Grafana 无数据 | `.env` 中 OTLP endpoint、Collector 日志，以及是否在 `observe up` 后重建了 Runtime |

## 9. 停止

```bash
./bin/1cat down
```

`down` 不删除数据卷。如需备份，先执行 `./bin/1cat backup`。
