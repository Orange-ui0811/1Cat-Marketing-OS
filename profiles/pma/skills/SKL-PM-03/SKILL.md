---
name: skl-pm-03-icp-claim
description: SKL-PM-03 ICP、定位和Claim候选 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 8e2affc6948f0db57cc742ec3b7368f4ab00be698255fe499e19b4f469a0a481
  dormant: false
---

# SKL-PM-03 ICP、定位和Claim候选 v0.3

> `skill_id: SKL-PM-03` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-01`

## 业务与追溯

对应`PMA-R03`、`CAP-03`、`EVT-04`、`OBJ-03`、`DATA-05`、`PERM-03`、`GOV-01/02/10`、`UAT-03/04`。

## 触发与不触发

- 触发：已批准Brief、有效Fact和ResearchFinding齐备，需生成或复核候选。
- 不触发：无证据效果承诺；批准或启用Claim；生成价格、交期或客户承诺。

## 前置与输入

Brief/版本与批准引用、有效ProductFact、ResearchFinding、经营方向、限制、禁用表达、对象Owner和批准路径。任一核心对象版本不可核验则不开始。

## 方法与人工点

提炼ICP问题/场景→建立价值-证据映射→生成互斥候选→检查差异化、可证实性、适用/禁止范围→标R&D确认点→执行事实、绝对化、比较、价格和承诺风险检查→用SKL-SH-04形成决策包。R&D确认事实性，公司负责人批准，产品营销Owner判断推荐。

## 输出、停止与完成

`PositioningCandidate/ClaimCandidate`：audience、scenario、expression、evidence map、allowed/prohibited scope、risks、version、alternatives、approvers、status=`candidate`。停止：证据冲突/失效、绝对效果、价格交期、批准人缺失、版本漂移。完成：所有对外断言有证据；候选标签明显；未写正式状态或下游白名单。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`object.get_version`、`claim.create_candidate`、`object.submit_review`、`human.escalate`。降级：仅形成“不可发布的假设+补证清单”。测试：PM03-T01正常；T02无证据；T03失效Fact；T04绝对化承诺；T05价格诱导；T06默认批准；T07对象漂移；T08送审失败。


