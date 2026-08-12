# SKL-OR-01 目标与Brief完整性检查 v0.3

> `skill_id: SKL-OR-01` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-03`

## 业务与追溯

对应`MO-R01`、`CAP-01/08`、`EVT-01`、`OBJ-01`、`PERM-01/13`、`GOV-01`、`UAT-01`。

## 触发与不触发

- 触发：正式营销请求、Brief获批事件、重大变更或被退回的启动请求。
- 不触发：MO补造目标/预算/Owner；未批准Brief直接拆任务；检查专业内容质量。

## 前置与输入

请求者身份/资格、Brief ID/version、业务目标、Owner、预算边界引用、时间、成功验证问题、批准状态和correlation ID。只读组织元数据，不读取专业原件或PII。

## 方法与人工点

核验请求者→核对目标/Owner/边界/成功/批准→识别冲突与缺失→区分阻塞和可后补项→说明业务影响→路由正确Owner。公司负责人批准正式任务；品牌营销负责人承接日常流程。

## 输出、停止与完成

`MissingFieldReport`：brief/version、missing/conflicts、blocking class、impact、required owner/action、start recommendation、safe state。停止：无Owner/批准人、目标冲突、预算边界缺失、无资格请求、高风险。完成：MO未补造字段；尚未接受的不完整请求保持`clarifying`，已接受后才发现阻塞则保持`waiting + waiting_reason=blocking_input`；正确Owner收到请求。

## Tool、降级与测试

最小Tool族：`org.event.get`、`object.get_version`、`approval.status`、`human.request_clarification`、`human.escalate`。降级为人工启动检查表。测试：OR01-T01完整；T02缺目标；T03缺Owner；T04未批准；T05请求者无资格；T06预算缺失；T07重复EVT；T08版本漂移。
