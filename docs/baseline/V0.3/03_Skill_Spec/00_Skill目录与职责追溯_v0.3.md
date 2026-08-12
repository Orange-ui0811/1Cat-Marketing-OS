# 三数字岗位 Skill 目录与职责追溯 v0.3

> 状态：`SKILL-CONTRACT-FREEZE-CANDIDATE`  
> 范围：5个共享Skill、23个岗位Skill，共28个；每个Skill独立版本化。  
> 边界：Skill是程序性知识，不授予Tool、数据或业务权限；本目录不是已安装Skill。

## 1. 统一版本与合同规则

- 初始规格版本均为`0.3.0-freeze-candidate`；身份以`skill_id + version`为准。
- 每次加载还必须绑定`role_id`、Manifest/SOUL版本、Commitment、对象版本、ContextSnapshot和权限快照。
- Major改变职责、人类保留权、数据/外部动作风险；Minor增加同职责方法；Patch不改变语义。Major回到岗位/组织评审。
- 激活顺序：规格批准→合成/脱敏离线评测→Shadow→Owner签署→有限激活。文件存在不等于已安装或激活。
- R0外部研究只接收人类提供的`SourceRef`；不得自行浏览、HTTP抓取或登录平台。
- Tool每次由Runtime按Role、Commitment、对象、动作、时间窗重新验权；Skill文本不能绕过策略。
- SKL-BG-07～11由用户提供的五个平台Playbook源包派生集成合同；源包按ZIP SHA-256锁定但未安装。SKL-BG-11视频号为禁用范围候选，不能因文件存在而激活。

## 2. 职责到Skill、产物与验收映射

