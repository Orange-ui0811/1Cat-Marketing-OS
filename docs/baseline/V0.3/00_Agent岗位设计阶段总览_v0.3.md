# S2 AI原生营销：Agent岗位设计阶段总览 v0.3

> 文档状态：`ROLE-DESIGN-FREEZE-CANDIDATE`  
> 设计模式：Hermes 数字岗位 `role-design + collaboration-design + handoff`  
> 形成日期：2026-08-11  
> 上游组织基线：`组织架构设计/V1.1/S2_AI原生营销组织架构方案_v1.1.md`  
> 上游业务交接：`组织架构设计/V1.1/S2_技术实现设计业务需求交接包_v0.1.md`  
> 上游技术基线：`技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md`  
> 上游UML基线：`技术方案设计/V1.1/S2_AI原生营销技术实现设计_UML配套图包_v1.1_冻结候选.md`  
> 替代关系：本目录是Agent岗位设计V0.2的完整冻结候选；V0.1、V0.2均保留不变。  
> 边界：形成可签署、可开发澄清、可测试和可入职评审的设计合同；不创建真实Profile，不安装Skill，不接入系统，不执行营销动作。

---

## 1. 固化结论

V0.3固定R0的三个长期数字岗位，不新增Reviewer Agent，也不把MO变成中央Workflow：

1. `DROLE-01` Product Marketing Agent（PMA），嵌入产品营销中心；
2. `DROLE-02` Brand & Growth Agent（BGA），嵌入品牌营销中心；
3. `DROLE-03` Marketing Orchestrator（MO），跨两个中心提供组织协作服务，由品牌营销负责人运营，不构成第三中心。

三个岗位之间是“一个组织协作岗位 + 两个专业岗位”的关系：MO理解目标、组织承诺、依赖、提醒、升级、接管和复盘；PMA与BGA分别对产品营销和品牌增长专业产物负责。Runtime只负责可靠投递、持久化、验权、执行协调和审计，不替MO规划协作，也不替专业岗位作判断。

本版把V0.2收敛为以下可签署基线：

- 三个Role Manifest、SOUL、Memory、日常运行、评价和Profile Bundle形成一一对应的岗位包；
- 保留原有5个共享Skill和18个岗位Skill，并把用户提供的5个平台Playbook作为BGA的SKL-BG-07～11纳入，合计28个独立、可版本化Skill合同；
- 固定10项公共合同，以及EVT-01～11路由和失败接管/恢复规则；
- 固定R0的MANUAL、MONITOR_ONLY、PII DISABLED和BASELINE_ONLY安全边界；
- 固定WorkCommitment、TaskAttempt/AgentRun、RoleHandoff、ApprovalGrant和Workspace之间的权威关系；
- 增加规范文件哈希清单、冻结签署包和Agent岗位UML配套图包。

`ROLE-DESIGN-FREEZE-CANDIDATE`只表示设计已收敛到可签署候选。它不表示上游技术设计已冻结，也不表示任何Agent、Runtime、Tool、Workspace、UAT、Shadow或业务结果已经实现。

## 2. 上游基线锁

| 上游制品 | 状态 | SHA-256 |
|---|---|---|
| 组织架构方案V1.1 | 上游组织基线 | `b15f046cac61ba21f47d64e519779e9566af906831a0e00e4d94e755de363e40` |
| 技术实现业务需求交接包v0.1 | 上游业务需求基线 | `e4bd375b05af99236299bffedf3959e8a66eef325bfffa6e1c401ec4f187816e` |
| 技术实现设计方案V1.1-R1 | `FREEZE-CANDIDATE-R1` | `6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a` |
| 技术实现设计UML图包V1.1-R1 | 冻结候选 | `4a3db32fd90ea2ecdc1d9af0698d92700f293d30a8ae9ba7bf944c6c48fe8942` |
| 技术设计冻结签署包v1.0 | `AWAITING-ORG-ALIGNMENT-AND-HUMAN-SIGNOFF` | `38b91c9f98ebe7bab10f4347aa8194ce75dff2b1a8eb0cc46f076ed8ec275fe6` |

以上哈希在2026-08-11校验一致。任一上游规范文件变化，V0.3必须先执行change-impact；旧签署不得自动继承。

### 2.1 本轮补充输入：五个平台Skill源包

