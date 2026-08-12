# ProfileBundleManifest - DROLE-03 MO v0.3

> 性质：可签署的Profile Bundle设计冻结候选；不是Hermes配置、中央Workflow或运行实例。  
> Bundle内部文件路径和版本在本文锁定；逐文件SHA-256只在最终规范清单生成且人类签署时回填，本候选不伪造hash。

## 1. Bundle身份与三种状态

| 字段 | 锁定值 |
|---|---|
| `bundle_id` | `PB-DROLE-03-MO` |
| `bundle_version` | `0.3.0-freeze-candidate` |
| `bundle_design_status` | `freeze_candidate` |
| `role_lifecycle_state` | `defined` |
| `runtime_instance_state` | `not_created` |
| `role_id` | `DROLE-03` |
| `profile_id` | `s2-marketing-orchestrator` |
| `business_owner_role` | 品牌营销负责人（跨两个营销中心服务，不构成第三中心） |
| `technical_owner` | `PENDING-DEC-07` |
| `hermes_baseline` | `Hermes Agent v0.20.0`; tag `v2026.8.3`; commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb` |
| `bundle_file_hash_manifest` | `PENDING-FINAL-SPEC-MANIFEST` |

三种状态不可互相推导：`freeze_candidate`不等于岗位已入职，`defined`不等于Profile已创建，`not_created`不得被运行时心跳或测试记录代替。

## 2. 上游基线锁

| 上游路径 | SHA-256 | 锁定作用 |
|---|---|---|
| `组织架构设计/V1.1/S2_AI原生营销组织架构方案_v1.1.md` | `b15f046cac61ba21f47d64e519779e9566af906831a0e00e4d94e755de363e40` | MO跨两个营销中心服务的岗位边界与人类责任 |
| `组织架构设计/V1.1/S2_技术实现设计业务需求交接包_v0.1.md` | `e4bd375b05af99236299bffedf3959e8a66eef325bfffa6e1c401ec4f187816e` | CAP/GOV/NFR/UAT/DEC |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md` | `6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a` | ORS/Hermes/权限/网络与部署边界 |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计_UML配套图包_v1.1_冻结候选.md` | `4a3db32fd90ea2ecdc1d9af0698d92700f293d30a8ae9ba7bf944c6c48fe8942` | 结构、协作、生命周期与承诺视图 |
| `技术方案设计/V1.1/S2_技术设计冻结决策签署包_v1.0.md` | `38b91c9f98ebe7bab10f4347aa8194ce75dff2b1a8eb0cc46f076ed8ec275fe6` | DEC-01～08和必签人确认 |

任一上游hash不匹配时，本Bundle立即转change-impact，不继续按原候选签署。

## 3. 岗位组件版本锁

Bundle根路径：`技术方案设计/Agent岗位设计/V0.3/`。

| 组件 | 锁定路径/版本 | MO约束 |
|---|---|---|
| Role Manifest | `01_Role_Manifest/DROLE-03_Marketing_Orchestrator_Role_Manifest_v0.3.md@0.3.0-freeze-candidate` | 岗位使命、Owner、职责、指标、禁区和生命周期权威；不是Workflow定义 |
| SOUL | `02_SOUL/DROLE-03_Marketing_Orchestrator_SOUL_v0.3.md@0.3.0-freeze-candidate` | 只放稳定身份、协作原则、拒绝和升级行为 |
| Skill Pack | `03_Skill_Spec/00_Skill目录与职责追溯_v0.3.md@0.3.0-freeze-candidate`；精确ID为 `SKL-SH-01,02,03,04,05` 与 `SKL-OR-01,02,03,04,05,06`，对应 `03_Skill_Spec/Shared/` 和 `03_Skill_Spec/MO/` 同名v0.3文件 | 11项可加载Skill；只做协作规划、承诺、提醒候选、升级、接管和复盘组织；Skill不授权Tool |
| Memory | `04_Memory_Policy/00_共享Memory治理合同_v0.3.md@0.3.0-freeze-candidate` + `04_Memory_Policy/DROLE-03_Marketing_Orchestrator_Memory_Policy_v0.3.md@0.3.0-freeze-candidate` | 只允许经批准的低敏通知格式、协调、依赖提示和交班偏好；不存任务状态/Owner名单 |
| Event/Inbox | `08_Collaboration_Protocol/02_OrganizationEventSubscription_合同_v0.3.md@0.3.0-freeze-candidate` + `11_EVT-01至11路由矩阵_v0.3.md@0.3.0-freeze-candidate` | 订阅 `EVT-01～11`的最小组织元数据；不接收专业原件、正文、Lead PII或凭据 |
| Tool allowlist | `07_Tool_Permission/00_Tool数据与权限总表_v0.3.md@0.3.0-freeze-candidate` + `07_Tool_Permission/DROLE-03_MO_Tool_Allowlist_v0.3.md@0.3.0-freeze-candidate` | 只读组织元数据，提交协作计划，提议/跟踪承诺，准备提醒，升级、接管和复盘 |
| Structured outputs | `08_Collaboration_Protocol/09_StructuredOutputSchema_合同_v0.3.md@0.3.0-freeze-candidate` | 锁定 `OUT-SH-01, OUT-OR-01～10`；WorkCommitment/RoleHandoff/ApprovalGrant使用各自独立合同 |
| Run/Attempt | `08_Collaboration_Protocol/08_AgentRun与TaskAttempt_合同_v0.3.md@0.3.0-freeze-candidate` | Runtime只负责唤醒/持久化/验权/证据；不生成MO的协作计划，Run不完成Commitment |
| Human Workspace | `08_Collaboration_Protocol/10_HumanCollaborationWorkspace_合同_v0.3.md@0.3.0-freeze-candidate` | 跨中心的CollaborationPlan/Commitment/依赖/Handoff/分歧/复盘议程；公司/治理视图批准、暂停、接管和审计 |
| Evaluation | `06_Evaluation/00_数字岗位统一评价与任用框架_v0.3.md@0.3.0-freeze-candidate` + `06_Evaluation/DROLE-03_Marketing_Orchestrator_Evaluation_v0.3.md@0.3.0-freeze-candidate` + `06_Evaluation/00_UAT与岗位测试目录_v0.3.md@0.3.0-freeze-candidate` | 评价启动完整、等待透明、依赖、提醒效用/噪声、漏批、接管/恢复、全人工连续性和越权 |
| Lifecycle/operation | Manifest生命周期 + 统一任用框架 + `05_Daily_Operation/00_三数字岗位日常运行公约_v0.3.md@0.3.0-freeze-candidate` + `05_Daily_Operation/DROLE-03_Marketing_Orchestrator_Daily_Operation_v0.3.md@0.3.0-freeze-candidate` | 初始`defined`；Major变更必须`retraining → shadow`；MO停机时人类两个中心仍可运行 |
| Network policy | `技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md@sha256:6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a#9.4` + `07_Tool_Permission/00_Tool数据与权限总表_v0.3.md@0.3.0-freeze-candidate` | 出站默认deny；只访问内部Organization MCP和Model Gateway；无DB/对象存储/secret/平台/互联网 |

