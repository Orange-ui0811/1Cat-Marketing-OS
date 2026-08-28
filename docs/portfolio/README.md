# Agent Runtime 求职证据包

这组材料把 1Cat Hermes OS 已完成的工程事实整理成可演示、可复述、可复核的求职证据。
所有数字都来自本机验收记录；未完成的生产容量、高可用、Kubernetes、真实平台发布和
Shadow/UAT 不在结论内。

## 使用顺序

1. 先读 `Agent_Runtime_架构一页图.md`，用一页建立系统全貌。
2. 按 `5到8分钟演示脚本.md` 排练，并在录屏前执行 `./bin/1cat portfolio-check`。
3. 从 `简历项目描述与岗位映射.md` 选择与投递岗位匹配的 2～3 条描述。
4. 用 `面试讲解稿.md` 练习 90 秒介绍和追问。
5. 在另一台机器或全新 Windows 用户环境按 `独立环境复现清单.md` 留存复现记录。

## 当前证据状态

| 证据 | 状态 | 说明 |
|---|---|---|
| 架构一页图 | 已完成 | 范围、主链、状态机、不变量和边界齐全 |
| 5～8 分钟演示脚本 | 已完成 | 三 Agent 九阶段闭环、恢复、unknown、Trace/指标 |
| 简历项目描述 | 已完成 | 只引用已验收数字，并给出岗位映射 |
| 面试讲解稿 | 已完成 | 覆盖 Runtime、Lease/Fencing、unknown、可观测性 |
| 合成完整 Case | 已完成 | 九阶段、4 Run、人工门禁与模拟发布确定性通过 |
| 真实完整 Case | 已完成 | DeepSeek 四角色阶段完成；保留一次安全重试历史 |
| Case 跨系统联查 | 已完成 | API/DB/Trace/MCP Link/Log/Metrics/Grafana 13/13 |
| 本机收口自动检查 | 已完成 | `./bin/1cat portfolio-check` 聚合全部机器证据 |
| 最终录屏 | 待本人完成 | 录屏需要本人讲解，建议 5～8 分钟 |
| 独立新环境复现 | 待本人完成 | 当前机器通过不等于第二环境已复现 |

## 自动检查

项目启动后，在 Git Bash 中运行：

```bash
./bin/1cat portfolio-check
```

检查会验证求职材料、合成/真实完整 Case、跨系统联查、两份故障演练机器证据、
Runtime/UI、Jaeger、Prometheus 和 Grafana，
并把结果写入 `.runtime/evidence/week8-readiness-latest.json`。它不会调用 DeepSeek、停止容器、
修改业务数据或读取/输出 API Key。
