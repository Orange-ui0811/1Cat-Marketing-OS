# 三数字岗位共享 Memory 治理合同 v0.3

> 状态：`MEMORY-POLICY-FREEZE-CANDIDATE`  
> 范围：PMA、BGA、MO的跨Session低敏稳定偏好。  
> 不变项：真实PII、凭据、业务原件、在途状态和完整日志禁止进入Memory。

## 1. 定位与权威关系

Memory只保存少量、稳定、低敏、经批准且能改善跨会话协作的事实或偏好；不保存SOP、正式ProductFact/Claim、对象状态、Commitment、Approval、平台结果、客户/Lead信息或业务日志。正式对象仍由权威业务载体持有；DEC-05未关闭时仅保存SourceRef指针，不假设载体。

## 2. MemoryRecord合同

| 字段 | 要求 |
|---|---|
| `memory_id / role_id / namespace` | 稳定ID、岗位隔离命名空间 |
| `statement / category` | 单一低敏事实或偏好，类别在岗位allowlist内 |
| `source_ref / evidence_class` | 可追溯人工决定或稳定观察，不存原文 |
| `approved_by / approved_at` | 具名业务Owner或授权审核人 |
| `scope / effective_from / review_at` | 适用任务、对象类别与复核事件；不编造保留天数 |
| `supersedes / status` | `candidate/active/superseded/deletion_pending/deleted` |
| `sensitivity / pii_check` | 只能`low_internal`；PII检查通过 |
| `audit_ref` | 创建、读取、纠正、禁用与删除证据 |

## 3. 写入与注入

写入：Agent只能生成`MemoryCandidate`；Owner批准、PII检查、重复/冲突检查和审计成功后才成为active。单次人工修改、未经确认的偏好和模型推断不能写入。

每次任务按以下优先级构建上下文：

1. 当前Role Manifest、SOUL和Tool/Memory Policy的硬边界；
2. 当前`ContextSnapshot`中的目标、对象版本、SourceRef和权限快照；
3. 权威对象当前状态与人类批准；
4. 当前Commitment与Handoff中的必要状态；
5. 经批准且作用域匹配的active Memory；
6. 当前Session临时推理。

低优先级与高优先级冲突时不注入冲突Memory，记录`MemoryConflict`并交Owner；不得用“最近写入”或模型偏好自动裁决。上下文仅注入完成当前任务最少记录，MO不得继承PMA/BGA专业Memory正文。

## 4. 禁止内容与冲突处理

- 明文姓名、电话、邮箱、平台账号、聊天正文、设备/地址标识或可重识别组合；
- 访问令牌、Cookie、密钥、凭据路径、平台主账号信息；
- 正式Fact/Claim/Brand规则/Decision的唯一副本；
- Campaign、审批、排期、Lead、销售反馈、Commitment和提醒的在途状态；
- 完整Prompt、Tool参数/响应、错误堆栈或长业务原文；
- 未批准的学习候选、主观人物评价或敏感画像。

发现PII/凭据立即阻断写入并按SKL-SH-03升级；发现事实冲突，将记录置为`quarantined candidate`或停止注入，保留新旧引用，等待Owner裁决，不静默覆盖。

## 5. 删除、暂停与退役

- DEC-06关闭前不写具体保留天数；`review_at`使用事件触发或“待政策决定”。
- 删除请求先冻结注入，执行物理/逻辑删除由开发方案决定；验证必须覆盖主存、索引、缓存、备份策略和派生上下文，并生成不含被删内容的`DeletionEvidence`。
- `deletion_pending`期间不可读；失败升级数据/隐私Owner，不能标记deleted。
- WorkCommitment=`paused`或数字岗位生命周期=`suspended`时停止Memory写入，只允许具名Owner审计和纠错；恢复前重做版本、冲突和权限检查。
- 岗位`retiring/retired`时撤销读写、冻结namespace、逐项决定迁移/删除/保留审计；不得把个人化Memory直接继承给其他岗位。

## 6. 审计与测试

所有候选、批准、注入、拒绝、冲突、纠正、暂停和删除都记录role、memory ID、policy/version、用途和correlation ID，不记录秘密正文。测试：PII/凭据拒绝、单次反馈不写、SourceRef失效、旧记忆与当前对象冲突、越作用域注入、跨岗位泄漏、删除验证失败、暂停写入、退役撤权、Runtime恢复后缓存不复活。
