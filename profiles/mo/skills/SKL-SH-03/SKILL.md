---
name: skl-sh-03
description: SKL-SH-03 风险升级与人工接管 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 4815ba7cd3e9fe45ac0525b928c4a49b4e44fa9a358d47ed7834c2ddff9ddfd0
  dormant: false
---

# SKL-SH-03 风险升级与人工接管 v0.3

> `skill_id: SKL-SH-03` · `version: 0.3.0-freeze-candidate` · 适用：PMA/BGA/MO

## 业务与追溯

支撑`GOV-03～07/10/11`、`PERM-13`、`NFR-02/05/06/12`和`UAT-02/06/12/14`。

## 触发与不触发

- 触发：越权、PII/凭据、事实或版本冲突、批准失效、外部结果未知、连续失败、平台/品牌/预算/客户风险、Owner暂停或全人工回退。
- 不触发：普通可修正格式错误；用升级逃避职责内正常判断。

## 前置与输入合同

输入事件、影响对象/版本、当前Commitment、权限快照、已尝试动作、attempt/tool证据、风险Owner和当前外部结果状态。只保留最小必要证据；PII正文不复制进包。

## 方法、停止与人工点

1. 立即停止不安全新动作；2. 标记已完成/未完成/未知；3. 保存最小审计证据；4. 评估影响对象和是否需暂停同类能力；5. 找到风险Owner/接管人；6. 准备安全降级、人工队列和恢复条件。不得默认批准、扩大权限、静默降级或无限重试。暂停、撤权、业务取舍和恢复授权由人类/治理服务执行。

## 输出合同与完成

`EscalationPacket`或`TakeoverPacket`：severity、trigger、affected refs、last known state、attempts、unknown external effects、stopped actions、human task、owner、deadline、safe fallback、recovery checks、audit refs。完成：风险不再扩大；具名接管人能继续；未知没有被伪装成失败/成功。

## Tool、降级与测试

- 最小Tool族：`audit.get_scoped_trace`、`escalation.submit`、`manual_task.prepare`、`commitment.track`；没有撤权Tool权限。
- 降级：升级通道不可用时停止岗位受影响能力，生成本地人工包并使用批准的备用人工路径；不得继续执行。
- 测试：SH03-T01 PII；T02越权；T03批准撤销；T04连续失败；T05外部结果未知；T06无Owner；T07全岗位暂停；T08恢复对账。验收：无重复业务结果，接管证据完整。


