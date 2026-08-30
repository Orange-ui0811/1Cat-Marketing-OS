# 八类服务端工作台与 Agent Profile 收口（2026-08-30）

## 结论

本轮完成了“安全整合计划”的最后工程收口：正式 8080 前端默认以 Runtime 服务端为唯一业务
事实源；八类页面覆盖任务、协作、对象、决策、异常、Daily、Agent 配置和运行诊断。旧
Context/Reducer/localStorage 界面没有删除，但只在 `?mode=prototype` 作为隔离参考入口存在，
不再冒充正式任务、聊天或结果。

Agent 配置已从浏览器展示项升级为运行配置：MO、PMA、BGA 的模型参数、岗位六件套、Skill、
工具权限、Memory 策略和 workflow/chat Prompt 由服务端执行草稿、校验、发布和回滚。每条新
工作流 Run 或聊天 Run 固化已发布 Profile 的版本、SHA-256 hash 和完整快照；草稿不影响新
Run，运行中与历史 Run 不被后来发布覆盖，安全重试继承原快照。

## 八类页面当前能力

| 页面 | 当前服务端能力 |
|---|---|
| 任务中心 | 新建案例、查看九阶段、启动四类 Agent 阶段、处理 simulated 发布和反馈任务 |
| 协作中心 | MO/PMA/BGA 频道、持久消息、附件元数据、真实 chat Run/回复、Change Request、Handoff 和活动时间线 |
| 业务对象 | Brief、Plan、Fact、Claim、Campaign、Content、Review、Lead、Feedback、对象谱系、版本差异和 FINAL DELIVERABLE/Markdown |
| 决策台账 | 批准、退回、HOLD、接管、理由、对象 ID/版本和决策历史 |
| 异常处置 | failure/Attempt/Lease/Heartbeat 证据、安全重试、取消、Unknown 人工对账和恢复 |
| Daily Brief | 全部服务端案例的待审批、待启动、运行、异常、新对象和已完成结果聚合 |
| Agent 配置 | 三岗位 Profile 强校验、草稿/发布/回滚、DeepSeek 连通性与执行开关 |
| 运行诊断 | Case/Run 筛选、Attempt、状态时间线、Trace/Correlation、Profile version/hash/snapshot、Jaeger/Grafana 入口 |

历史功能分为案例、对象、决策和执行四层保存。三 Agent 之间不直接互调，而是通过同一 Case、
Commitment、Handoff、消息、版本化对象和具名人类门禁协作。

## 本轮重新执行的验证

| 检查 | 结果 |
|---|---|
| Python 全套 | 通过；2 个 PostgreSQL 专用用例按当前环境跳过 |
| 观测证据覆盖保护测试 | 2/2 通过 |
| Workspace production build | 通过 |
| Workspace Playwright | 10/10 通过 |
| 4173 开发镜像一致性 | 29 个文件一致 |
| 架构研修台 | 4 图、89 节点、173 关系、7 链路、92 证据，校验通过 |
| Week 8 离线聚合 | 10/11；唯一失败为当前真实 Case 观测机器证据不是 13/13 |
| Week 8 在线聚合 | 10/16；Docker Desktop Linux Engine 未运行，5 个在线入口未复验 |

## 本轮发现并修复的证据问题

`marketing_workflow_observability.py` 以前会让一次合成 Case 的 8/13 观测结果覆盖已有真实 Case
的 13/13 `latest` 文件。合成 Run 本来就没有 Hermes Run ID 和 MCP Span Link，因此不能满足
真实验收合同；覆盖后 `portfolio-check` 会正确失败。

现在改为：

- 始终写入 `marketing-workflow-observability-<mode>-latest.json`。
- 只有全部检查通过时才更新兼容文件 `marketing-workflow-observability-latest.json`。
- `week8_readiness.py` 优先读取真实模式专用证据。
- 新增测试证明失败验收不会覆盖最后一份已通过证据。

当前没有伪造或根据 Markdown 反向生成一份“通过”的 JSON。仓库内 2026-08-27 的真实 Case
13/13 报告仍是历史证据，但本轮未重新运行 DeepSeek、未重启观测栈，也未把它表述为本轮通过。

## 计划整体状态

| 阶段 | 状态 |
|---|---|
| 本机合成闭环、真实 DeepSeek、PMA 黄金链 | 已有历史验收 |
| Attempt/Lease/Heartbeat/Fencing/恢复 | 已实现并有故障与并发证据 |
| 三 Agent 九阶段完整 Demo 与最终方案 | 已实现并有合成/真实历史证据 |
| 八类页面全部服务端化与真实岗位聊天 | 已实现，本轮回归通过 |
| Agent Profile 真实运行绑定 | 已实现，本轮回归通过 |
| 四张知识图谱、演示稿、简历与复现材料 | 已更新并校验 |
| 当前机器真实 Case 观测重新签证 | 待 Docker/观测栈启动后执行 |
| 5～8 分钟本人录屏、第二环境复现签字 | 待本人完成 |

按工程功能计算，计划约完成 93%：核心代码、八类完整功能、确定性测试和材料已经收口；剩余
不是新增业务模块，而是一次真实 Case 观测重新签证、最终录屏和独立环境复现。若旧 Jaeger/
容器日志已随重建丢失，重新取得 13/13 需要显式执行一条新的真实 DeepSeek Case，会产生外部
请求和可能费用，不能由离线检查替代。
