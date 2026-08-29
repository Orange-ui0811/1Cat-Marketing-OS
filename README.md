# 1Cat Hermes OS

一猫营销实验性 AI 原生组织运行系统 R0。系统由三个长期数字岗位组成：

- PMA：产品营销 Agent
- BGA：品牌与增长 Agent
- MO：营销协同 Agent

R0 只生成候选、协作、审核和人工发布任务。抖音、小红书、B站、公众号均为人工发布；视频号保持休眠；真实 PII、自动发布、A2A、关键 Cron 和生产高可用不在范围内。

## 快速开始

```bash
./bin/1cat doctor
./bin/1cat init
./bin/1cat up
./bin/1cat smoke
./bin/1cat e2e
```

打开 <http://localhost:8080>。这里直接交付由服务端驱动的八类工作台；三 Agent 完整流程
分布在任务、协作、对象、决策、异常、Daily、Agent 配置和运行诊断八个页面中。PMA Runtime 研修页位于
<http://localhost:8080/?view=runtime>。首次登录用户为 `admin`，密码在
初始化后写入 `.env` 的 `INITIAL_ADMIN_PASSWORD`；不要复制到文档、日志或部署包。

在“Agent 配置 → 模型与权限”中，可以从本机页面保存、验证 DeepSeek Key 并切换真实
执行。Key 只写入 `.runtime/secrets`，Caddy 使用内部令牌把 `/local-admin` 转发给 Runtime
API；浏览器不保存或回显 Key。命令行 `auth deepseek` 继续作为备用入口。

需要运行真实 Hermes Agent 时：

```bash
./bin/1cat auth deepseek
./bin/1cat restart-agents
```

命令使用隐藏输入把 DeepSeek API Key 写入 `.runtime/secrets/model_api_key`，
随后通过 Model Gateway 验证上游模型列表。Provider Key 不进入 `.env`、Profile、
Hermes 容器、镜像或日志；验真失败时 `HERMES_EXECUTION_ENABLED` 保持 `false`。
项目仍保留 `auth codex` 作为显式备选，但不会静默切换 Provider。

模型连通后，可用固定的合成业务边界分别验收三个真实 Agent。脚本会校验 Runtime、
Hermes、Commitment 终态以及实际写入的候选对象类型：

```bash
.venv/Scripts/python.exe scripts/real_agent_demo.py --role pma
.venv/Scripts/python.exe scripts/real_agent_demo.py --role bga
.venv/Scripts/python.exe scripts/real_agent_demo.py --role mo
```

通过标准为 Runtime=`evidence_accepted`、Hermes=`completed`、Commitment=`submitted`、
候选类型落在岗位白名单内且仍需人工确认。真实 Run 不代表发布或业务履约。

## 三 Agent 完整业务 Demo

完整流程以服务端 Marketing Case 为事实源，包含九个阶段和四次角色执行：

```text
Brief → MO 规划 → 人工确认 → PMA Fact/Claim → 人工产品审核
→ BGA Campaign/Content → 人工内容审核 → simulated 发布
→ 合成 Lead/销售反馈 → MO 复盘 → 生成完整营销方案 → 人工确认完成
```

默认合成模式不调用模型，可确定性复现；真实模式会调用 DeepSeek 并产生费用，必须显式选择：

```bash
.venv/Scripts/python.exe scripts/marketing_workflow_demo.py --mode synthetic
.venv/Scripts/python.exe scripts/marketing_workflow_demo.py --mode real
```

验收会保存 Case、阶段、Run、Attempt、Trace、候选、审批、Handoff、模拟回执、反馈和最终方案证据。
最终方案是独立、版本化的 `MarketingDeliverable`，包含 10 个结构化章节、证据索引与可下载
Markdown；最后一次人工确认会批准该方案的明确版本。Agent 只返回占位短文、缺少必需对象或
方案章节不完整时，Case 会进入 `blocked`，不会被标记为完成。
若安全失败停在 `retry_safe_step`，由人类确认后可增加 `--case-id <id> --allow-safe-retry`
继续；旧 Run/Attempt 不会被覆盖。发布回执固定声明 `external_effect=false`，系统不访问真实平台。

### 八类页面如何分工

- **任务中心**：新建 Brief、启动 MO/PMA/BGA、完成模拟人工发布、登记合成反馈。
- **协作中心**：围绕当前 Case 留言，查看 Commitment 与 Handoff 的服务端记录。
- **业务对象**：查看 Fact、Claim、Campaign、完整内容母稿和 10 章 FINAL DELIVERABLE；切换历史案例并下载 Markdown。
- **决策台账**：审阅对象版本，批准、退回修改、HOLD 或人工接管，并保留正式理由。
- **异常处置**：查看失败事实，执行安全重试、暂停恢复、Unknown 人工对账或取消。
- **Daily Brief**：按待人工、运行中、异常、已完成聚合全部服务端案例。
- **Agent 配置**：维护 PMA/BGA/MO 的服务端 Profile 草稿，校验、发布和回滚版本。
- **运行诊断**：按 Case 查看 Run、Attempt、Lease、Heartbeat、状态时间线与 Trace。

`/?view=workflow` 只保留为兼容入口，并会进入同一套八类服务端工作台；它不再是完成流程所必需的页面。

Windows 请使用 Docker Desktop Linux containers + Git Bash；完整步骤见 `docs/deployment/Windows开发运行手册.md`。

## 求职演示与第 8 周收口

