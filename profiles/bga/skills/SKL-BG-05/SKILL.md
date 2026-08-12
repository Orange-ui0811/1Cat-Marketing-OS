---
name: skl-bg-05
description: SKL-BG-05 线索登记、去重建议与销售移交 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 7b3bbb49225c3246d3a1c537e66e15a0ec73a5b4a580fdfebcb24ebc12308a5b
  dormant: false
---

# SKL-BG-05 线索登记、去重建议与销售移交 v0.3

> `skill_id: SKL-BG-05` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-02` · 真实PII禁入

## 业务与追溯

对应`BGA-R06/R07`、`CAP-06`、`EVT-09/10`、`OBJ-06/07`、`DATA-09/10`、`PERM-09`、`PERM-10`、`PERM-11`、`PERM-12`、`GOV-08`、`UAT-08～11`及`DEC-01/02/06`。

## 触发与不触发

- 触发：人工提供的非PII LeadStub、来源触点、销售接收事件，或带可验证销售身份、对象版本、`pending/valid/invalid/needs_more_info`之一及版本化原因码的明确回传事件。
- 不触发：读取私信正文/姓名/电话/账号；客户回复或外联；Agent创建、补齐或改写询盘状态/原因码；根据行为或文本推断有效询盘；不确定匹配自动强并。

## 前置与输入

不含明文PII的`lead_id`、不透明`source_record_ref`、触点、Campaign/ContentRef、时间、批准的确定性去重特征、销售接口规则和权限快照。销售反馈还必须包含经授权的销售人类身份引用、LeadStub/version、状态、`reason_code`、`reason_code_registry_version`、写入时间和审计引用；只有销售身份可写四种状态和原因码。DEC-01未签署前，口径与指标均标记未冻结；DEC-06未关闭时任何明文PII均fail-closed。

## 方法与人工点

验证最小化/敏感标签→登记全部允许触点→应用批准的确定性规则→不确定则`MergeProposal`→准备`SalesHandoff`→对销售反馈验证身份、对象版本、四值枚举和版本化原因码→仅记录销售原始决定的不可变引用。未收到合格销售反馈时，`inquiry_status`保持未设置，BGA只记录“缺少明确反馈引用”；MO按DEC-02生成内部提醒/升级候选，R0不得自动外发。品牌Owner核验不确定合并；销售独占询盘有效性及商业状态判断，Agent不预测、不代填、不把未反馈默认为`pending`或`invalid`。

## 输出、停止与完成

`LeadStub`、`MergeProposal`、`SalesHandoff`、`SalesFeedbackReference`。其中SalesFeedbackReference仅在合格回传存在时携带销售身份引用、原始状态、原因码及注册表版本；不得成为Agent可写销售状态的旁路。停止：疑似PII、source ref失效、合并不确定、销售拒收/缺少合格反馈、非销售身份写状态、非法枚举、原因码或注册表版本缺失、隐私规则缺失。完成：触点不丢；不确定未强并；销售状态未推断或默认；Session/Memory/日志无PII。

## Tool、降级与测试

最小Tool族：`lead_stub.record`、`dedupe.evaluate_rule`、`object.get_version`、`handoff.create`、`sales_feedback.record_reference`、`human.escalate`；`sales_feedback.record_reference`只接受销售侧已写事实引用，不授予Agent写询盘状态的能力，不存在PII Adapter写入或客户外联能力。降级：生成人工处理引用，不复制原文、不创建销售状态。测试：BG05-T01确定匹配；T02不确定；T03跨平台触点；T04 PII注入；T05销售未回且状态保持未设置；T06销售明确回传；T07非销售身份伪造状态；T08非法枚举；T09原因码无注册表版本；T10外联诱导；T11重复事件。

