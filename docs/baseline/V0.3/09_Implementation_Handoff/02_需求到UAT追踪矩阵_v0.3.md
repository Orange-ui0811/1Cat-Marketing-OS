# 需求→岗位→Skill/Tool/Memory→Hermes机制→UAT追踪矩阵 v0.3

> `role_design_status: ROLE-DESIGN-FREEZE-CANDIDATE`  
> 证据状态：本文只记录`planned`（计划证据）和`design_covered`（设计覆盖）；尚无`executed/passed/production`证据。

## 1. 追踪语法与十项合同

| 简写 | 合同ID | 用于追踪的核心证据 |
|---|---|---|
| DM | `IF-DROLE-MANIFEST-01` | 岗位身份、Owner、职责、指标、禁区、生命周期和Bundle |
| EVT | `IF-EVENT-SUB-01` | 订阅、去重、投递、死信和升级 |
| WC | `IF-WORK-COMMITMENT-01` | 目标、请求者/承诺者、依赖、输出、验收和公共状态 |
| RH | `IF-ROLE-HANDOFF-01` | 对象版本、证据、完成检查、退回和下一责任人 |
| CTX | `IF-CONTEXT-SNAPSHOT-01` | 单次Attempt最小、不可变、可过期上下文 |
| TCP | `IF-TOOL-CAP-POLICY-01` | role/profile/service identity/commitment/object/action/window验权和Tool返回 |
| AG | `IF-APPROVAL-GRANT-01` | 具名人类、对象版本/hash、动作、范围、撤销和单次消费 |
| RUN | `IF-AGENT-RUN-01` | AgentRun/TaskAttempt、预算、幂等、unknown、校验和恢复 |
| SCH | `IF-OUTPUT-SCHEMA-01` | 统一Envelope、岗位产物Schema、校验和兼容性 |
| WS | `IF-HUMAN-WORKSPACE-01` | 两个中心、Owner 1:1、审批、人工任务、销售反馈、评价和接管 |

`ORS-03 Work Commitment Ledger`是WC及公共状态的唯一事实源；Hermes Kanban和WS卡片只是从ORS-03生成的只读、可重建投影。

## 2. CAP追踪

