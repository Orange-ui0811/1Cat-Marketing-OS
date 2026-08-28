# Agent Runtime 8 周实战进度

更新日期：2026-08-27

## 总体状态

第 1～7 周的本机开发和验收目标已经完成。Docker Desktop Linux Engine 28.3.3、
合成 Smoke、PMA 前端黄金链路、PMA/BGA/MO 三岗位真实 DeepSeek Run、Attempt/Lease/
Heartbeat/Fencing、Worker kill 恢复、PostgreSQL 短暂中断、4 Worker 并发、Hermes 超时/
取消以及 OTel/Jaeger/Prometheus/Grafana 联查均已有实际证据。第 8 周已完成 README、
Windows 手册、ADR、故障报告、架构一页图、演示脚本、简历项目描述、面试讲解稿、独立
环境复现清单和知识图谱同步，并完成三 Agent 九阶段合成/真实闭环及 Case 跨系统联查。
尚缺本人完成的 5～8 分钟最终录屏，以及在第二台机器或全新环境中填写独立复现记录。
因此工程第五步已完成，但不能按生产高可用、生产容量、Shadow/UAT 或业务履约宣传。

| 周次 | 代码/资料状态 | 已有证据 | 还需亲自完成的验收 |
|---|---|---|---|
| 1 本机基线 | 已完成 | Engine、`doctor`、`init`、完整 `up/status/smoke/e2e`；三个 Hermes Gateway healthy | 保留本次 Windows 网络与 LF 故障记录，后续新环境复验 |
| 2 真实 Agent | 已完成 | DeepSeek Model Gateway；PMA/BGA/MO 三岗位真实 Run；候选类型、人工确认边界与错误日志复核 | 后续更换模型或 Profile 时重复执行固定验收脚本 |
| 3 Demo1 黄金链路 | 已完成并扩展 | TypeScript/Vite build；Playwright 7/7；PMA 研修页与三 Agent Workflow 登录、阶段推进、刷新恢复、历史切换和 401 通过 | 第二环境继续复验 |
| 4 状态模型 | 已完成 | Alembic 升级到 `0004 head`；Run/Attempt 与 Case/Step/Resource 状态机、非法命令、版本和幂等测试通过 | 对未来独立新环境继续执行备份与迁移复验 |
| 5 Lease/取消 | 已完成 | 4 Worker × 20 Run 容器验收无重复有效执行；旧 Lease 写回拒绝；运行中取消等待假 Hermes 明确确认 | 生产规模和真实 Provider 极端竞态仍不在本轮结论内 |
| 6 恢复 | 已完成 | 派发前 kill 可恢复；派发后 kill 为 `unknown`；claim 前/Heartbeat 中 PostgreSQL 断 6 秒均恢复；Hermes 超时 `unknown/unsafe` 且不重试 | 长时间分区、主从切换和高可用不在本轮范围 |
| 7 可观测性 | 已完成本机验收 | 单 Run 9/9 与完整 Case 13/13 联查；Grafana v4/20 Panel | 生产集中日志、采样、保留、告警和 SLO 不在本轮范围 |
| 8 收口 | 工程完成 | 九阶段合成/真实 Case、跨系统联查、README、证据报告、架构一页图、演示脚本、简历描述、面试讲解、复现清单和 `portfolio-check` 已完成 | 本人录制 5–8 分钟视频；在第二机器/全新环境填写复现记录并签字 |

## 当前自动化证据

```text
Current local Python suite: 52 passed, 2 PostgreSQL-only skipped
Workspace: TypeScript + Vite build passed; Playwright 7/7 passed
Demo1 mirror: deterministic sync and consistency check passed
Alembic: 0001 → 0002 → 0003 → 0004 (head) passed
Docker Compose: base and observability profiles parse successfully
Docker runtime: Engine/doctor/init/up/status/smoke/e2e passed
Core health: PostgreSQL/MinIO/Keycloak/Runtime API/Model Gateway/Hermes PMA+BGA+MO healthy
Real DeepSeek PMA/BGA/MO: Runtime evidence_accepted / Hermes completed / Commitment submitted
Worker kill drill: safe recovery + unknown boundary + stale fencing rejection passed
Reliability drill: 4 Workers / 20 Runs + two DB outages + timeout + cancellation, 5/5 passed
Marketing Workflow: synthetic 9 stages / 4 Runs; real 9 stages / 5 preserved Runs with 1 safe retry
Workflow observability: API/DB/Jaeger/MCP Link/Logs/Prometheus/Grafana, 13/13 passed
Grafana: v4 / 20 panels, including 9 Marketing Workflow panels
Week 8 readiness: 16/16 passed (artifacts + workflows + drills + online endpoints)
```

