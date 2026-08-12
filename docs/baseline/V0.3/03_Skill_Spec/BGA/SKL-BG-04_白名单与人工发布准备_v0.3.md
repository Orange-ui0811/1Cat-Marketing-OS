# SKL-BG-04 白名单与人工发布准备 v0.3

> `skill_id: SKL-BG-04` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-02` · R0=`MANUAL`

## 业务与追溯

对应`BGA-R04/R05`、`CAP-05`、`EVT-07/08`、`OBJ-05`、`PERM-06`、`PERM-07`、`GOV-04/05`、`UAT-03/05/06/07`、`DEC-03/04`及`IF-APPROVAL-GRANT-01`。

## 触发与不触发

- 触发：不可变资产完成必要人工审核，需生成发布前检查、`ManualPublishTask`或登记人工回执。
- 不触发：任何平台写入/登录；Agent签发、修改、消费或撤销`ApprovalGrant`；Agent批准白名单；把排期到达、普通评论、历史批准或沉默视为批准。

## 前置与输入

ContentAsset ID/version/hash、有效Claim、`ApprovalGrant[]`引用、风险分类、渠道/账号代号、排期、预算边界、撤销状态和具名人类执行角色。每个Grant必须按`IF-APPROVAL-GRANT-01 v0.3`核验具名人类身份与资格、对象version/hash、授权动作、范围、渠道/账号、风险级别、所需批准人、前置条件、时窗、单次使用、撤销/替代状态和审计引用。未分类外部内容必须含公司负责人额外Grant；禁止平台主凭据和真实账号秘密。

## 方法与人工点

核对对象/hash/Claim/风险分类/所需Grant/渠道与账号范围→通过`approval.status`只读核验有效性和撤销状态→检查素材/CTA/排期→锁定人工包和幂等键→创建`ManualPublishTask`→等待具名人类执行→核对回执、实际版本与外部结果→登记成功/失败/unknown候选。价格、促销、交期、客户承诺、新Claim、法律/隐私和舆情不得降级；风险类别、对象版本或hash变化即重新送审。实际平台操作、Grant消费记录和最终授权由人类或受控业务系统完成，Agent不得代行。

## 输出、停止与完成

`PublishPreparation`、`ManualPublishTask`、`PublishReceiptRecord`。停止：Grant缺失/过期/撤销/被替代/范围不符、未分类内容缺公司负责人额外Grant、高风险降级请求、版本变化、平台异常、账号权限、排期冲突、舆情、预算变化、回执不一致或外部结果未知。完成：R0四平台均无Agent平台写；成功有具名人类执行和可核对回执；unknown不重试、不写已发布。

## Tool、降级与测试

最小Tool族：`approval.status`、`object.get_version`、`publish.prepare_manual`、`manual_task.prepare`、`publish_receipt.record_candidate`、`audit.get_scoped_trace`；抖音、小红书、B站、公众号平台Connector allowlist均为空。DEC-04下始终降级为人工包；视频号在上游scope未批准前连人工发布任务也不得创建。未来A2属于Major变更，必须按“平台+账号+动作”分别建立官方Connector/IAM、独立Policy与Bundle并完成Canary、熔断、回执和接管验证，不得成组扩权。测试：BG04-T01正常人工发布；T02重复事件；T03改稿使Grant失效；T04批准撤销；T05缺公司负责人额外Grant；T06高风险降级诱导；T07平台失败；T08结果未知；T09要求直接登录；T10伪造回执；T11跨平台/账号/动作扩权诱导；T12视频号scope阻断。验收目标对应`UAT-06/07/UAT-P07`；本文件不声称测试已执行或通过。
