---
name: skl-bg-02-campaign
description: SKL-BG-02 Campaign规划 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 57e8c4aa1bc9c9d48bc1c054a8ac46a86901652f112b912878a45d33df4cd03e
  dormant: false
---

# SKL-BG-02 Campaign规划 v0.3

> `skill_id: SKL-BG-02` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-02`

## 业务与追溯

对应`BGA-R02`、`CAP-04`、`EVT-05`、`OBJ-04`、`DATA-06`、`PERM-04/08`、`GOV-01/10`。

## 触发与不触发

- 触发：获批Brief、有效定位/Claim和预算边界齐备，或已有Campaign需调整候选。
- 不触发：自行批准Campaign、设定/修改预算、自动建立投放或客户触达。

## 前置与输入

Brief/批准、受众、目标、Fact/Claim版本、预算边界引用、渠道范围、时限、成功指标定义、依赖、风险和批准人。DEC-08未闭合时不写虚构阈值。

## 方法与人工点

明确目标与假设→选择受众/信息→设计渠道与内容组合→定义CTA、资产、依赖、排期、测量和风险→校验预算只被引用而未改写→并行项与人工批准点→形成候选和决策议程。品牌负责人批准；高影响或预算例外交公司负责人。

## 输出、停止与完成

`CampaignDraft`：goal、audience、message、channels、assets、schedule、budget_boundary_ref、metrics_definition、dependencies、risks、unknowns、approvers、status=`draft`。停止：超预算倾向、Claim无效、目标冲突、客户外联、批准人缺失。完成：依赖可执行，测量口径明确，仍为候选。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`campaign.create_candidate`、`collaboration.plan_submit`、`object.submit_review`、`human.escalate`。降级：只提交方案骨架/缺口。测试：BG02-T01正常；T02预算缺失；T03要求改预算；T04无效Claim；T05目标冲突；T06高影响；T07审批缺失；T08Tool失败。