`model_policy_id/version`、实际服务身份、容器镜像digest和部署制品hash属实现交付项，当前均为`not_created/PENDING-TECH-OWNER`，不在设计包中伪造。

## 4. 十项公共合同锁

`contract_set_version: 0.3.0-freeze-candidate`，权威目录为 `08_Collaboration_Protocol/00_公共合同目录与权威关系_v0.3.md`。

| 合同ID | 锁定文件 | Bundle用法 |
|---|---|---|
| `IF-DROLE-MANIFEST-01` | `01_DigitalRoleManifest_合同_v0.3.md@0.3.0-freeze-candidate` | 验证MO身份、非第三中心定位、版本和生命周期 |
| `IF-EVENT-SUB-01` | `02_OrganizationEventSubscription_合同_v0.3.md@0.3.0-freeze-candidate` | 限定EVT-01～11元数据订阅、去重和投递 |
| `IF-WORK-COMMITMENT-01` | `03_WorkCommitment_合同_v0.3.md@0.3.0-freeze-candidate` | MO可提议/跟踪，不代接受/验收；ORS-03唯一事实源 |
| `IF-ROLE-HANDOFF-01` | `04_RoleHandoff_合同_v0.3.md@0.3.0-freeze-candidate` | 检查对象版本、证据、未完成项和下一责任人 |
| `IF-CONTEXT-SNAPSHOT-01` | `05_ContextSnapshot_合同_v0.3.md@0.3.0-freeze-candidate` | Attempt级最小目标/承诺/依赖/批准元数据 |
| `IF-TOOL-CAP-POLICY-01` | `06_ToolCapabilityPolicy_合同_v0.3.md@0.3.0-freeze-candidate` | 逐次Tool验权；专业对象、批准、平台、PII、外联默认拒绝 |
| `IF-APPROVAL-GRANT-01` | `07_ApprovalGrant_合同_v0.3.md@0.3.0-freeze-candidate` | MO只读批准状态/发现漏批，不签发/修改/消费Grant |
| `IF-AGENT-RUN-01` | `08_AgentRun与TaskAttempt_合同_v0.3.md@0.3.0-freeze-candidate` | Run只是技术尝试；Runtime不取代MO业务编排 |
| `IF-OUTPUT-SCHEMA-01` | `09_StructuredOutputSchema_合同_v0.3.md@0.3.0-freeze-candidate` | 校验OUT-SH-01/OUT-OR-01～10；MO不输出专业正式结论 |
| `IF-HUMAN-WORKSPACE-01` | `10_HumanCollaborationWorkspace_合同_v0.3.md@0.3.0-freeze-candidate` | 人类委派、承诺协商、分歧、批准、暂停/接管/复盘 |

