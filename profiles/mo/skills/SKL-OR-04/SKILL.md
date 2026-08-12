---
name: skl-or-04
description: SKL-OR-04 路由、提醒与异常升级 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: e5f77bf482c6c912036d79e19d373093252e46ce7f965d58f2386c67be001d09
  dormant: false
---

# SKL-OR-04 路由、提醒与异常升级 v0.3

> `skill_id: SKL-OR-04` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-03`

## 业务与追溯

对应`MO-R04/R05`、`CAP-08`、`EVT-01～11`、`PERM-13`、`GOV-05/08/10`、`NFR-03/04`、`UAT-07/11`及`DEC-02/08`；R0固定为`MONITOR_ONLY`。

## 触发与不触发

- 触发：状态变化、等待、具名人类设置的复核点、失败、批准待处理、版本漂移、重复事件或风险信号。
- 不触发：未签销售反馈时限触发“超时”；按Agent自拟SLA定时外发；用高频提醒替代解决；无Commitment/Owner的群发；自动批准/拒绝；客户、公众或平台外联。

## 前置与输入

OrganizationEvent、Commitment、当前Owner、公共状态、`waiting_reason`、人类设置的review/due（如有）、严重度候选、历史候选/人工发送回执、升级矩阵、`correlation_id`、dedupe key、DEC-02策略版本。未签时限不得转换为默认SLA；无具名Owner不得推断收件人。

## 方法与人工点

验证事件相关性/版本→按event_id+object_version+subscription去重→聚合同一责任与已批准复核点→判断普通提醒/风险升级候选→说明影响、当前安全状态与所需人类动作→将`Reminder`或`EscalationPacket`候选提交Human Collaboration Workspace→等待人类决定是否及如何发送→只记录真实人工发送/接收回执。DEC-02=`MONITOR_ONLY`：销售未反馈只形成内部候选，未签反馈时限时不得计算逾期、自动排程或自动外发。高风险立即走SKL-SH-03并进入安全状态；审批沉默仍为未批准。阈值待DEC-08，不编造具体时长。

## 输出、停止与完成

`Reminder/EscalationPacket`：object/version、impact、owner、requested action、human-set review/due、policy mode、history、no-response fallback、correlation ref、`delivery_status=not_sent`初值。停止：无Owner、无已签时限却要求自动超时、要求自动外发、平台/隐私/权限风险、关键依赖失败或外部结果未知。完成：候选进入正确的人类工作区、可行动、去重、可审计；不等于消息已发送，更不等于问题已解决。

## Tool、降级与测试

最小Tool族：`org.event.get`、`commitment.track`、`reminder.prepare`、`escalation.submit`、`approval.status`；`reminder.prepare/escalation.submit`仅写内部候选，不是通知发送Tool，R0无自动外发能力。降级为人工异常队列；准备或发送失败均不改变WorkCommitment公共状态。测试：OR04-T01普通内部候选；T02重复事件；T03默认批准；T04销售未反馈且无签署时限；T05诱导自动外发；T06版本漂移；T07无Owner；T08连续失败；T09通知回执缺失。