| 需求 | 岗位/人类Owner | Skill与结构化产物 | Tool/数据/Memory边界 | 公共合同→Hermes/支撑机制 | 计划UAT/Workspace证据 |
|---|---|---|---|---|---|
| CAP-01 任务与目标 | MO组织；公司负责人/业务Owner决定 | OR-01/02/03；MissingFieldReport、CollaborationPlan、CommitmentProposal | event/object/approval元数据只读；无业务状态Memory | DM+EVT+WC+CTX+RUN+SCH+WS → MO Profile/Loop/ORS-02/03/05 | UAT-01、R02/03；委派资格、澄清/拒绝、Owner 1:1 |
| CAP-02 事实/Claim治理 | PMA履职；R&D/产品营销/公司人类确认 | PM-01/03/06、SH-01/04；EvidenceNote、Fact/ClaimCandidate、EvidenceRequest | DATA-02/03/05按SourceRef只读；只写候选；不存事实Memory | DM+WC+RH+CTX+TCP+AG+RUN+SCH+WS → PMA Profile/Skill/Knowledge Hub | UAT-02/03/05、R05；产品Workspace审核/补证/版本退回 |
| CAP-03 研究/定位 | PMA；产品营销Owner验收 | PM-02/03；ResearchFinding、Positioning/ClaimCandidate | 人工提供SourceRef；候选Tool；仅低敏偏好Memory | DM+WC+CTX+TCP+RUN+SCH+WS → PMA Loop；有限只读Delegate可选 | UAT-04、R04/07；研究反证、来源失效和人工退回 |
| CAP-04 Campaign/内容 | BGA主责；PMA提供产品资产；品牌Owner验收 | BG-02/03、PM-04/05；按需使用BG-07～10的抖音/小红书/B站/公众号方法；CampaignDraft、ContentMaster、ChannelVariant/PlatformVariant、ProductReviewPacket；BG-11仅dormant设计候选 | DATA-05～07；候选/送审；不存正文Memory；BG-07～11不新增Tool/Connector，当前均未安装 | DM+EVT+WC+RH+CTX+TCP+RUN+SCH+WS → 两Profile+持久交接；BG-07～10按源名+ZIP SHA-256锁定、R0 MANUAL；BG-11从active allowlist/Shadow排除 | UAT-05、R07/08；跨中心Workspace、差异修改和Handoff退回；四平台事实一致/原生结构/源hash负例；BG-11 scope gate |
| CAP-05 审批/发布控制 | PMA/BGA只准备；具名人类批准/发布 | PM-05、BG-03/04；ReviewPacket、PublishPreparation、ManualPublishTask/Receipt | version/hash/approval只读；R0平台写为空 | WC+RH+CTX+TCP+AG+RUN+SCH+WS → Policy Gateway/OIDC/人工任务 | UAT-03/05/06/07、R02/09；未分类内容额外Grant、撤销、人工回执 |
| CAP-06 Lead/销售移交 | BGA准备；品牌Owner/销售负责 | BG-05；LeadStub、MergeProposal、SalesHandoff | 仅去敏DATA-09/不透明ref；确定性去重规则；Memory禁Lead | DM+EVT+WC+RH+CTX+TCP+RUN+SCH+WS → BGA Profile+规则软件+持久Handoff | UAT-08/09、R04/08；LeadStub可见、PII隐藏、销售接收/退回 |
| CAP-07 销售反馈/归因 | BGA分析、MO组织提醒；只有销售判断 | BG-05/06、OR-04/06；AttributionCandidate、ExperimentReview、Reminder/ReviewPacket | DATA-10必须引用销售明确状态/原因码；无推断/无Memory | EVT+WC+CTX+TCP+RUN+SCH+WS → Profiles+Sales Workspace+MONITOR_ONLY | UAT-10/11/13、R07；销售写权、unknown保留、提醒候选人工确认 |
| CAP-08 编排/接管 | MO负责业务协作；Runtime负责可靠投递/持久化/验权/审计 | OR-01～05、SH-02/03；DependencyMap、Reminder、Escalation/Takeover/Reconciliation | Commitment/Inbox/audit元数据；仅协作偏好Memory | DM+EVT+WC+RH+CTX+TCP+RUN+SCH+WS → MO Profile+ORS-02/03/05/11；Kanban只读投影 | UAT-01/06/07/11/12/14、R06/08～10；三岗位/运行时中断、人工连续、恢复对账 |
| CAP-09 知识/决策闭环 | 三岗位只提候选；人类Owner决定 | SH-04/05、BG-06、OR-06；DecisionAgenda、ReviewPacket、MemoryCandidate | DATA-11/12候选/审计；Memory写入需人工批准 | DM+RH+CTX+TCP+AG+RUN+SCH+WS → ORS-07 Knowledge Hub + ORS-10 Review + 人类决策 | UAT-13/15、R07/10；人工修改历史、学习候选批准/删除 |

### 2.1 BGA平台Playbook源锁与激活追踪

权威设计目录：`03_Skill_Spec/BGA/00_五平台增长Skill集成目录_v0.3.md@0.3.0-freeze-candidate`。五包`.generated`均声明`repo_version=0.7.0`，但共同库内容不是同一份，必须按三组`content_hash`校验：抖音/公众号=`f07dcc50d2cfa129834194774175a9f1ae663b2e8a248485d6ce9f3d8188dea8`，小红书/B站=`fbd4e4c979a55aeaf5852579f3ae41c9d06d7c7b4969c333228c182d8e58aea4`，视频号=`36dfcc37409f60b9bd98bfa0dc2eb60808986cf3b459d03486b3d2e9784fe0b6`；不得用一个包的hash替代其他包。

| Skill | 源名 + ZIP SHA-256 | 当前状态 | 追踪门 |
|---|---|---|---|
| SKL-BG-07 | `douyin-growth-playbook` + `1fe1e4dd44b000ddbf7326e22348b1c8add71977da6b0abc716219d3671a80f8` | `design_candidate / not_installed / R0_MANUAL` | 仅经源hash复核、正式版本分配、离线评测后才可候选进BGA allowlist |
| SKL-BG-08 | `xiaohongshu-growth-playbook` + `69638b446bf040a20c742db842bac0b0e18742b2a9220b6f9ce6efb4a8301fcc` | `design_candidate / not_installed / R0_MANUAL` | 同上 |
| SKL-BG-09 | `bilibili-growth-playbook` + `950344e3c9877d232a2c4dbca0db2886598e11be21d29e1e16bd508830461a72` | `design_candidate / not_installed / R0_MANUAL` | 同上 |
| SKL-BG-10 | `wechat-official-account-growth-playbook` + `b73c6fc1abf8508b1b9754ae2efc3300d3cfc2bde8e572a0d7803cfcfc22e7d0` | `design_candidate / not_installed / R0_MANUAL` | 同上 |
| SKL-BG-11 | `wechat-channels-growth-playbook` + `7a48e372bb3021d7ea80111650a2da1b3bf18425ae72abc40ce4ad2f8168b667` | `DORMANT_SCOPE_CANDIDATE / not_installed` | 视频号不在上游四平台范围；只可做scope gate离线负例，不得进active allowlist、真实任务或Shadow |

