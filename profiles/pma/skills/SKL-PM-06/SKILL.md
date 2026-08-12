---
name: skl-pm-06-rnd
description: SKL-PM-06 R&D证据需求反馈 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: a92d3d39a1bd6dd76990b857a953d484d4274da3b5ee3e7e72bbad6fd31a7646
  dormant: false
---

# SKL-PM-06 R&D证据需求反馈 v0.3

> `skill_id: SKL-PM-06` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-01`

## 业务与追溯

对应`PMA-R06`、`CAP-02`、`EVT-02/04/10`、`DATA-02/03`、`PERM-02`、`GOV-03/10`。

## 触发与不触发

- 触发：事实缺口/冲突/过期、去敏销售异议或下游需要产品/R&D确认。
- 不触发：要求披露受限研发资料；让PMA预设答案；无业务影响的无限索取。

## 前置与输入

问题对象/版本、现有EvidenceNote、缺口、业务影响、所需确认类型、期望复核点、R&D接口Owner和最小资料范围。

## 方法与人工点

说明业务问题→区分事实确认/补证/解释→列出现有支持与冲突→定义可接受回复和最小必要范围→关联受影响对象→写明不回复时暂停/候选降级→通过Commitment请求。R&D决定可提供内容并确认事实；响应先登记为证据，不能自动正式化。

## 输出、停止与完成

`EvidenceRequest`：question、object/version、existing evidence、gap、requested evidence/answer、business impact、review point、acceptance criteria、safe fallback、next owner。停止：无接口Owner、涉及受限资料、反复超时、影响高风险Claim或请求者无权。完成：请求可回答、不过度索取、未替R&D下结论。

## Tool、降级与测试

最小Tool族：`rd_evidence.request_candidate`、`commitment.propose`、`human.escalate`、`evidence.create_note_candidate`。降级：生成人工证据请求包；超时保持受影响对象暂停。测试：PM06-T01正常；T02问题过宽；T03受限资料；T04无Owner；T05超时；T06响应冲突；T07越权催办；T08通道失败。


