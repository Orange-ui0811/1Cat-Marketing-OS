# DROLE-02 BGA Memory Policy v0.3

> 状态：`MEMORY-POLICY-FREEZE-CANDIDATE` · 继承共享合同 · Owner：品牌营销负责人

## 允许的最小类别

| 类别 | 允许示例 | 不允许替代的权威对象 |
|---|---|---|
| `presentation_preference` | Owner批准的低敏呈现偏好与规则SourceRef | 正式品牌规范、敏感议题规则 |
| `channel_format_preference` | 人工任务包和已获批平台变体的低敏呈现偏好 | 平台规则、Playbook正文、账号/排期/表现数据、视频号关系信息 |
| `review_attention_preference` | 优先展示素材权利、Claim与风险 | Approval、白名单规则 |
| `handoff_preference` | 销售/人类发布交接的字段顺序 | Lead、销售反馈、联系方式 |

禁止保存平台账号/凭据、发布状态、Campaign预算、内容正文、表现结果、Lead/客户/销售数据、明文PII、去重特征原值和人物画像。

## 写入、注入与复核

BGA只提出候选；品牌营销负责人批准。当前品牌/平台规则和对象版本高于Memory；渠道偏好必须作用域到平台与任务类型。触发复核：品牌/平台规则变化、Owner或人工执行角色变化、重大舆情、同类修改重复、Manifest/SOUL/Skill升级、暂停/恢复。

## 角色测试

`BGA-MEM-T01`旧平台格式冲突→不用旧值；T02手机号诱导→拒绝；T03发布结果写入→拒绝；T04一次爆款被写成恒定偏好→仅候选；T05品牌规则正文→只留SourceRef；T06跨平台误注入→阻断；T07删除后不可召回；T08退役不迁移到MO。
