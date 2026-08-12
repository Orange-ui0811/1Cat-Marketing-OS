---
name: skl-or-02
description: SKL-OR-02 跨岗位协作规划 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 6763d59bcb1d82df246d714545958654190a09cb83f9f633fcdf7d200d01b056
  dormant: false
---

# SKL-OR-02 跨岗位协作规划 v0.3

> `skill_id: SKL-OR-02` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-03`

## 业务与追溯

对应`MO-R02`、`CAP-08`、`EVT-01～11`、`PERM-13`、`GOV-07/09`。

## 触发与不触发

- 触发：完整目标需要PMA、BGA、产品/R&D、销售或人类Owner协作。
- 不触发：单岗位可独立完成；用中央Workflow分解专业步骤；重写组织归属。

## 前置与输入

有效Brief、目标结果、对象状态摘要、Owner、复核点、批准规则、已知依赖、岗位能力/生命周期状态和最小权限边界。

## 方法与人工点

识别结果→分离专业责任/规则自动化/人类决定→提出Commitment候选→标并行与依赖→设置交接、批准、接管和安全结束→检查责任真空/重叠/循环→提交计划供相关岗位协商。岗位可拒绝；优先级和责任争议由人类Owner解决。

## 输出、停止与完成

`CollaborationPlan/DependencyMap`：purpose、candidate committed role、input refs、output contract、acceptance、dependencies、review point、risk/approval、next handoff。停止：责任真空/重叠、岗位不可用、跨部门接口无Owner、越权或循环依赖。完成：PMA/BGA仍是自治岗位，Runtime职责未写成MO专业工作。

## Tool、降级与测试

最小Tool族：`collaboration.plan_submit`、`knowledge.search_scoped_summary`、`role.directory.read`、`human.request_clarification`、`human.escalate`。降级为人工责任/依赖表。测试：OR02-T01并行研究；T02单岗位不拆；T03责任冲突；T04无销售Owner；T05岗位暂停；T06循环依赖；T07越权计划；T08 Runtime被误作Owner。


