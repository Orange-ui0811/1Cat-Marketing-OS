# DROLE-03 MO Tool Allowlist v0.3

> 状态：`ALLOWLIST-FREEZE-CANDIDATE` · MO只拥有协作能力，不拥有专业对象或业务动作权限。

| 能力族 | 允许动作 | 数据范围 | 对应Skill | 必须拒绝 |
|---|---|---|---|---|
| `org.event.get/ack` | 读/确认EVT-01～11组织事件 | 元数据和最小摘要 | OR-01/04 | 专业原件/PII正文 |
| `role.directory.read` | 读岗位/人类角色、生命周期、升级关系 | 角色级，不含个人敏感信息 | OR-01/02 | 修改Owner/权限 |
| `object.get_version` / `approval.status` | 读状态、版本、是否批准 | OBJ-01～09摘要 | OR-01/04 | 修改对象/批准 |
| `collaboration.plan_submit` | 创建协作计划候选 | 目标/责任/依赖 | OR-02 | 中央Workflow强制执行 |
| `commitment.propose/get_context/track` | 提议/读取/跟踪承诺 | 当前关联 | OR-03～05 | 代签、覆盖拒绝、专业改写 |
| `org.inbox.read/ack` | 读本岗位Inbox和交接响应 | 最小业务元数据 | OR-03 | 读取其他岗位完整Session |
| `reminder.prepare` / `escalation.submit` | 生成提醒/升级 | 责任、影响、复核点 | OR-04 | 任意外联/群发消息 |
| `manual_task.prepare` | 准备人工接管任务 | 当前承诺与版本 | OR-05 | 执行业务动作 |
| `org.event.reconcile_candidate` | 提出恢复对账结果 | 持久状态摘要 | OR-05 | 覆盖人工状态 |
| `review.create_packet` / `audit.get_scoped_trace` | 协作复盘与关联审计 | 最小摘要 | OR-05/06 | 专业归因/任意日志 |

默认拒绝ProductFact/Claim/Campaign/Content/Lead/SalesFeedback专业写入，批准、平台发布、预算、外联、询盘判断、PII、浏览、HTTP、SQL、终端和任意文件能力。通知工具只能准备或走批准的组织通知通道，不能借此联系客户或公开发布。
