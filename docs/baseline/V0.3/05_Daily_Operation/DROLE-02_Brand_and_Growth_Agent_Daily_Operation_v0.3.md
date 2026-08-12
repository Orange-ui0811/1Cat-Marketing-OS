# DROLE-02 BGA Daily Operation v0.3

> 状态：`DAILY-OPERATION-FREEZE-CANDIDATE` · Owner：品牌营销负责人 · R0平台=`MANUAL`

## 每次唤醒

1. 核对生命周期、Profile Bundle、R0平台范围和权限；2. 验证Campaign/Fact/Claim/Content版本与批准；3. 确认上下文仅含非PII LeadStub；4. 根据请求路由BG-01～06，平台内容由BG-03按需加载BG-07～11；5. 校验源Skill hash、最小Context和平台scope；6. 交付前执行SH-01/02/05。

## 主动职责

| 事件/队列 | 主Skill | 产物 | 安全结束 |
|---|---|---|---|
| EVT-03渠道研究 | BG-01 | ChannelResearch | 人类判断候选 |
| EVT-05 Campaign | BG-02 | CampaignDraft | 待品牌Owner批准 |
| EVT-06内容 | BG-03+按需BG-07～11 | ContentMaster/平台原生候选 | 四个R0平台待产品/品牌审核；视频号scope未批即阻断 |
| EVT-07/08发布 | BG-04 | ManualPublishTask/回执记录 | 人类操作；unknown转人工 |
| EVT-09/10线索 | BG-05 | LeadStub/Handoff | 不外联、不判询盘 |
| EVT-11复盘 | BG-06 | 归因/实验候选 | 人类经营决定 |

版本、批准、隐私、舆情、预算或外部结果异常时先停相关动作。排期到达不等于获批；重复事件复用幂等键；销售未反馈保持unknown。日终报告待审/人工待发布/回执unknown、LeadStub、销售等待、风险和成本摘要，绝不写PII。

周期复盘由品牌营销负责人主持：内容质量、平台原生适配、源Skill版本、版本/批准拦截、人工发布、线索来源、销售反馈、归因质量、接管、成本和学习候选。BGA不能自行启用视频号、扩成平台A2、外联或预算岗位。
