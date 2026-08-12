# ToolCapabilityPolicy 合同 v0.3

> `contract_id: IF-TOOL-CAP-POLICY-01` · 状态：`INTERFACE-FREEZE-CANDIDATE`  
> 目标：按岗位、Commitment、对象、动作、数据和时间窗实行最小权限；不是自然语言提醒。

## 1. 策略字段

| 字段 | 要求 |
|---|---|
| `policy_id/version/status` | draft/approved/superseded；本版draft |
| `role_id, role_version_range` | 精确岗位和兼容Manifest |
| `profile_id, profile_bundle_range, service_identity_id` | 精确profile、可用Bundle和独立服务身份；不得只凭role授权 |
| `commitment_scope` | accepted commitment、purpose/CAP、请求者资格 |
| `subject_scope` | 对象类型、ID/版本/hash、数据敏感度 |
| `capability/action` | 明确能力族和read/create_candidate/submit/record等动作 |
| `conditions` | 生命周期、ApprovalGrant、SourceRef、时间/频率/额度窗口 |
| `effect` | `allow/deny/require_human`；默认deny |
| `idempotency_rule` | 业务幂等键、并发/重复处理 |
| `external_iam_requirement` | 独立服务身份、最小外部权限；Profile不作安全边界 |
| `verification` | 输入校验、执行后验证、unknown处理 |
| `retry/compensation/takeover` | safe/unsafe/conditional与人工路径 |
| `audit/redaction` | 关联ID、策略结果和脱敏错误 |
| `owner/expiry/review` | 业务/技术Owner、撤销和版本门 |

## 2. 决策顺序

拒绝硬门（PII、凭据、禁止动作、岗位暂停、版本失效）→校验role+profile+service identity→校验accepted Commitment和authority snapshot→校验对象/动作/时窗→检查ApprovalGrant和幂等→执行最小能力→核对业务结果→返回统一Tool响应。任何条件不满足均`not_executed`；紧急和上级口吻不影响策略。

## 3. Tool请求与响应信封

每次Tool请求必须携带：`request_id, tool_call_id, correlation_id, role_id, profile_id, service_identity_id, commitment_id/version, attempt_id, context_snapshot_id, authority_snapshot_id, object_refs(id/type/version/hash), capability, action, approval_grant_id(optional), idempotency_key`。任何role/profile/service identity/Commitment/Attempt/Context/对象不匹配均不得执行，不能退化为仅按role放行。

响应遵循`07_Tool_Permission/00_Tool数据与权限总表_v0.3.md`：必须含role/profile/service identity、policy结果、关联ID、对象版本、ApprovalGrant、幂等键、attempt、`retryable + retryability`、human task、audit ref和脱敏消息。外部结果unknown时停止自动重试，`retryable=false, retryability=unsafe`并创建人工对账；不能用第二个幂等键绕过。

## 4. 变更与验收

新增外部写、PII、平台、预算、客户触达或询盘相关能力为Major，回到岗位/治理评审和独立Canary。测试所有allow与deny、跨岗位冒用、过期权限、对象漂移、重复/并发、注入、错误脱敏、Tool超时、unknown和撤权即时生效。
