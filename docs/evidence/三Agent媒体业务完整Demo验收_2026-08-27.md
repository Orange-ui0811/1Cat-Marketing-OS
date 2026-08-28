# 三 Agent 媒体业务完整 Demo 验收（2026-08-27）

## 结论

第五步最终验收已完成。统一前端、服务端 Case 状态机、三 Agent 真实 DeepSeek 执行、人类门禁、
模拟发布、合成反馈、故障边界和本机可观测性已形成一条可复现证据链。

这证明的是本机技术闭环，不代表真实平台发布、真实营销效果、生产高可用或通用 DAG。

## 完整流程结果

真实案例：`case_26571297a8f9438e891d18fe77771f86`

| 项目 | 实测结果 |
|---|---|
| Case 终态 | `completed`，版本 17 |
| 阶段 | 9/9 完成 |
| Agent 阶段 | MO 规划、PMA、BGA、MO 复盘全部覆盖 |
| Run 历史 | 5 条，全部 `evidence_accepted`；包含 1 次安全重试 |
| Commitment | 4 条，全部经人类门禁成为 `fulfilled` |
| Handoff / Approval | 2 / 6 |
| Knowledge | brief×1、review×2、fact×1、claim×1、campaign×1、content×1 |
| 发布 | `simulated`，`external_effect=false` |
| 反馈 | 无 PII Lead×1、SalesFeedback×1 |

合成案例 `case_d4c5ef4f31a04daeba7e3d5219a624f9` 以 4 条合成 Run 确定性完成相同九阶段闭环。

## 本次发现并修复的问题

第一次真实 MO 复盘已完成模型运行，但未能持久化 review，Case 正确进入
`blocked/missing_required_artifacts`。根因是随机 `attempt_...` 标识符中偶然出现连续 11 位数字，
被公共 PII 策略误判为手机号，Runtime 返回 422。

修复内容：

- 手机号规则排除 ASCII 业务标识符内部的数字片段，同时继续拒绝正文中的真实手机号。
- 增加回归测试，覆盖含 11 位数字片段的 `attempt_id`。
- MCP 把经过截断的 Runtime 校验详情返回给 Agent，便于一次修正后停止。
- MO 提示词要求先确认 CandidateKind、尽早持久化 review，并减少重复读取。
- 演示脚本支持显式 `--allow-safe-retry`，旧 Run/Attempt 永不覆盖。
- Smoke 创建 Run 时显式固定 `execution_mode=synthetic`；即使网页已开启真实 DeepSeek，
  12 步基线仍不调用模型。该问题在最终 Smoke 中被发现并修复，复跑通过。

第一次 Smoke 已创建的真实 PMA Run `run_443b3314141440668036b37ef47c292c` 在专用 Worker
停止后由恢复扫描器标记为 `unknown/unsafe`，并保存 Hermes Run ID；系统没有自动重试或
伪造成成功。随后固定 synthetic 的 Smoke 12/12 通过。

修复后由人类授权安全重试，新 MO Run 创建 review，最终 Case 完成。

## 跨系统联查

`scripts/marketing_workflow_observability.py` 对同一 Case 完成 13/13 检查：

- 前端/API Case 与九阶段事实一致。
- PostgreSQL：Case×1、Step×9、Run×5、Case Resource×27。
- 5 条 Run 均存在 Attempt、Hermes Run ID、终态 Timeline。
- 5 条主 Trace 均包含 Runtime API 与 Worker，并存在 MCP `FOLLOWS_FROM` Span Link。
- Case 范围结构化日志包含 Runtime API、Worker、Organization MCP。
- Prometheus 存在 Case 创建/完成、阶段耗时、活动 Case、Run 终态和 MCP 调用指标。
- Grafana Dashboard 为 v4，共 20 面板，其中 9 个属于 Marketing Workflow。
- 安全边界保持 `publishing=simulated`、`external_effect=false`、`pii=false`、
  `business_outcome_claimed=false`。

机器证据：

- `.runtime/evidence/marketing-workflow-demo-synthetic-latest.json`
- `.runtime/evidence/marketing-workflow-demo-real-latest.json`
- `.runtime/evidence/marketing-workflow-observability-latest.json`
- `.runtime/evidence/week8-readiness-latest.json`

## 最终回归

| 检查 | 结果 |
|---|---|
| Python | 52 passed，2 PostgreSQL-only skipped |
| Workspace build | TypeScript + Vite production build passed |
| Workspace Playwright | 7/7 passed |
| 4173 镜像 | 26 个源文件一致，独立 production build passed |
| Alembic | PostgreSQL `0004 (head)` |
| 12 步 Smoke | passed；固定 synthetic，未执行真实发布 |
| 架构研修台 | 4 图、87 节点、164 关系、7 链路、84 证据，校验通过 |
| Week 8 readiness | 16/16 passed |

## 复现命令

```bash
.venv/Scripts/python.exe scripts/marketing_workflow_demo.py --mode synthetic
.venv/Scripts/python.exe scripts/marketing_workflow_demo.py --mode real
.venv/Scripts/python.exe scripts/marketing_workflow_observability.py --case-id <case_id> --log-since 3h
./bin/1cat portfolio-check
```

真实模式会调用 DeepSeek 并可能产生费用；确定性 CI 继续使用合成模式。
