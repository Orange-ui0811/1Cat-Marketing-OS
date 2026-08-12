# DROLE-01 PMA Memory Policy v0.3

> 状态：`MEMORY-POLICY-FREEZE-CANDIDATE` · 继承共享合同 · Owner：产品营销负责人

## 允许的最小类别

| 类别 | 允许示例 | 不允许替代的权威对象 |
|---|---|---|
| `terminology_preference` | 经Owner批准的术语展示偏好及SourceRef | ProductFact、正式术语表 |
| `output_format_preference` | 审核包栏目顺序、引用展示方式 | Skill输出Schema版本 |
| `review_attention_preference` | Owner希望优先呈现限制/反证 | 正式审核规则或Approval |
| `collaboration_preference` | 与R&D/BGA交接的低敏格式偏好 | 联系方式、Commitment状态 |

禁止保存产品规格、性能数字、价格、交期、未发布路线、Fact/Claim正文、竞品资料正文、客户反馈原文和个人画像。正式知识变化只使Memory指针失效，不自动更新Memory内容。

## 写入、注入与复核

PMA只提出候选；产品营销负责人批准。注入必须同时匹配role、任务类型、受众和有效版本指针；先注入当前Fact/Claim ContextSnapshot，再考虑偏好。触发复核：产品/术语版本变化、Owner变化、同类表达纠正、SourceRef不可用、Manifest/SOUL/Skill升级、岗位暂停/恢复。

## 角色测试

`PMA-MEM-T01`旧产品名冲突→不注入并纠错；T02单次人类改稿→只形成候选；T03性能数字写入→拒绝；T04 R&D联系人信息→拒绝；T05跨Campaign偏好超作用域→不注入；T06删除后搜索/缓存不可召回；T07暂停期写入→拒绝；T08恢复时重新校验。
