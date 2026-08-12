---
name: skl-sh-04
description: SKL-SH-04 决策证据包 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: c9fcd5eb2edba7e9f1ba2803e609d6fdf88cefa4403aae0f1b5fee3d371cad82
  dormant: false
---

# SKL-SH-04 决策证据包 v0.3

> `skill_id: SKL-SH-04` · `version: 0.3.0-freeze-candidate` · 适用：PMA/BGA/MO

## 业务与追溯

支撑`OBJ-09`、`PERM-01/03/04/06/08/12/14`、`GOV-01/02/10`和`CAP-09`。

## 触发与不触发

- 触发：需要人类选择、批准、拒绝、暂停、纠正、缩权或扩权。
- 不触发：确定性状态校验；让Agent自行产生正式Decision；决策人未知。

## 前置与输入合同

决策问题、具名角色决策人、候选及版本、EvidenceNote、约束、反证、影响、不可逆点、截止和不决策时的安全状态。不得包含真实PII或凭据。

## 方法、停止与人工点

1. 校验决策权；2. 区分事实、观察、建议和未知；3. 呈现互斥选项与基准选项；4. 说明影响、风险、可逆性和证据质量；5. 明确请求的决定与记录要求。决策权冲突、关键证据缺失、高风险Owner不明或对象版本漂移时停止。正式决定、例外批准和扩权必须由人类完成。

## 输出合同与完成

`DecisionAgenda`或领域ReviewPacket：decision_id candidate、question、decision_owner、object/version、options、evidence/contradictions、constraints、risks、recommendation、unknowns、deadline、no-decision fallback。完成只表示“可供判断”，不表示批准；沉默永远不产生Decision。

## Tool、降级与测试

- 最小Tool族：`object.get_version`、`approval.status`、`review.create_packet`、`object.submit_review`。
- 降级：审批系统不可用时生成只读人工评审包并保留待批准状态；不得通过聊天回复自动正式化。
- 测试：SH04-T01正常两方案；T02决策人缺失；T03证据冲突；T04默认批准诱导；T05对象已变；T06扩权决定；T07高影响内容；T08审批通道失败。


