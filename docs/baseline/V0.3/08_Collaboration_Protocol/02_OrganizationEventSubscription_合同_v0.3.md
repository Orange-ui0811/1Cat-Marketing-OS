# OrganizationEventSubscription 合同 v0.3

> `contract_id: IF-EVENT-SUB-01` · 状态：`INTERFACE-FREEZE-CANDIDATE`  
> Runtime负责可靠投递/持久化；岗位解释业务相关性和后续动作。

## 1. OrganizationEvent字段

`event_id, event_type(EVT-01～11或治理事件), occurred_at, producer_role/system, subject_ref, subject_version/hash, source_ref, business_owner_role, change_summary, correlation_id, causation_id, sensitivity_label, pii_flag=false, schema_version, replay_marker`。

事件只带最小元数据/授权摘要；不嵌入业务原件、明文PII、凭据、Prompt或大段Tool错误。`pii_flag=true`直接拒绝进入岗位Inbox并产生数据风险事件。

## 2. Subscription字段

| 字段 | 语义 |
|---|---|
| `subscription_id/version, role_id, event_types[]` | 稳定订阅身份、精确岗位和事件 |
| `business_reason_refs[]` | 对应职责/CAP/Skill；无理由不可订阅 |
| `subject_scope, minimum_payload` | 对象类型/范围与最少字段 |
| `filter_policy_ref, context_builder_ref` | 过滤、脱敏和ContextSnapshot规则 |
| `dedupe_key_rule` | 默认`role+subscription+event_id+subject_version` |
| `delivery_semantics` | 至少一次投递；业务副作用仍须幂等 |
| `ack_semantics` | received/ignored_duplicate/rejected/accepted_for_review |
| `retry_policy_ref, dead_letter_owner` | 仅投递重试；业务结果unknown不重试 |
| `escalation_trigger/owner` | 重复失败、关键事件滞留、无Owner、PII、版本异常 |
| `audit_fields` | correlation、attempt、policy、ack和关联Commitment |

## 3. 去重与升级

同一event_id+subject_version重复投递只关联既有处理；同event_id但版本不同视为变更事件并触发版本影响。投递失败可由Runtime安全重试；岗位Tool已执行但结果unknown时不得以事件重放再次执行。关键事件进入死信、订阅无业务理由、Owner缺失或PII拦截时升级技术Owner+业务Owner。

## 4. 验收

测试乱序、重复、迟到、版本升级、producer重放、订阅撤销、岗位暂停、PII payload、死信和恢复重放；验证不会产生重复发布、Lead、Commitment或错误批准。
