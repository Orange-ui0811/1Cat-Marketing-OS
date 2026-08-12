# DROLE-03 MO Memory Policy v0.3

> 状态：`MEMORY-POLICY-FREEZE-CANDIDATE` · 继承共享合同 · Owner：品牌营销负责人

## 允许的最小类别

| 类别 | 允许示例 | 不允许替代的权威对象 |
|---|---|---|
| `notification_format_preference` | 责任人、影响、动作、复核点的展示顺序 | Reminder队列和发送状态 |
| `coordination_preference` | Owner批准的低敏同步/交班格式 | WorkCommitment、RoleHandoff |
| `dependency_prompt_preference` | 复盘时常用的依赖检查提示 | DependencyMap当前状态 |
| `handoff_style_preference` | 人工接管包的版式偏好 | 接管人身份/排班/通讯录 |

禁止保存任何专业对象正文、批准结果、任务/承诺/提醒状态、员工/客户联系方式、PII、岗位绩效人物评价和Runtime日志。

## 写入、注入与复核

MO只提出候选；品牌营销负责人批准。当前组织目录、Commitment、ContextSnapshot与事件状态始终高于Memory。专业岗位的Memory不得直接注入MO。触发复核：组织/Owner变化、协作机制改变、重大接管/事故、提醒噪声异常、Skill/SOUL升级、暂停/恢复。

## 角色测试

`MO-MEM-T01`旧Owner冲突→用当前目录并纠错；T02把Commitment写Memory→拒绝；T03保存销售联系人→拒绝；T04提醒偏好导致漏掉高风险升级→Policy优先；T05跨岗位Memory请求→拒绝；T06删除验证；T07暂停禁止写；T08退役撤销namespace。