| 源Skill | ZIP SHA-256 | 纳入方式 |
|---|---|---|
| `douyin-growth-playbook` | `1fe1e4dd44b000ddbf7326e22348b1c8add71977da6b0abc716219d3671a80f8` | SKL-BG-07；R0 MANUAL候选 |
| `xiaohongshu-growth-playbook` | `69638b446bf040a20c742db842bac0b0e18742b2a9220b6f9ce6efb4a8301fcc` | SKL-BG-08；R0 MANUAL候选 |
| `bilibili-growth-playbook` | `950344e3c9877d232a2c4dbca0db2886598e11be21d29e1e16bd508830461a72` | SKL-BG-09；R0 MANUAL候选 |
| `wechat-official-account-growth-playbook` | `b73c6fc1abf8508b1b9754ae2efc3300d3cfc2bde8e572a0d7803cfcfc22e7d0` | SKL-BG-10；R0 MANUAL候选 |
| `wechat-channels-growth-playbook` | `7a48e372bb3021d7ea80111650a2da1b3bf18425ae72abc40ce4ad2f8168b667` | SKL-BG-11；`DORMANT_SCOPE_CANDIDATE` |

这些是用户提供的程序性知识资产，不是上游组织/技术基线，也未安装到Hermes。完整集成规则见`03_Skill_Spec/BGA/00_五平台增长Skill集成目录_v0.3.md`。

## 3. 组织与岗位不变量

| ID | 不变量 | V0.3固定处理 |
|---|---|---|
| RD-I01 | 保留产品营销中心与品牌营销中心 | 不新建第三个营销中心 |
| RD-I02 | PMA属于产品营销中心 | 产品营销负责人是PMA业务Owner |
| RD-I03 | BGA属于品牌营销中心 | 品牌营销负责人是BGA业务Owner |
| RD-I04 | MO跨两个中心服务 | 品牌营销负责人运营；MO不是专业上级、审批者或第三中心 |
| RD-I05 | 人类保留最终责任 | 目标、事实、正式Claim、预算、内容批准、平台执行、外联、询盘和经营判断均由具名人类承担 |
| RD-I06 | R0四平台为MANUAL | BGA只准备不可变人工发布任务并登记人类回执 |
| RD-I07 | R0真实PII关闭 | 只处理无明文PII的LeadStub和不透明SourceRef |
| RD-I08 | Agent是岗位，Runtime是支撑 | MO负责业务协作；Runtime负责确定性控制和可靠运行 |
| RD-I09 | 三岗位使用独立Hermes profile | profile不是安全边界；仍需独立服务身份、网络隔离和Tool逐次验权 |
| RD-I10 | 设计、实例与运行状态分离 | `freeze_candidate / defined / not_created`不得混写为已入职或上线 |

## 4. 岗位拆分决定与变更触发器

R0不继续拆分三个岗位。Skill、短期Delegate、规则校验器、Runtime组件和人工审核人都不等于新数字岗位。

新增或拆分岗位属于Major组织与Agent设计变更，至少需要同时满足：

1. 出现持续、可观测的独立任务量或明显并行收益；
2. 新职责与现岗位在目标、知识、数据、行动权限、风险、独立制衡或评价上至少两至三项稳定不同；
3. 有独立且具名的人类业务Owner；
4. 有单独评估集、运行指标、异常接管能力和Profile/权限边界；
5. 完成组织一致性、权限、数据、成本和变更影响评审。

BGA是最可能在后续拆分的岗位，但本版不预先拆分。当真实PII进入范围、平台A2形成独立高风险执行域、内容与增长出现不同Owner，或两类工作量/评价目标已明显分离时，重新评估拆为`Brand Content Agent`与`Growth Operations Agent`。PMA与MO当前没有足够证据继续拆分。

## 5. V0.3规范制品

| 目录 | 规范制品 | 评审重点 |
|---|---|---|
| `01_Role_Manifest/` | 三岗位Manifest | 使命、Owner、职责、事件、数据、权限、指标、升级、生命周期 |
| `02_SOUL/` | 三岗位稳定身份与对抗边界 | 角色一致、默认批准、越权、PII诱导、事实冲突 |
| `03_Skill_Spec/` | 28个Skill合同与职责追溯 | 触发/不触发、输入输出、停止、人工判断、Tool、测试、源包hash |
| `04_Memory_Policy/` | 共享合同与三岗位差异策略 | 注入、冲突、删除、暂停、接管和退役 |
| `05_Daily_Operation/` | 共享运行公约与岗位节奏 | 事件、承诺、履职、交接、等待、升级、接管、复盘 |
| `06_Evaluation/` | 生命周期、任用、指标与测试目录 | 硬门、baseline、Shadow、UAT、扩权和周期任用 |
| `07_Tool_Permission/` | 数据/权限总表与三岗位allowlist | role/profile/identity/commitment验权、R0禁区、幂等与审计 |
| `08_Collaboration_Protocol/` | 10项公共合同、EVT路由与恢复协议 | 权威源、状态、批准、Workspace、连续性和跨岗位一致性 |
| `09_Implementation_Handoff/` | Profile Bundle、路线、追踪、UML、签署和哈希 | Hermes映射、开发接手、固化条件和证据状态 |

