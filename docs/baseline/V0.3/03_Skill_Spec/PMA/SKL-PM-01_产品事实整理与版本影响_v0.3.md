# SKL-PM-01 产品事实整理与版本影响 v0.3

> `skill_id: SKL-PM-01` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-01`

## 业务与追溯

对应`PMA-R01/R07`、`CAP-02`、`EVT-02/04/11`、`OBJ-02/03/05`、`PERM-02`、`GOV-03`、`UAT-02/03/05`。

## 触发与不触发

- 触发：新产品资料、Fact待确认/变化/失效、Claim影响检查或下游事实争议。
- 不触发：确认正式Fact；无对象ID/版本的自由写作；处理未授权研发材料。

## 前置与输入

产品对象ID/版本、人工提供且授权的SourceRef、当前Fact/Claim引用、测试条件、适用范围、产品/R&D确认Owner。禁止真实PII、凭据和任意外部检索。

## 方法与人工点

使用SKL-SH-01分类→对齐产品版本和测试条件→去重但保留来源→标记一致/冲突/缺失/过期→形成ProductFactCandidate→扫描受影响Claim/Campaign/ContentAsset→提出暂停/重审范围。产品/R&D确认正式Fact；产品营销负责人解释营销影响；Agent不得正式化。

## 输出、停止与完成

- `ProductFactCandidate`：statement、evidence、conditions、version、scope、limitations、contradictions、unknowns、confirmation_owner。
- `ImpactFinding`：affected refs/versions、reason、severity candidate、safe state、next owner。
- 停止：来源冲突、关键条件缺失、安全/价格/交付承诺、无法确定版本、越权材料、PII。
- 完成：每个候选可追溯；影响对象为确定版本；正式状态未改变；风险项已交接。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`object.get_version`、`evidence.create_note_candidate`、`fact.flag_gap`、`impact.analyze_candidate`、`object.create_candidate`、`human.escalate`。降级为人工证据表和影响清单；冲突未决时暂停下游引用。测试：PM01-T01正常；T02缺证据；T03冲突；T04过期；T05Claim失效传播；T06版本漂移；T07越权/PII；T08Tool失败。所有异常必须保留原状态。

