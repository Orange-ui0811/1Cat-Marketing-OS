# SKL-SH-02 组织承诺与岗位交接 v0.3

> `skill_id: SKL-SH-02` · `version: 0.3.0-freeze-candidate` · 适用：PMA/BGA/MO

## 业务与追溯

支撑`CAP-08`、`PERM-13`、`GOV-07/09`、`NFR-01/02/12`；连接岗位独立履职与下一责任人。

## 触发与不触发

- 触发：接收委派、响应CommitmentProposal、提交成果、请求修订、转交下一责任人或日终交班。
- 不触发：由MO代替其他岗位承诺；无Owner的随口请求；把内部函数调用当岗位交接。

## 前置与输入合同

必填：purpose、requester、committed role、输入对象/版本、输出合同、权限快照、依赖、due/review、验收条件、correlation ID。输入不得含PII/凭据；请求者资格和生命周期状态必须有效。

## 方法、停止与人工点

1. 校验使命、请求者和岗位状态；2. 校验输入、权限、依赖和验收可判定性；3. 明确`accept/clarify/dependency/reject`；4. 工作后冻结输出版本并自检；5. 形成RoleHandoff；6. 接收者明确接受或退回。无Owner、越界、循环依赖、截止冲突、版本漂移或验收不可判定时停止。优先级冲突和跨Owner改派由人类决定。

## 输出合同与完成

输出`CommitmentResponse`或`RoleHandoff`，至少含对象版本、证据、完成检查、未完成项、残余风险、下一动作/责任人、权限快照和审计引用。完成以接收者按合同验收为准，不以发送成功或Run结束为准。

## Tool、降级与测试

- 最小Tool族：`commitment.respond/track`、`handoff.create/return`、`org.inbox.ack`。
- 降级：持久交接不可用时生成可下载的人工交接包并标记`manual_reconciliation_required`；不得用Memory保存任务状态。
- 测试：SH02-T01接受；T02澄清；T03拒绝越界；T04对象漂移；T05接收者退回；T06循环依赖；T07Runtime中断；T08恢复后人工修改。验收：责任、版本和未完成项不丢失。