| Skill | 职责/理由 | 主要产物 | 接收者 | 最小验收 |
|---|---|---|---|---|
| SKL-SH-01 | 全岗位证据纪律；CAP-02/03/09 | EvidenceNote | 当前岗位、审核人 | 分类、版本、支持/反证、未知和SourceRef齐全 |
| SKL-SH-02 | PMA/BGA/MO交接；CAP-08 | CommitmentResponse、RoleHandoff | 承诺请求者/下一责任人 | 对象、版本、证据、未完成和验收无歧义 |
| SKL-SH-03 | 全岗位风险与接管；GOV-06/10 | EscalationPacket、TakeoverPacket | 风险Owner/接管人 | 不安全动作停止、影响与恢复条件明确 |
| SKL-SH-04 | 全岗位人类决定准备；OBJ-09 | DecisionAgenda | 具名决策人 | 选项、证据、反证、风险和不决定后果齐全 |
| SKL-SH-05 | 全岗位自检与学习；CAP-09 | SelfCheckReport、LearningCandidate | 业务Owner | 边界/证据/版本/权限检查完成，未自动固化 |
| SKL-PM-01 | PMA-R01/R07；CAP-02 | ProductFactCandidate、ImpactFinding | 产品/R&D、产品营销Owner、BGA | 候选可追溯，影响对象版本明确，无Agent确认 |
| SKL-PM-02 | PMA-R02；CAP-03 | ResearchFinding | 产品营销Owner、PMA下游 | 回答问题，反证/局限/时效可见 |
| SKL-PM-03 | PMA-R03；CAP-03 | PositioningCandidate、ClaimCandidate | 公司负责人、产品/R&D | 价值-证据映射与禁止范围完整 |
| SKL-PM-04 | PMA-R04；CAP-03/04 | ProductAssetDraft | 产品营销Owner、BGA | 有效Fact/Claim引用、用途和审核点清楚 |
| SKL-PM-05 | PMA-R05；CAP-05 | ProductReviewPacket | 产品营销负责人、BGA | 针对不可变资产版本，问题逐项可定位 |
| SKL-PM-06 | PMA-R06；CAP-02 | EvidenceRequest | 产品/R&D接口Owner | 问题可回答、不过度索取、降级明确 |
| SKL-BG-01 | BGA-R01；CAP-04 | ChannelResearch | 品牌营销Owner | 时效、来源、机会、风险和验证建议齐全 |
| SKL-BG-02 | BGA-R02；CAP-04 | CampaignDraft | 品牌营销负责人 | 目标、Claim、依赖、预算边界与批准人齐全 |
| SKL-BG-03 | BGA-R03；CAP-04 | ContentMaster、PlatformVariant | 产品/品牌审核人 | 选择最小平台Skill，跨平台事实一致且保留原生结构 |
| SKL-BG-04 | BGA-R04/R05；CAP-05 | PublishPreparation、ManualPublishTask | 人类发布执行人、品牌Owner | R0无平台写，版本/批准/回执检查闭合 |
| SKL-BG-05 | BGA-R06/R07；CAP-06 | LeadStub、MergeProposal、SalesHandoff | 品牌Owner、销售接口 | 无明文PII、触点不丢、未知不强并/不推断 |
| SKL-BG-06 | BGA-R08；CAP-07/09 | AttributionCandidate、ExperimentReview | 品牌Owner、公司负责人 | 口径、局限、替代解释与销售来源明确 |
| SKL-BG-07 | BGA-R03；CAP-04；抖音 | Douyin PlatformVariant | 产品/品牌审核人 | 单一认知、Hook、证据、回报清楚；MANUAL |
| SKL-BG-08 | BGA-R03；CAP-04；小红书 | Xiaohongshu PlatformVariant | 产品/品牌审核人 | 需求/搜索、点击承诺、效用和收藏资产清楚；MANUAL |
| SKL-BG-09 | BGA-R03；CAP-04；B站 | Bilibili PlatformVariant | 产品/品牌审核人 | 起始知识、承诺理解、知识地图和证据计划清楚；MANUAL |
| SKL-BG-10 | BGA-R03；CAP-04；公众号 | Official Account PlatformVariant | 产品/品牌审核人 | 原创判断、论证、知识块、更新触发器清楚；MANUAL |
| SKL-BG-11 | BGA-R03；CAP-04；视频号候选 | Channels PlatformVariant | 产品/品牌审核人 | scope未批准时阻断；不读取关系图/PII，当前不激活 |
| SKL-OR-01 | MO-R01；CAP-01/08 | MissingFieldReport | 请求者、Brief Owner | 缺口/冲突/阻塞和补充Owner明确 |
| SKL-OR-02 | MO-R02；CAP-08 | CollaborationPlan、DependencyMap | 相关岗位/人类Owner | 专业责任不漂移，并行、依赖和决策点明确 |
| SKL-OR-03 | MO-R03；CAP-08 | CommitmentProposal/Response | 承诺岗位、请求者 | 接收者明确接受，修改与拒绝可追溯 |
| SKL-OR-04 | MO-R04/R05；CAP-08 | Reminder、EscalationPacket | 当前责任人/升级Owner | 去重、可行动、无默认批准、时限清楚 |
| SKL-OR-05 | MO-R06；GOV-06/07 | TakeoverPacket、ReconciliationPlan | 人工接管人、技术Owner | 已做/未做/未知、去重和恢复条件完整 |
| SKL-OR-06 | MO-R07/R08；CAP-09 | ReviewPacket、DecisionAgenda | 公司负责人、两名营销Owner | 专业结论来源明确，未替人类决定 |

反向检查结论：28个Skill均对应已确认职责、治理要求或用户提供的平台专业方法；新增五个Skill只细化BGA-R03，不增加Agent、Tool或平台权限。发布、批准、预算、外联、询盘判断、固定状态机、鉴权、幂等和审计不是Skill新增能力，分别保留给人类或Runtime/规则软件。

## 3. BGA平台Skill加载关系

`SKL-BG-03`是平台适配协调Skill；`SKL-BG-07～11`是按需加载的平台原生方法；`SKL-BG-04`是批准与人工发布准备。三层依赖固定为：

```text
SKL-BG-03 ContentMaster/选择平台
  ├─ SKL-BG-07 抖音
  ├─ SKL-BG-08 小红书
  ├─ SKL-BG-09 B站
  ├─ SKL-BG-10 公众号
  └─ SKL-BG-11 视频号（当前dormant）
        ↓
SKL-BG-04 人工审核/发布准备
```

任何平台Playbook都不能直接调用SKL-BG-04或产生发布状态；必须先返回BG-03的统一PlatformVariant候选并完成产品/品牌/合规审核。

## 4. 全局失败优先级

`PII/凭据/越权/批准失效` → 立即停止并使用SKL-SH-03；`版本冲突/来源不可核验` → 保持候选或等待并找Owner；`输入缺失` → 澄清；`Tool暂时失败且无外部副作用` → 仅按策略有限重试；`外部结果未知` → 禁止重试并转人工对账。
