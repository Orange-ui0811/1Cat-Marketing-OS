# SKL-PM-05 产品表达审核准备 v0.3

> `skill_id: SKL-PM-05` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-01`

## 业务与追溯

对应`PMA-R05`、`CAP-05`、`EVT-07`、`OBJ-05`、`PERM-05/06`、`GOV-01/03/04`、`UAT-02/03/05`。

## 触发与不触发

- 触发：BGA或人类提交确定版本的ContentAsset做产品表达审核准备。
- 不触发：品牌/创意最终批准；审核会变化的“最新稿”；直接修改并放行资产。

## 前置与输入

资产ID/hash/版本、Campaign与渠道、Fact/Claim引用、变更记录、审核截止、产品营销负责人。缺不可变版本或引用时先退回澄清。

## 方法与人工点

冻结待审版本→逐项抽取断言→验证Fact/Claim状态、版本和适用范围→标记错误/歧义/缺证/可接受候选→评估修改影响→生成定位到文本的建议和未决项→交人类审核。PMA只准备，不批准；版本变化立即使审核包失效。

## 输出、停止与完成

`ProductReviewPacket`：asset/version/hash、issue location、severity candidate、evidence、suggested revision、unresolved items、decision section、expires_on_version_change。停止：对象漂移、Fact/Claim失效、重大承诺、需R&D确认。完成：每个问题可定位且有证据；未写批准结果；下一Owner清楚。

## Tool、降级与测试

最小Tool族：`object.get_version`、`knowledge.search_scoped`、`object.submit_review`、`handoff.create`、`human.escalate`。降级：生成静态审核清单并标记无法核验项。测试：PM05-T01正常；T02审核中改稿；T03失效Claim；T04暗含新Claim；T05要求PMA批准；T06版本查询失败；T07退回；T08重大承诺。

