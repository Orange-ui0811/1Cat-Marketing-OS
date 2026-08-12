---
name: skl-or-05
description: SKL-OR-05 人工接管与恢复组织 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 6b10ea7b65138d3cd56845bcec8e50a67e1b60b2a09f25174d7626083ea2bf56
  dormant: false
---

# SKL-OR-05 人工接管与恢复组织 v0.3

> `skill_id: SKL-OR-05` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-03`

## 业务与追溯

对应`MO-R06`、`CAP-08`、`GOV-05～07`、`NFR-02/06/12`、`UAT-06/07/14`。

## 触发与不触发

- 触发：Agent/Owner暂停、Runtime中断、连续失败、权限撤销、风险红线、外部结果未知或全人工回退。
- 不触发：普通可重试的无副作用瞬时错误；MO自行决定恢复或扩权。

## 前置与输入

受影响Commitment、对象/版本、最后已确认业务状态、attempt/tool证据、未完成与不确定动作、风险、人工接管角色和恢复门。

## 方法与人工点

停止新尝试→冻结输入/输出版本→列已完成/未完成/unknown→检查可能重复外部结果→准备人工队列和优先级候选→人类接管→记录人工改动→恢复前对账、重放安全事件或废弃旧承诺→人类重新授权。任何unknown外部结果不得自动重试。

## 输出、停止与完成

`TakeoverPacket/ReconciliationPlan`：affected refs、last confirmed state、attempts、unknowns、manual tasks、dedupe keys、human changes、recovery checks、new authority snapshot。停止：状态无法确定、可能重复发布/写入、审计缺口、接管人不明。完成：人类可继续；恢复不覆盖人工改动；差异可审计。

## Tool、降级与测试

最小Tool族：`commitment.track`、`audit.get_scoped_trace`、`manual_task.prepare`、`org.event.reconcile_candidate`、`human.escalate`；暂停/撤权由治理服务和人类执行。测试：OR05-T01单Agent暂停；T02 Runtime中断；T03外部unknown；T04全人工；T05恢复对账；T06人工改版本；T07审计缺口；T08重复事件。满足UAT-14才可limited active。


