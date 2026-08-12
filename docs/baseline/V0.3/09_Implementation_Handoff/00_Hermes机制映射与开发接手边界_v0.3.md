# Hermes机制映射与开发接手边界 v0.3

> `role_design_status: ROLE-DESIGN-FREEZE-CANDIDATE`  
> 交接性质：可供签署、估算和开发澄清的技术需求基线；不是已实现、已测试或已上线证明。  
> 本文不创建Profile、SOUL、Skill、Memory、MCP、Runtime、平台连接或真实数据访问。

## 1. 锁定上游与Hermes基线

Hermes实现基线固定为 `Hermes Agent v0.20.0`，tag `v2026.8.3`，commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb`。开发开始前由DEC-07指定的具名技术Owner再核验机制与API映射；未核验不得静默更换版本。

| 锁定上游 | SHA-256 | 用途 |
|---|---|---|
| `组织架构设计/V1.1/S2_AI原生营销组织架构方案_v1.1.md` | `b15f046cac61ba21f47d64e519779e9566af906831a0e00e4d94e755de363e40` | 两个中心、三岗位拓扑与人类责任 |
| `组织架构设计/V1.1/S2_技术实现设计业务需求交接包_v0.1.md` | `e4bd375b05af99236299bffedf3959e8a66eef325bfffa6e1c401ec4f187816e` | CAP/GOV/NFR/UAT与DEC业务基线 |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md` | `6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a` | 五层架构、ORS、Hermes与安全基线 |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计_UML配套图包_v1.1_冻结候选.md` | `4a3db32fd90ea2ecdc1d9af0698d92700f293d30a8ae9ba7bf944c6c48fe8942` | 跨视图结构和状态基线 |
| `技术方案设计/V1.1/S2_技术设计冻结决策签署包_v1.0.md` | `38b91c9f98ebe7bab10f4347aa8194ce75dff2b1a8eb0cc46f076ed8ec275fe6` | DEC-01～08与人类签署入口 |

任一上游文件的路径、内容或hash变化都触发change-impact，不能沿用本候选包的签署结论。

## 2. 十项公共合同与权威语义

| 合同ID | 合同 | 开发不可改义的语义 |
|---|---|---|
| `IF-DROLE-MANIFEST-01` | DigitalRoleManifest | 岗位身份、Owner、职责、能力、权限、指标、生命周期和版本组合 |
| `IF-EVENT-SUB-01` | OrganizationEventSubscription | EVT订阅、相关性、投递、去重、死信与升级 |
| `IF-WORK-COMMITMENT-01` | WorkCommitment | 请求者与承诺岗位对目标、边界、产物和验收的显式协定 |
| `IF-ROLE-HANDOFF-01` | RoleHandoff | 带对象版本、证据、完成检查和残余风险的正式交接 |
| `IF-CONTEXT-SNAPSHOT-01` | ContextSnapshot | 单次Attempt允许注入的最小、不可变、可过期上下文 |
| `IF-TOOL-CAP-POLICY-01` | ToolCapabilityPolicy | `role + profile + service identity + commitment + object + action + time-window`逐次验权 |
| `IF-APPROVAL-GRANT-01` | ApprovalGrant | 具名人类对确定对象版本/hash和动作的可撤销、限时、默认单次授权 |
| `IF-AGENT-RUN-01` | AgentRun/TaskAttempt | WorkCommitment到Hermes async `/v1/runs`的执行、预算、验证和恢复证据 |
| `IF-OUTPUT-SCHEMA-01` | StructuredOutputSchema | 三岗位产物Envelope、结构校验、版本和兼容性 |
| `IF-HUMAN-WORKSPACE-01` | HumanCollaborationWorkspace | 两个中心、Owner 1:1、审批、人工任务、评价、接管和连续性入口 |

合同权威目录为 `08_Collaboration_Protocol/00_公共合同目录与权威关系_v0.3.md`；十项合同本文件为同目录 `01～10`。`11_EVT-01至11路由矩阵`和`12_失败接管与恢复协议`是跨场景规则，不另建事实源。

### 2.1 唯一事实源

- `ORS-03 Work Commitment Ledger`是WorkCommitment及其公共状态的唯一事实源。
- Hermes Kanban、Workspace卡片、列表、Inbox和提醒只能是从ORS-03生成的只读、可重建投影；不得直接拖拽改状态、离线回写或形成第二套可写真相。
- 状态改变只能通过合法命令进入ORS-03状态机，并保留人类/岗位身份、原因、版本和审计。
- AgentRun成功、Tool返回成功、Schema校验成功或卡片显示完成，都不能直接使Commitment进入 `fulfilled`。

## 3. Hermes与组织Runtime映射

| 设计对象 | Hermes/支撑机制 | 约束 |
|---|---|---|
| PMA、BGA、MO三个长期岗位 | 三个独立Profile、HERMES_HOME、容器、服务身份与审计namespace | Profile不是安全边界；不合并为超级Agent |
| 稳定身份和长期禁区 | SOUL | 不放动态权限、业务对象、任务状态或凭据 |
| 程序性方法 | 28个独立Skill（共享5、PMA 6、BGA 11、MO 6） | 按需加载、独立版本/测试；Skill不授予Tool权限。BGA的5个平台Playbook只是设计合同，当前未安装；`SKL-BG-11`为`DORMANT_SCOPE_CANDIDATE` |
| 少量跨Session低敏偏好 | Memory | 候选→人工批准→最小注入；PII、SOP、业务原件和任务状态禁入 |
| 单次岗位专业工作 | Agent Loop/Goal + AgentRun/TaskAttempt | 受已接受Commitment、ContextSnapshot、预算、Schema和Policy限制 |
| 同岗位当前会话并行研究 | 有限Delegate | 只读/无外部副作用；主Profile复核；不承担跨重启承诺 |
| 跨Profile正式协作 | ORS WorkCommitment + RoleHandoff + Inbox | Runtime持久化、至少一次投递、幂等、人工接管 |
| 跨岗位看板 | Hermes Kanban | 仅ORS-03只读、可重建投影 |
| 人类委派、批准、发布、反馈、评价和接管 | Human Collaboration Workspace + OIDC + ApprovalGrant | Workspace不是事实源；普通评论/点击不是批准 |
| SourceRef、证据与候选/正式知识 | ORS-07 Organization Knowledge Hub | 业务原件留在权威载体；人类保留事实与知识确认权，Memory不替代Knowledge Hub |
| 运行、岗位质量、成本、接管与风险证据 | ORS-10 Observability & Role Evaluation | 分层采集；指标与阈值待DEC-08，技术成功不等于业务或岗位评价通过 |
| 全人工队列、接管和恢复对账 | ORS-11 Manual Continuity & Reconciliation | 不覆盖人工期间结果，不替业务Owner作例外决定 |
| 事件投递、验权、持久化、审计 | ORS + 确定性基础设施 | Runtime不代替MO做协作计划，不代替专业岗位判断 |
| 定时唤醒 | ORS调度；Cron仅后评估非关键提醒 | R0关键营销闭环不依赖Cron |
| 远程多Agent | A2A后评估 | R0不使用A2A |
| Tool拦截/事件观测 | Policy Gateway + Events/Hooks/Webhooks | 前置验权是硬门；best-effort通知不作强一致控制 |

## 4. 开发必须保持的边界

1. **身份与网络**：三Profile只能访问内部Organization MCP和Model Gateway；无DB、对象存储、secret-provider、四平台、浏览器、终端、任意HTTP/SQL或互联网访问。
2. **权限**：Organization MCP每次Tool调用按 `role + profile + service identity + commitment + object/action/window` 重新验权；SOUL、Skill、Prompt和Hermes `approvals.mode`均不能授予业务权限。
3. **批准**：Agent只准备证据和请求；只有具名人类身份按ApprovalGrant签发业务授权。
4. **数据**：R0真实PII完全禁入Profile、Context、Memory、Session和日志；只允许去敏LeadStub与不透明SourceRef。
5. **对外动作**：R0四平台全部MANUAL；无自动发布、客户外联、预算修改、询盘/销售判断或共享主凭据。
6. **完成语义**：Run成功只是执行证据；结构和Policy校验合格只允许提交；业务完成由RoleHandoff、输出验收和ORS-03合法迁移共同确定。
7. **人工连续性**：任意Profile、三Profile或Runtime中断时，Workspace必须能输出无PII接管包；恢复后对账，不覆盖人工期间结果。
8. **平台Playbook**：`SKL-BG-07～10`分别对应抖音、小红书、B站和公众号，必须依据`03_Skill_Spec/BGA/00_五平台增长Skill集成目录_v0.3.md`的源名、ZIP SHA-256及三组共同库content hash逐包校验；`PLAT-SKL-OPEN-01`关闭前不得安装或进入onboarding，R0只生成MANUAL候选。`SKL-BG-11`视频号因不在上游四平台范围，只能作为`DORMANT_SCOPE_CANDIDATE`，不得进Profile active allowlist、Shadow或真实任务。五项Playbook均不新增Tool、Connector、平台访问或发布权。

## 5. DEC-01～08的安全默认与阻塞作用

| DEC | 候选安全默认 | 未签署时的开发/激活影响 |
|---|---|---|
| DEC-01 | 销售反馈仅 `pending/valid/invalid/needs_more_info`，只有销售身份可写且带版本化原因码 | 可实现候选Schema；有效询盘指标不冻结，Shadow/active不得凭Agent推断验收 |
| DEC-02 | `MONITOR_ONLY`；MO只准备提醒/升级候选 | 未签时限前不自动外发、不编造SLA；阻塞自动提醒能力而非人工协作 |
| DEC-03 | 未分类外部内容一律要求公司负责人额外ApprovalGrant | 可开发fail-closed路径；未满足额外Grant不得进入Shadow或active的发布准备闭环 |
| DEC-04 | R0四平台均 `MANUAL` | 不阻塞MANUAL的Shadow/`active_limited`；仅阻塞任何A2平台写和步骤6 Canary |
| DEC-05 | Source Registry过渡，默认 `authority=unknown/manual_reference` | 可用合成/人工SourceRef开发；阻塞未定权威载体的真实Connector与真实上下文 |
| DEC-06 | 真实PII `DISABLED`，fail-closed | 可用去敏LeadStub开发；阻塞真实PII、PII Adapter、保留/删除验收和相关激活 |
| DEC-07 | 具名人类技术Owner为硬门 | 未具名不得冻结、实施、接受残余风险或进入onboarding |
| DEC-08 | `BASELINE_ONLY`；不编造SLA、容量、成本或连续失败阈值 | 可埋点和采集基线；未批准阈值不得判定Shadow通过或进入`active_limited` |

## 6. 开发团队决策空间

开发团队仍需由具名技术Owner主持决定：接口端点与物理Schema、存储/队列实现、IAM与密钥轮换、Organization MCP内部实现、模型与供应商、容器/网络策略实现、日志/监控、测试自动化、性能/安全验证和未来Connector技术选型。这些决定必须满足本包的业务Owner、最小权限、幂等、审计、人工接管、恢复和UAT边界，不得反向改写岗位职责。

## 7. 接手条件

V0.3当前只能作为 `ROLE-DESIGN-FREEZE-CANDIDATE`。开发可以在授权后使用合成/去敏输入构建最小垂直切片；未完成人类签署、DEC相应门、实现与验证证据前，不得标记 `DESIGN-FROZEN`、不得创建真实Runtime实例，也不得宣称任一测试或业务能力已通过。
