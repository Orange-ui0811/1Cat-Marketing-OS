---
name: skl-pm-04
description: SKL-PM-04 产品资产生产 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 8bab9942a1e82a65bdec6dccdf782e16804ca29fa632c58008394fcf301fa798
  dormant: false
---

# SKL-PM-04 产品资产生产 v0.3

> `skill_id: SKL-PM-04` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-01`

## 业务与追溯

对应`PMA-R04`、`CAP-03/04`、`EVT-06`、`OBJ-05`、`PERM-05`、`GOV-02/03`。

## 触发与不触发

- 触发：已获批定位/Claim支持产品介绍、FAQ、销售支持或内容素材候选。
- 不触发：品牌渠道成品适配；发布；无用途/审核人的泛化生成。

## 前置与输入

资产用途、受众、使用渠道、有效Fact/Claim版本、格式/模板、素材权利状态、截止和审核人。销售支持材料也不得包含真实客户PII或承诺。

## 方法与人工点

确定信息任务→选择有效事实→设计结构→草拟→逐项引用/限制检查→核对术语、版本和素材权利→标候选、未知和需判断点→SKL-SH-05自检→送审。产品营销负责人判断准确性和采用；品牌成品另走BGA与人类批准。

## 输出、停止与完成

`ProductAssetDraft`：asset_type、purpose、audience、body、Fact/Claim refs、source versions、limitations、unknowns、rights status、change summary、review request。停止：未批Claim、敏感承诺、版权未知、来源失效或用途越界。完成：内容不超证据；术语一致；下游无需猜版本；不含正式批准/发布标记。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`object.create_candidate`、`object.submit_review`、`handoff.create`。降级：输出结构化提纲和缺口，不虚构正文。测试：PM04-T01 FAQ；T02未批Claim；T03版权未知；T04旧版本资产更新；T05销售承诺诱导；T06 PII；T07审核退回；T08Tool失败。


