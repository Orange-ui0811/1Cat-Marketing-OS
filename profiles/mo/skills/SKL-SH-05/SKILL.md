---
name: skl-sh-05
description: SKL-SH-05 自我检查与任务复盘 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 2e9d33457c2ad24c7f251b9e440574199c7abba150b752182eadb54865f3cdb5
  dormant: false
---

# SKL-SH-05 自我检查与任务复盘 v0.3

> `skill_id: SKL-SH-05` · `version: 0.3.0-freeze-candidate` · 适用：PMA/BGA/MO

## 业务与追溯

支撑`CAP-09`、`GOV-09/12`、`NFR-01/09/10`；为岗位任用、回归和学习候选提供证据。

## 触发与不触发

- 触发：产物提交前、人工退回后、Commitment结束、日终交班或周期复盘。
- 不触发：把自评当人类验收；自动更新SOUL/Skill/Memory；对真实PII做复盘语料。

## 前置与输入合同

role/Manifest/SOUL/Skill/Policy版本、Commitment、对象版本、产物、EvidenceNote、Tool轨迹、人工修改/评价、成本摘要和已知风险。Tool错误必须脱敏。

## 方法、停止与人工点

1. 检查使命与非职责；2. 检查证据、对象/版本与状态；3. 检查输入输出和验收合同；4. 检查权限、Tool响应、幂等与审计；5. 对比人工修改；6. 区分个案与可能模式；7. 提出可测试学习候选。发现硬门失败、系统性漂移、PII或同类连续失败时暂停相关提交并升级。是否采纳候选由Owner决定。

## 输出合同与完成

`SelfCheckReport`含checks、failures、residual risks、evidence refs、cost summary、next owner；`LearningCandidate`含observations、scope、proposed change target、counterexample、test additions、reviewer。完成：问题可复现、候选未自动泛化、修改前后历史保留。

## Tool、降级与测试

- 最小Tool族：`audit.get_scoped_trace`、`object.get_version`、`review.create_packet`、`knowledge.submit_candidate`。
- 降级：审计不完整时自检标记`inconclusive`并阻止正式交接；不得补造轨迹。
- 测试：SH05-T01正常自检；T02人工退回；T03角色漂移；T04缺审计；T05PII日志；T06同类失败重复；T07单次偏好误泛化；T08版本升级回归。