五项Skill均只输出`OUT-BG-04 ChannelVariant/PlatformVariant`候选；源包的`publish_ready`只能映射为质量门候选，不表示批准或可发布。

## 3. GOV追踪

| GOV | 设计控制点 | 主要合同/机制 | 计划证据 |
|---|---|---|---|
| GOV-01 正式状态由人类 | Tool Policy禁止Agent批准；Grant仅具名人类签发 | DM+TCP+AG+SCH+WS | UAT-03/12、R02；管理员口吻/Hermes批准模式伪造被拒 |
| GOV-02 候选/正式分离 | Schema Envelope只允许candidate/draft/submitted | SCH+TCP+RH | UAT-04、R01；正式状态字段拒绝 |
| GOV-03 上游失效传播 | EVT与ImpactFinding带对象版本 | EVT+RH+CTX+SCH | UAT-02/05、R05；下游暂停/重审 |
| GOV-04 白名单可撤销 | ApprovalGrant绑定asset version/hash/action，执行前复核 | AG+TCP+WS | UAT-03/05；过期/撤销/重复消费拒绝 |
| GOV-05 重试不重复 | 事件去重、业务幂等、unknown禁重试 | EVT+TCP+RUN | UAT-07、R09；重复回调/外部结果unknown |
| GOV-06 暂停撤权接管 | Policy deny、新Context/新Attempt、Workspace接管 | DM+WC+CTX+TCP+RUN+WS | UAT-12/14、R10；暂停后Tool拒绝/人工连续 |
| GOV-07 全人工回退 | TakeoverPacket、人工队列、恢复对账 | WC+RH+RUN+SCH+WS | UAT-06/14、R10；导出无PII接管包/恢复不覆盖 |
| GOV-08 销售unknown保护 | 只有销售写四状态/原因码；Agent不推断 | TCP+SCH+WS | UAT-11；缺反馈保持pending/needs_more_info |
| GOV-09 全链路追溯 | correlation/causation、Bundle/对象/批准/Attempt/Tool/人工修改引用 | 十合同全部 | UAT-15、R08/10；从UAT反向定位上游hash |
| GOV-10 高风险升级 | SOUL/Skill检测，DM升级矩阵和WS具名Owner | DM+EVT+WC+RH+WS | UAT-12、R03/04；安全停止与升级包 |
| GOV-11 最小权限 | 不可变Context+七维Tool验权+独立服务身份 | DM+CTX+TCP+RUN | UAT-12、R01/03；错profile/冒用身份/对象越界 |
| GOV-12 纠错保留历史 | version/supersedes、Handoff return、人工修改差异 | RH+SCH+WS | UAT-15、R08；旧版不被覆盖 |

## 4. NFR追踪

| NFR | 设计要求 | 合同/机制 | 计划证据 |
|---|---|---|---|
| NFR-01 可追溯 | 来源/版本/Owner/批准/Run/Tool/人工修改关联 | 十合同+审计 | UAT-15 |
| NFR-02 可恢复 | 持久状态、新Context/新Attempt、人工队列和恢复对账 | WC+RH+CTX+RUN+WS+ORS-11 | UAT-06/14、R10 |
| NFR-03 结果一致 | 业务幂等、重复事件去重、unknown保护 | EVT+TCP+RUN | UAT-07、R09 |
| NFR-04 响应时效 | 可配置复核点/提醒/升级；DEC-02 MONITOR_ONLY；DEC-08前不编造时限 | EVT+WC+WS | Shadow超时场景执行证据（待） |
| NFR-05 权限控制 | role+profile+service identity+commitment+object+action+window | DM+CTX+TCP+AG+RUN | UAT-12、R03 |
| NFR-06 人工接管 | 停止、撤权、改派、纠正、恢复 | DM+WC+RH+TCP+RUN+WS | UAT-12/14、R10 |
| NFR-07 数据质量 | 缺失/冲突/过期/authority unknown/外部结果unknown显式 | CTX+SCH+Source Registry+ORS-07 | UAT-02/09/11、R05 |
| NFR-08 隐私/保留 | R0真实PII DISABLED；Memory/Context/Session/日志fail-closed；保留期待DEC-06 | CTX+TCP+SCH+WS+Memory Policy | R04+注入/脱敏/删除验证（待） |
| NFR-09 可观察 | 成功/失败/退回/人工修改/接管/成本/异常 | RUN+TCP+WS+审计+ORS-10 | Shadow实际运行证据（待） |
| NFR-10 成本边界 | 按岗位/Capability/Skill/Campaign归集；阈值待DEC-08 | RUN+Model Gateway+Evaluation+ORS-10 | Shadow成本基线（待） |
| NFR-11 峰值承载 | 业务量、队列、瓶颈和人工降级先采baseline | EVT+RUN+WS+ORS-10/11 | 峰值/积压/人工降级执行证据（待） |
| NFR-12 业务连续 | 单岗位、三岗位或Runtime停止仍有两个人类中心最小闭环 | WC+RH+RUN+WS+ORS-11 | UAT-14、R10 |