可直接使用的架构一页图、5～8 分钟演示脚本、简历表述、面试讲解稿和独立环境复现清单
位于 `docs/portfolio/`。项目启动后可执行只读收口检查：

```bash
./bin/1cat portfolio-check
```

检查会核对材料、完整工作流、故障演练机器证据及 Runtime/Jaeger/Prometheus/Grafana 健康状态，并写入
`.runtime/evidence/week8-readiness-latest.json`。它不会调用真实模型、读取或输出 Secret，
也不会修改业务数据。最终录屏和第二环境复现仍必须由本人完成并签字，不能用本机检查代替。

当本机无法直连 Docker Hub 时，可只在不入库的 `.env` 中设置
`DOCKER_HUB_REGISTRY`；Hermes 大镜像还可单独设置
`HERMES_IMAGE_REGISTRY`。默认值仍是 `docker.io`，所有上游镜像继续由
Compose/Dockerfile 中固定的 SHA-256 摘要校验，切换镜像代理不会放宽版本约束。

## 可恢复 Agent Runtime

Run 保持原有状态名，并增加了不可覆盖的 Attempt 历史、Lease/Heartbeat、fencing token、取消请求与安全恢复：

```text
queued → accepted → running → evidence_accepted | failed | cancelled | unknown
```

- 默认 Lease 30 秒，Heartbeat 10 秒，最多 2 次 Attempt。
- 尚未记录外部启动意图时租约过期，Run 可安全重新入队。
- 一旦记录外部启动意图，即使 Hermes Run ID 尚未来得及回写，结果不明也进入 `unknown`，禁止自动重试。
- 所有写回必须匹配 `current_attempt_id + lease_token`。
- `evidence_accepted` 只表示候选证据已接收，不代表 Commitment 已经 `fulfilled`。

可执行的容器故障演练会临时停止正式 Worker，分别杀死“外部派发前”和“外部派发
边界后”的专用 Worker，并在结束时恢复正式 Worker。演练只使用合成执行，不调用模型：

```bash
.venv/Scripts/python.exe scripts/runtime_failure_drill.py --scenario all
```

通过标准：安全场景产生 `lost → succeeded` 两个不可覆盖 Attempt；不安全场景只产生
一个 `unknown/unsafe` Attempt；两种场景下旧 Lease 写回都必须被拒绝。运行证据写入
`.runtime/evidence/runtime-failure-drill-latest.json`。

第 5、6 周的综合可靠性验收还会启动 4 个 Worker 处理 20 条私有合成 Run，短暂停止并
恢复本项目 PostgreSQL，并使用本地假 Hermes 验证超时和取消确认；不会调用真实模型：

```bash
.venv/Scripts/python.exe scripts/runtime_reliability_drill.py \
  --scenario all --run-count 20 --worker-count 4 --database-outage-seconds 6
```

2026-08-27 实测 5 / 5 场景通过：20 条 Run 重复有效执行为 0；断库前和 Heartbeat 中断
均安全恢复；Hermes 超时保持 `unknown/unsafe` 且不重试；运行中取消只在 Hermes 明确
确认后成为 `cancelled`。证据见 `docs/evidence/Runtime可靠性综合验收_2026-08-27.md`。

登录 `http://127.0.0.1:8080/?view=runtime` 后，可在“最近服务端 Run”中直接切换上述
两条演练记录：安全场景显示 `lost` 与 `succeeded` 两个 Attempt，不安全场景显示
“不确定副作用已隔离”和 `lease_expired_after_external_dispatch / unsafe`。

正式前端源码位于 `apps/workspace`，已经与 Demo1 的八类工作台视图、Agent 配置和 PMA
Runtime 页面统一。`D:\媒体架构\demo1\demo1` 只保留为 4173 开发镜像，不再是部署入口。

## 可观测性

```bash
./bin/1cat observe up
```

启动后可打开：

- Jaeger：<http://localhost:16686>
- Prometheus：<http://localhost:9090>
- Grafana：<http://localhost:3000>（默认 `admin / onecat-observe`，可在 `.env` 修改）

八类工作台的“运行诊断”可查看每个 Agent 阶段的 Run/Attempt/Trace，
`/?view=runtime` 继续保留 PMA 研修页。Grafana v4 共 20 个面板，含 Marketing Workflow、
队列/租约/恢复、MCP 和数据库不可用区域。可以创建一条新的真实 PMA Run并自动核对 Trace、
指标、结构化日志与时间线：

```bash
.venv/Scripts/python.exe scripts/observability_acceptance.py --role pma
```

传入 `--run-id <id>` 可复查已有 Run，不会再次调用模型。真实联查记录见
`docs/evidence/Runtime可观测性真实联查_2026-08-26.md`。

完整 Case 的跨系统联查：

```bash
.venv/Scripts/python.exe scripts/marketing_workflow_observability.py --case-id <case_id> --log-since 3h
```

停止并让 Runtime 切回无 OTLP 导出模式：

```bash
./bin/1cat observe down
```

## 常用命令

```bash
./bin/1cat status
./bin/1cat logs
./bin/1cat test
./bin/1cat observe up
./bin/1cat backup
./bin/1cat restore <backup-directory> --confirm
./bin/1cat package arm64
./bin/1cat package amd64
```

详细说明见 `docs/deployment/部署与运维手册.md`。

业务人员请按 `docs/一猫营销_R0业务使用说明_v1.0.md` 完成 Brief → PMA → BGA → 人工发布 → LeadStub → 销售反馈 → MO复盘闭环。
