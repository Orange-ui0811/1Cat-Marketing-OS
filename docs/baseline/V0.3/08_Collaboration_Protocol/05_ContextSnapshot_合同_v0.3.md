# ContextSnapshot 合同 v0.3

> `contract_id: IF-CONTEXT-SNAPSHOT-01` · 状态：`INTERFACE-FREEZE-CANDIDATE`  
> 用途：为单次Run提供最小、可追溯、可过期上下文；不是Memory或业务原件副本。

## 1. 必填字段

`snapshot_id/hash, role_id, role_manifest_version, profile_id, profile_service_identity_id, profile_bundle_version, commitment_id/version, purpose, expected_outcome, requester/business_owner, object_refs(version/hash/status), source_refs(scope/access), approval_refs(status only), authority_snapshot_id, allowed_tool_capabilities, dependencies/status, prior_handoff_refs, active_memory_refs, output_schema_id/version, policy/version_bundle, sensitivity_labels, created_at, expires_at_or_event, correlation_id`。

## 2. 构建与注入顺序

1. 验证岗位生命周期、profile服务身份和版本组合；2. 验证Commitment已接受或处于允许澄清状态；3. 从权威载体读取当前对象元数据/SourceRef；4. 应用数据最小化和PII/凭据拦截；5. 绑定权限快照、Tool allowlist和输出Schema；6. 注入必要Handoff；7. 最后注入作用域匹配且无冲突的approved Memory；8. 生成不可变snapshot/hash。

优先级：Manifest/SOUL/Policy硬门 > 当前Authority/Object/Approval > Commitment/Handoff > approved Memory > Session。低优先级冲突时不注入，创建冲突记录。MO只能获得组织元数据和最小专业摘要；PMA不能获得Lead/PII；BGA只能获得去敏LeadStub。

## 3. 失效与刷新

对象版本/hash、Approval、权限、岗位状态、SourceRef可访问性或Policy Major变化时立即失效；Session不得继续调用Tool。刷新产生新snapshot并重新校验Commitment，不原地修改。外部结果unknown不会通过刷新变成safe retry。

## 4. 测试

最小字段、越作用域SourceRef、PII/凭据、旧Memory冲突、对象漂移、权限撤销、跨岗位专业正文泄漏、暂停岗位、恢复后人工变更和snapshot重放。通过标准：上下文足够完成任务但不包含禁入或不必要数据，所有注入可追溯。