## 5. DEC-01～08追踪

| DEC | 设计锁定 | 影响对象 | 计划验证 |
|---|---|---|---|
| DEC-01 | `pending/valid/invalid/needs_more_info`；只有销售写；原因码版本化 | BGA Schema/Tool、Sales Workspace、增长指标 | 非销售写入拒绝；Agent不推断；指标只引用销售明确反馈 |
| DEC-02 | R0 `MONITOR_ONLY` | MO OR-04、EVT-10、Workspace提醒 | 只准备候选；未签时限不自动外发/不造SLA |
| DEC-03 | 未分类外部内容需公司负责人额外Grant | BGA BG-03/04、AG、Policy/Workspace | 缺额外Grant、版本/hash变化或撤销时fail-closed |
| DEC-04 | R0四平台 `MANUAL` | BGA Tool allowlist、ManualPublishTask | R0无Connector写；未签仅阻塞A2，不阻塞MANUAL A1/A3 |
| DEC-05 | Source Registry；`authority=unknown/manual_reference` | Context、PMA/BGA来源、Knowledge Hub | unknown不冒充权威；真实Connector未授权时不读取 |
| DEC-06 | R0真实PII `DISABLED` | 全Profile/Context/Memory/Session/日志、Lead | PII注入拒绝；只显示LeadStub/不透明SourceRef |
| DEC-07 | 具名人类技术Owner硬门 | 冻结、实施、安全、变更、事故 | 未具名时不得登记冻结/进onboarding |
| DEC-08 | `BASELINE_ONLY`；不编造SLA/阈值/容量/成本上限 | Evaluation、Run budget、提醒/连续失败、阶段门 | Shadow采baseline；人类批准阈值前不进`active_limited` |

## 6. Profile Bundle与岗位UAT路由

| Bundle | 锁定设计 | 适用证据路由 |
|---|---|---|
| PB-DROLE-01 PMA | DM/SOUL/SH+PM Skill/Memory/Tool/Event/10合同/SCH/RUN/WS/Evaluation/Lifecycle/Network | UAT-02/03/04/05/12/14/15 + PMA-SR-01～10 + SH/PM Skill测试 |
| PB-DROLE-02 BGA | DM/SOUL/SH+BG-01～11 Skill/Memory/Tool/Event/10合同/SCH/RUN/WS/Evaluation/Lifecycle/Network；BG-07～10源hash锁定但当前未安装、R0 MANUAL；BG-11=`DORMANT_SCOPE_CANDIDATE`并从active allowlist/Shadow排除 | UAT-03～15 + BGA-SR-01～10 + SH/BG Skill测试 + 四平台集成合同测试 + BG-11 scope gate |
| PB-DROLE-03 MO | DM/SOUL/SH+OR Skill/Memory/Tool/Event/10合同/SCH/RUN/WS/Evaluation/Lifecycle/Network | UAT-01/06/07/11/12/14/15 + MO-SR-01～10 + SH/OR Skill测试 |

三Bundle共用Workspace UAT：两个中心隔离/跨中心协作、Owner 1:1、委派资格、批准身份/对象/hash、Handoff退回、人工发布回执、销售反馈、PII隐藏、岗位暂停、三岗位全停、Runtime中断、恢复对账、Kanban只读、共享身份拒绝和全链路审计。

## 7. 实现后证据回填门

开发团队必须在此追踪模型后回填：`implementation_component, source_commit_or_artifact_version, test_execution_id, evidence_location, environment, result, executed_by, executed_at, defect_or_gap, gap_owner, residual_risk`。没有可复现的实际证据时，只能标`planned/design_covered`，不能标`passed`。

任何Tool、外部写权限、Profile、Memory写入、Cron或A2A peer若不能反向追溯到明确CAP/GOV/NFR、岗位职责、人类Owner和计划验证，默认不进入实现范围。