除明确标注的三岗位真实 Run 外，这些数字代表本机合成测试；不代表真实 Shadow/UAT、
平台发布、生产容量或高可用。

## 2026-08-19 合成 Run 证据

| Run | Attempt | correlation ID | 状态序列 |
|---|---|---|---|
| `run_6a0d3570b3274a75a1318e07d5d9546a` | `attempt_949cef094e284ce493211d101f3f02a2` | `smoke-05107dcf80c24ee98b82f83562d3e290` | `queued → accepted → running → evidence_accepted` |
| `run_177c53199cb84c7aaa167f9790d97ca6` | `attempt_d01220b8b2e44f36a995d9e2e1ec3d40` | `smoke-1c180f548f94428c874978a8d7db8e1e` | `queued → accepted → running → evidence_accepted` |
| `run_8f5feeb706f34695bc9e147d6b8740f3` | `attempt_d4458e3eea0f48a0ae91735f30fcc467` | `smoke-89027bc4d6b7487386a15c9ae554ea3c` | `queued → accepted → running → evidence_accepted` |
| `run_bcda0c70cbf649068f3e361cfa7891e8` | `attempt_325e7a3c93bb42aabf88ba4850bdb2d8` | `demo1-cfb34eef-fc16-4370-83a1-8d2cdbb43530` | `queued → accepted → running → evidence_accepted → 人工 fulfilled` |

前三次 Smoke Attempt 与 Demo1 Attempt 均由同一实际 Worker 容器领取并写为
`succeeded`。这证明合成
执行、状态持久化与迁移时间线已贯通；不证明模型授权、Hermes 工具调用或业务履约。

Demo1 验收时发现刷新后页面遗失当前 Run 游标。现已只在 `sessionStorage` 保存
当前 Run ID（不复制业务事实），刷新后重新向 Runtime API 读取 Run、Attempt、
Timeline 与 Commitment。真实页面整页刷新后仍恢复同一 Run 和人工 `fulfilled`，
对应 Playwright 回归用例也已通过。

## 2026-08-19 DeepSeek 真实 PMA 证据

| 结果 | Runtime Run | Attempt | Hermes Run | correlation ID | 终态 |
|---|---|---|---|---|---|
| 首次失败，保留诊断证据 | `run_529adac6140b4902882b9df335bd5ac5` | `attempt_054268959406405393a9a7e1236e4c42` | `run_028b91f9e60848938b5cf357ffe1daeb` | `real-pma-9871997c68614eb3804ae95e52f1135b` | Runtime `failed` / Hermes `failed` |
| 修复后成功 | `run_6fda46e0d7f94f9895c7b75dbce59cbd` | `attempt_1729aee0b42142a6b2fb626863be320e` | `run_6d38a4fdf472491782c61270d7e53803` | `real-pma-d693a8427c4b4cbfac7e1c43e675eb83` | Runtime `evidence_accepted` / Hermes `completed` / Commitment `submitted` |

首次 Run 失败的根因是 Hermes 的 `NO_PROXY` 未包含内部 `model-gateway`，请求错误地
进入出口代理并被重置。将网关加入内部直连白名单并重建 Agent 后，Model Gateway
记录多次真实 `POST /v1/chat/completions 200`，第二次 Run 完成。该 Run 没有自动进入
`fulfilled`，仍保留人类最终确认边界。

该次历史 Run 曾发现 PMA 使用不支持的候选类型并重复尝试。此问题已在 2026-08-21
通过精确候选枚举、岗位二次校验、失败最多重试一次和固定真实验收脚本修复；修正后的
三岗位日志均未再次命中候选类型、工具搜索或 Commitment 动作错误。

