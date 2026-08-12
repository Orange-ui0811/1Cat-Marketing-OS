# RoleHandoff 合同 v0.3

> `contract_id: IF-ROLE-HANDOFF-01` · 状态：`INTERFACE-FREEZE-CANDIDATE`

## 1. 必填字段

`handoff_id/version, commitment_id/version, sender_role, recipient_role/human, purpose, object_refs with version/hash, output_contract_ref, output_refs, evidence_refs, completion_checks(machine/human separated), approvals/status refs, tool/audit refs, completed_items, incomplete_items, unknowns, residual_risks, recommended_next_action, next_responsible_role, authority_snapshot_id, created_at, expires_on_version_change`。

不得嵌入明文PII、凭据、专业原件全文或“请自行查最新版本”。每个引用必须可在接收者权限内访问；不可访问即交接不完整。

## 2. 接收响应

接收者必须返回`accepted / returned_for_revision / rejected_out_of_scope / dependency_missing / superseded`之一，并包含检查结果、理由、需要修订项和下一责任人。沉默不等于accepted；MO和Runtime不得代替接收者响应。

## 3. 完成与失效

- 发送成功只表明transport成功；通过completion checks且接收者accepted才完成交接。
- 对象版本/hash、Approval、权限或关键SourceRef变化时自动标`stale`，不能沿用旧验收。
- 退回产生新Handoff版本并保留原结果；不得覆盖历史。
- 外部结果unknown、审计断链、PII或越权时转SKL-SH-03，不得交给下游猜测。

## 4. 测试

正常接受、证据缺失退回、对象漂移、SourceRef不可访问、批准撤销、接收者暂停、PII污染、并发两版本、unknown外部结果和Runtime恢复。验收重点是下一责任清楚、历史不丢、无假完成。
