---
name: skl-bg-06
description: SKL-BG-06 增长归因与实验复盘 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 1a1cdaf6350e8a12b0e4df84df448609d24f8af27e7e726ccca9c8f4c2331199
  dormant: false
---

# SKL-BG-06 增长归因与实验复盘 v0.3

> `skill_id: SKL-BG-06` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-02`

## 业务与追溯

对应`BGA-R08`、`CAP-07/09`、`EVT-10/11`、`OBJ-07`、`OBJ-08`、`OBJ-09`、`DATA-08/10/12`、`PERM-08/12/14`、`UAT-10/11/13`及`DEC-01/02/08`。

## 触发与不触发

- 触发：人工发布/LeadStub/销售明确反馈形成、实验结束、指标异常或复盘。
- 不触发：把缺失反馈当`invalid`或把`pending/needs_more_info`重分类；Agent判断有效询盘；自动继续/停止实验；自动调预算；输出正式归因决定。

## 前置与输入

Campaign/Content/channel/touchpoint SourceRef、成本边界、LeadStub、销售明确反馈引用、实验假设、指标口径和数据质量说明。销售反馈引用必须能核验授权销售身份、LeadStub/version、`pending/valid/invalid/needs_more_info`、`reason_code`和`reason_code_registry_version`。DEC-01未签署前有效询盘口径与相关指标标记未冻结；DEC-08前阈值为待定，只采baseline。

## 方法与人工点

核对来源链与销售写入身份→按原因码注册表版本分组，禁止跨版本静默合并→区分观察/相关/归因候选→只在已获人类批准的指标定义下对齐分子分母和时间窗→分析内容/渠道贡献→单列未反馈、`pending`和`needs_more_info`，不得计作`valid`或`invalid`→列偏差、缺失与替代解释→检查线索量/销售明确反馈质量/成本护栏→提出实验或经营选项。只有销售写询盘状态与原因码；品牌Owner判断归因与实验，公司负责人作阶段决定。

## 输出、停止与完成

`AttributionCandidate/ExperimentReview`：evidence chain、metric definitions/status、sales writer evidence、reason-code registry version、feedback coverage、observations、attribution hypothesis、limitations、alternative explanations、cost context、recommendations、decision items。停止：非销售状态写入、原因码版本缺失/冲突、指标口径未批准却被要求给正式KPI、样本不足、成本无权限、负面风险或需要经营决定。完成：不把Lead数当询盘；不填补、预测或重分类销售状态；未反馈显式列缺口；结论保持候选。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`attribution.submit_candidate`、`review.create_packet`、`object.submit_review`、`human.escalate`；无销售状态写入、预算写入或外联Tool。降级：提交数据完整性/反馈覆盖/口径问题清单，不生成正式有效询盘指标。测试：BG06-T01闭环；T02无销售反馈；T03非销售身份写`valid`；T04原因码跨版本；T05`pending/needs_more_info`被误计；T06口径冲突；T07样本不足；T08线索涨而销售明确质量降；T09预算调整诱导；T10相关误当因果；T11数据Tool失败。

