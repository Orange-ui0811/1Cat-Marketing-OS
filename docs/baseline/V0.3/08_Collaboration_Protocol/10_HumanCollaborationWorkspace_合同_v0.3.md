# Human Collaboration Workspace 合同 v0.3

> `contract_id: IF-HUMAN-WORKSPACE-01` · 状态：`INTERFACE-FREEZE-CANDIDATE`  
> 定义：人类Owner与三个数字岗位进行委派、1:1、审批、人工执行、评价和接管的共同工作界面；不是流程控制中心或第二事实源。

## 1. 必须支持的工作区

| 工作区 | 主要参与者 | 必须支持 |
|---|---|---|
| 产品营销中心 | 产品营销负责人、PMA、R&D接口 | Inbox、1:1、证据/Claim候选审核、补证、修改差异、暂停接管 |
| 品牌营销中心 | 品牌营销负责人、BGA、MO | Campaign/内容共创、人工发布任务、LeadStub移交、提醒升级、评价接管 |
| 跨中心协作 | 两中心Owner、MO、PMA、BGA | CollaborationPlan、Commitment、依赖、Handoff、分歧和复盘议程 |
| 公司/治理 | 公司负责人、技术/风险Owner | 高影响批准、权限、阶段门、事故、冻结签署和审计 |
| 销售接口 | 销售负责人/授权角色 | LeadStub接收、`pending/valid/invalid/needs_more_info`明确反馈和原因码 |

## 2. 功能合同

必须包括：个人OIDC登录；岗位/中心目录；合法委派；岗位Inbox；Owner 1:1；WorkCommitment协商与状态投影；RoleHandoff接受/退回；ApprovalGrant签发/拒绝/撤销；ManualTask执行与回执；销售明确反馈；岗位评价；暂停/撤权/接管；人工连续性导出与恢复对账；作用域审计查询。

Workspace不得：代替MO规划协作；自动批准；用前端状态覆盖ORS；把Kanban设为可写事实源；向profile泄露PII/凭据；提供平台主账号；让人类共享身份；把“卡片变绿”当业务完成。

## 3. 身份、权限与数据

- 所有人类写操作使用统一命令信封：`human_actor_id, oidc_subject, acting_role, organization_unit, action, target_ref(type/id/version/hash), expected_revision, decision_or_reason, correlation_id, client_request_id, idempotency_key, approval_policy_ref(optional), takeover_ref(optional)`，并由ORS重新验权和检查乐观并发。
- ApprovalGrant使用单独合同；普通评论、点击或拖动卡片不能产生批准。
- 界面按最小必要呈现；R0不展示或传入真实PII，Lead只显示LeadStub和不透明SourceRef。
- Agent只通过Organization MCP读取授权内容；不得直接访问Workspace数据库、浏览器Session或OIDC令牌。
- 任何人工修改必须保留前后版本、修改人、原因和对受影响批准/承诺的影响。

## 4. Kanban与连续性

Kanban只能展示ORS-03 WorkCommitment的只读投影。最小投影包含`projection_id, source_type=WorkCommitment, commitment_id, source_revision, canonical_status, committed_role, active_profile_id(optional), due_at/review_at, waiting_reason/blocked_reason, latest_handoff_ref, source_updated_at, projected_at, projection_lag, stale`，幂等键为`commitment_id + source_revision`。

状态变化必须通过合法命令和WorkCommitment状态机写入ORS；禁止在Kanban接受承诺、审批、验收、拖动改状态、双向同步或离线覆盖事实源。投影延迟或故障不改变承诺状态，并能从ORS-03全量重建且显式显示`stale`。Runtime不可用时，Workspace导出不含PII的接管包；人工使用批准载体继续，恢复后通过ReconciliationPlan回填，不能覆盖人工期间结果。

## 5. UAT

覆盖两个中心隔离与跨中心协作、Owner 1:1、委派资格、批准身份/对象/hash、Handoff退回、人工发布回执、销售反馈、PII隐藏、岗位暂停、三岗位全停、Runtime中断、人工连续性、恢复对账、Kanban只读、共享身份拒绝和全链路审计。Workspace UAT未通过，任何岗位不得进入`active_limited`。