10项公共合同固定为：DigitalRoleManifest、OrganizationEventSubscription、WorkCommitment、RoleHandoff、ContextSnapshot、ToolCapabilityPolicy、ApprovalGrant、AgentRun/TaskAttempt、StructuredOutputSchema、HumanCollaborationWorkspace。`EVT路由矩阵`和`失败接管与恢复协议`是跨场景规则，不另建事实源。

## 6. 权威关系

| 内容 | 唯一权威/控制关系 | 明确不是事实源 |
|---|---|---|
| 岗位使命、Owner、职责、指标、生命周期 | DigitalRoleManifest + 人类签署 | SOUL、动态任务、运行进程 |
| 组织承诺及公共状态 | ORS-03 Work Commitment Ledger | Hermes Kanban、Workspace卡片、Session |
| 人类业务批准 | 具名人类签发的ApprovalGrant | Agent文本、评论、Hermes `approvals.mode` |
| 业务对象和正式状态 | 上游权威业务载体 | Agent输出、Memory、日志 |
| 一次运行技术证据 | TaskAttempt/AgentRun与Tool/Audit记录 | 业务完成或人类验收 |
| 最小运行上下文 | 不可变ContextSnapshot | Memory或业务原件副本 |
| 人类协作入口 | Human Collaboration Workspace经ORS写入 | 第二套工作流或数据库 |
| 岗位工作表面 | Hermes Kanban只读、可重建投影 | 双向同步或状态写入口 |

## 7. DEC-01～08冻结处置与激活门

下表的“安全处置”可以被签署为设计决定；它不代表未来Connector、PII、SLA或自动化能力已经建成。

| DEC | V0.3冻结候选中的安全处置 | 后续激活门 |
|---|---|---|
| DEC-01 有效询盘 | 状态固定为`pending/valid/invalid/needs_more_info`，只有销售身份可写并使用版本化原因码；Agent不判断 | BGA有效询盘指标启用前，销售与品牌Owner签署口径版本 |
| DEC-02 销售反馈时限 | R0=`MONITOR_ONLY`；MO只准备提醒/升级候选，未签时限不自动外发且不虚构SLA | 自动提醒启用前绑定时限、渠道、升级策略和Owner版本 |
| DEC-03 高影响内容 | 未分类外部内容默认要求公司负责人额外ApprovalGrant；价格、促销、交期、客户承诺、新Claim、法律/隐私和舆情不得降级 | BGA Shadow即执行保守门；任何A2前完成分类规则与测试 |
| DEC-04 四平台连接 | 抖音、小红书、B站、公众号全部`MANUAL` | A2按平台+账号+动作分别完成官方能力、IAM、幂等、回执、熔断和Canary |
| DEC-05 权威载体 | 使用Source Registry过渡；默认`authority=unknown/manual_reference`，不虚构Connector | 每项真实输入激活前绑定权威载体、Owner和可核验SourceRef |
| DEC-06 个人信息 | R0真实PII=`DISABLED`，Context/Memory/Session/日志均fail-closed | 另行确认合法用途、最小字段、保留、删除、Owner、Adapter/Vault和隐私Canary |
| DEC-07 技术责任人 | 必须具名并由本人接受设计、实现偏差、安全、证据和事故责任 | Agent岗位设计登记冻结的硬门；未关闭不得改为FROZEN |
| DEC-08 基线与成本 | R0=`BASELINE_ONLY`；只定义公式、采样和证据，不虚构阈值/SLA | `shadow→active_limited`前批准岗位阈值、容量、成本和连续失败策略 |

当前DEC-01～08均尚未完成人类签署。V0.3可以作为冻结候选进入签署，但不能登记`ROLE-DESIGN-FROZEN`。

## 8. 事实、假设与开放项

### 8.1 已确认事实

- 当前营销团队由两个中心及各自人类负责人构成；
- 上游已批准的R0渠道为抖音、小红书、B站和公众号；本版新增视频号Playbook设计候选，但其平台范围尚未批准并保持dormant；
- 品牌营销负责人是营销任务到原始线索移交的日常流程Owner；
- 销售负责有效询盘、商机、报价、谈判和成交判断；
- R0只设计人工发布和不含PII的LeadStub闭环。

### 8.2 设计假设

