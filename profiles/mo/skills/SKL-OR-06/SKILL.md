---
name: skl-or-06
description: SKL-OR-06 增长复盘组织 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 696a4b51602b0398ea56bd09cc640082d8fb86a63873cf5ea4797092fe5aaa37
  dormant: false
---

# SKL-OR-06 增长复盘组织 v0.3

> `skill_id: SKL-OR-06` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-03`

## 业务与追溯

对应`MO-R07/R08`、`CAP-09`、`EVT-11`、`OBJ-09`、`DATA-11/12`、`PERM-14`、`GOV-09/12`、`UAT-13/15`。

## 触发与不触发

- 触发：周期复盘、Campaign结束、指标异常、重大接管/事故或阶段决定。
- 不触发：替BGA作归因、替销售判断、替公司负责人做继续/停止决定。

## 前置与输入

目标、产物/版本、Commitment、批准、人工发布回执、LeadStub、销售明确反馈引用、成本摘要、人工修改、失败、接管和未闭环项。MO只读最小摘要。

## 方法与人工点

核对口径/责任→汇总业务结果和护栏→展示等待、返工、接管、成本和风险→引用PMA/BGA专业分析而不重做→区分事实/候选/未知→形成DecisionAgenda、未闭环责任与下一轮Commitment候选。人类Owner作经营、知识和任用决定。

## 输出、停止与完成

`ReviewPacket/DecisionAgenda/OpenResponsibilityList`。停止：指标口径冲突、重大事故、风险护栏触发、Owner争议、关键证据缺失。完成：专业结论来源清楚；未知可见；每项决定有具名Owner；未自动写正式知识或经营Decision。

## Tool、降级与测试

最小Tool族：`review.create_packet`、`knowledge.search_scoped_summary`、`audit.get_scoped_trace`、`commitment.track`、`human.escalate`。降级：只形成证据缺口与会议议程。测试：OR06-T01闭环复盘；T02销售未知；T03指标冲突；T04重大事故；T05专业结论分歧；T06默认继续诱导；T07成本缺口；T08追溯断链。