Kanban仅为ORS-03只读、可重建投影；MO不得通过拖拽卡片、消息、Run/Tool成功将Commitment置为`fulfilled`，也不得强迫PMA/BGA接受承诺。

## 5. DEC-01～08绑定

| DEC | MO安全默认 | 对本Bundle的门 |
|---|---|---|
| DEC-01 | 询盘四状态只由销售写；MO只跟踪是否有明确反馈 | 缺反馈保持pending/unknown语义，不替销售判断；Shadow前已签 |
| DEC-02 | R0 `MONITOR_ONLY`；MO只准备提醒/升级候选 | 未签时限不自动外发、不编造SLA；Shadow前已签 |
| DEC-03 | 未分类外部内容要求公司负责人额外Grant | MO只检测批准依赖/漏批并升级；不签Grant；Shadow前已签 |
| DEC-04 | R0四平台MANUAL | 不阻塞MO A1/A3的Shadow/`active_limited`；阻塞任何A2平台动作，MO本身不获得该权限 |
| DEC-05 | Source Registry；`authority=unknown/manual_reference` | MO只读协调所需摘要/SourceRef；不取代R&D/平台/销售原件 |
| DEC-06 | 真实PII DISABLED | MO仅见LeadStub状态/交接；PII在Context/Memory/Session/日志一律fail-closed |
| DEC-07 | 具名技术Owner硬门 | 未具名不得冻结、实施或进`onboarding` |
| DEC-08 | BASELINE_ONLY | 提醒时限、连续失败、成本/容量阈值均不编造；阈值未批准不进`active_limited` |

## 6. 激活、验证与变更门

1. **`defined → onboarding`**：必签人批准Manifest/SOUL/Skill/Memory/Tool/Evaluation/Lifecycle/10合同/Network；DEC-07具名；实际Profile、服务身份、模型策略和制品hash由开发提供。
2. **`onboarding → shadow`**：只用合成/去敏元数据；MO/Shared Skill、MO-SR-01～10、适用UAT/UAT-R、Workspace承诺协商/分歧/提醒候选/接管必须有实际执行证据；DEC-01～03已签。
3. **`shadow → active_limited`**：业务Owner审阅实际Shadow证据；DEC-08阈值已批准；重复事件、承诺拒绝、Handoff退回、漏批、Runtime中断、提醒噪声、接管、全人工和恢复对账已实际验证；只激活批准的A1/A3。
4. **组织边界**：MO始终是跨中心服务岗位，不是第三中心、全局业务Owner、中央Workflow或技术Runtime的人格化。组织归属、Owner或专业批准边界变化必须先回上游评审。
5. **Major变更/恢复**：职责/Owner/批准/数据/网络/Tool扩权、合同改义、Hermes基线或上游hash变化都要新Bundle和hash清单，并经`retraining → shadow`；暂停后不得直接回`active_limited`。

当前检查结论只是`设计覆盖`：未创建Profile，未运行测试，未连接平台/R&D/销售系统，未处理真实PII，不得将本Bundle标记为已激活。