| ID | 假设 | 错误时影响 | 验证Owner |
|---|---|---|---|
| RD-ASM-01 | 上游组织V1.1和技术V1.1-R1在本轮不改变 | 岗位使命、接口和授权需执行Major change-impact | 公司负责人、两名营销负责人 |
| RD-ASM-02 | 三岗位可用受控SourceRef完成合成/脱敏离线评测 | Skill不能进入Shadow准备 | 业务Owner、技术Owner |
| RD-ASM-03 | Runtime能够提供独立身份、对象版本、Commitment和审计能力 | Profile不能安全履职或恢复 | 具名人类技术Owner |
| RD-ASM-04 | 两名营销负责人能够承担日常复核、异常接管和周期任用 | 自主等级需降低或增加人类支持 | 公司负责人 |

### 8.3 仍需关闭

| ID | 影响 | 当前安全状态 | 关闭Owner |
|---|---|---|---|
| DEC-01～08 | 见第7节 | 使用对应保守处置，不推断签署 | 各DEC列明的人类签署人 |
| RD-OPEN-05 | 替补、排班和升级通讯录未形成，阻塞岗位入职 | 使用角色名；不承诺具体响应时限 | 公司负责人、两岗位Owner |
| RD-OPEN-06 | Connector、IAM、回执和熔断未验证，阻塞A2 | 四平台MANUAL | 品牌Owner、具名技术Owner |
| RD-OPEN-07 | 视频号不在上游四平台范围，阻塞SKL-BG-11激活 | 只纳入设计/离线候选，Profile active allowlist排除 | 公司负责人、品牌营销负责人 |
| PLAT-SKL-OPEN-01 | 五个源包缺独立版本、企业Owner、许可证/权属依据、导入清单和正式测试，阻塞安装与onboarding | 只保留设计合同和源哈希；不安装、不加载真实Profile | 公司负责人/内容资产Owner、具名技术Owner |

## 9. 设计冻结门与运行门

| Gate | 通过条件 | 当前状态 |
|---|---|---|
| RD-G0 上游锁定 | 上游五份规范哈希一致，冲突已记录 | 已完成文档校验 |
| RD-G1 制品完整 | 三岗位包、28个Skill、10项合同、UML、追踪和哈希清单无断链 | 待最终静态验收记录 |
| RD-G2 业务一致性 | 公司、两中心、R&D和销售确认岗位、人类保留权及DEC-01～06/08安全处置 | 待人类签署 |
| RD-G3 技术与风险签署 | DEC-07具名；技术、数据/隐私和风险责任人接受合同与残余风险 | 未通过 |
| RD-G4 `ROLE-DESIGN-FROZEN` | 规范清单哈希锁定，所有必签人接受，无未回写修改 | 未通过 |
| RD-G5 开发授权 | 冻结设计另获实施授权和开发接收 | 未授权 |
| RD-G6 离线评测 | 合成/脱敏正常、边界、拒绝、风险和恢复场景有证据 | 未开始 |
| RD-G7 Shadow | 三岗位跟随真实去敏工作，所有产物由人类复核 | 未开始 |
| RD-G8 Limited Active | DEC-01～03/05～08相关门、UAT、接管和人工连续性通过 | 未开始 |
| RD-G9 Extended Authority | 单项A2按平台+账号+动作分别Canary | 不属于R0 |

设计冻结、开发授权、岗位入职和运行上线是四个不同决定，任何一个不得由前一个自动推导。

## 10. 本版不授权

- 不创建或修改Hermes profile、SOUL运行文件、Skill安装目录、Memory、Cron或A2A；
- 不开发或连接Runtime、MCP、Workspace、数据库、Connector、身份或基础设施；
- 不读取、复制或写入真实产品、平台、Lead、客户、销售、PII或凭据数据；
- 不对外发布、联系客户、调整预算、判断询盘或批准任何业务对象；
- 不把本目录状态改为`FROZEN`，不声称Agent已入职、上线、通过UAT或达到L3。

## 11. 推荐签署顺序

1. 公司负责人确认三岗位拓扑、人类保留权和拆分触发器；
2. 产品营销负责人及产品/R&D负责人评审PMA与事实边界；
3. 品牌营销负责人评审BGA、MO、Workspace和跨岗位协议；
4. 销售负责人评审LeadStub、DEC-01/02和反馈指标；
5. 数据/隐私责任人评审PII、Memory、删除和审计边界；
6. 具名技术Owner接受DEC-07并评审Hermes、Tool、Profile Bundle、Runtime合同和规范哈希；
7. 所有修改回写后重新生成哈希清单，再由必签人签署冻结决定。