## 2026-08-21 DeepSeek 三岗位真实验收

| 岗位 | Runtime Run | Attempt | Hermes Run | 终态 | 候选对象 |
|---|---|---|---|---|---|
| PMA | `run_a95526179a7a438884c94e926025de12` | `attempt_256da4dd880c4a0ebf7693aefbc46de9` | `run_d1f80b05d0084bc9a3b99703079baba7` | `evidence_accepted / completed / submitted` | `fact × 1`、`claim × 3` |
| BGA | `run_0c8521747c0c473fb76736f8b0de7034` | `attempt_9652b2e4864a4c1994d0f9aa5287623f` | `run_cdf5ad85111142a686140ccab27e336a` | `evidence_accepted / completed / submitted` | `campaign × 1`、`content × 1` |
| MO | `run_236fe01ef6034555a9abf393d0511f99` | `attempt_95b51eebed8847dc98d91306390f4911` | `run_342d937b8d1349098fc6c3db2623aa4a` | `evidence_accepted / completed / submitted` | `review × 1` |

完整 correlation ID、耗时、修正项和复验命令见
`docs/evidence/第2周_DeepSeek三岗位真实验收_2026-08-21.md`。

本次首次启动同时修复了两个 Windows 可复现问题：

- Docker Hub DNS/认证不可达时，项目可通过独立 registry 前缀切换代理，摘要固定不变。
- 容器内 shell 与 Tinyproxy 配置强制 LF，避免 `profile-init` 和出口代理因 CRLF 失败。

## 第 8 周收口产物

- `docs/portfolio/Agent_Runtime_架构一页图.md`
- `docs/portfolio/5到8分钟演示脚本.md`
- `docs/portfolio/简历项目描述与岗位映射.md`
- `docs/portfolio/面试讲解稿.md`
- `docs/portfolio/独立环境复现清单.md`
- `scripts/week8_readiness.py` 与 `./bin/1cat portfolio-check`

2026-08-27 本机 `portfolio-check` 已扩展为核对六份材料、合成/真实完整 Case、Case 跨系统
联查、两份故障演练机器证据及 Workspace、Runtime、Jaeger、Prometheus、Grafana。机器结果写入
`.runtime/evidence/week8-readiness-latest.json`；检查明确记录没有读取 Secret、没有修改
Runtime 业务数据。

完整 Case 实测：`case_26571297a8f9438e891d18fe77771f86` 完成 9 阶段，保留 5 条
`evidence_accepted` Run（含 1 次安全重试）、4 条人工确认 Commitment、2 Handoff、6 Approval、
simulated 回执和合成反馈。详见 `docs/evidence/三Agent媒体业务完整Demo验收_2026-08-27.md`。

## 下一个可执行学习单元：本人录屏与第二环境复现

### 学什么

- 如何用一条可重复演示链说明系统设计、故障边界和技术取舍。
- 如何把“做过”转化为有 Run ID、Trace 和实测数字支撑的求职证据。
- 如何清楚披露本机验收与生产高可用之间的边界。

### 做什么

1. 按现成脚本本人录制 5～8 分钟演示：三 Agent 完整 Case → Worker 恢复 → `unknown` → Trace/指标。
2. 在另一台机器、虚拟机或从未运行本项目的全新 Windows 用户环境执行复现清单。
3. 填写环境、失败、修复和最终签字；不要复制当前 `.env`、`.runtime` 或 Docker volume。
4. 录屏和第二环境记录完成后，才把第 8 周正式标记为完成。

### 你应该能讲清的问题

1. 这个项目为什么算 Agent Runtime，而不只是调用了一次大模型 API？
2. PostgreSQL 中断时为什么不能把数据库错误写成 Agent `failed/unknown`？
3. 4 Worker × 20 Run 的结果证明了什么，又没有证明什么？
4. 为什么 Hermes 超时必须保留 `unknown/unsafe`，而不是盲目重试？
5. `evidence_accepted`、`submitted` 与人类 `fulfilled` 的责任边界是什么？
