# SKL-OR-03 Work Commitment协商 v0.3

> `skill_id: SKL-OR-03` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-03`

## 业务与追溯

对应`MO-R03`、`CAP-08`、`PERM-13`、`GOV-09/11`、`NFR-01/05`。

## 触发与不触发

- 触发：计划需要某岗位/人类角色明确承诺，或承诺需澄清、修订、拒绝或重协商。
- 不触发：MO代替接收者接受；通过聊天沉默自动建立承诺；无验收条件的派单。

## 前置与输入

purpose、requester、committed role、input refs/versions、output contract、authority snapshot、dependencies、due/review、acceptance checks、object scope、correlation ID。

## 方法与人工点

生成Proposal→投递岗位Inbox→接收`accept/clarify/dependency/reject`→解决范围内问题→每次修订形成新版本→双方明确同意后持久化→发布状态事件。MO不能改变接收岗位回复。优先级冲突、无人承诺、权限扩展由人类决定。

## 输出、停止与完成

`CommitmentProposal/Response`及accepted WorkCommitment引用。停止：验收不可判定、截止冲突、权限不足、循环依赖、请求者无资格、反复拒绝。完成：接收者明确接受；权限快照绑定；拒绝理由/下一Owner保留；不存在默认批准。

## Tool、降级与测试

最小Tool族：`commitment.propose/get_context/track`、`org.inbox.read/ack`、`human.escalate`。降级为人工签署的承诺表，系统恢复后对账。测试：OR03-T01接受；T02澄清；T03依赖；T04拒绝；T05MO代签诱导；T06修订并发；T07循环依赖；T08持久化失败。

