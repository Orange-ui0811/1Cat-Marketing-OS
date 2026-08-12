# ProfileBundleManifest - DROLE-01 PMA v0.3

> 性质：可签署的Profile Bundle设计冻结候选；不是Hermes配置或运行实例。  
> Bundle内部文件路径和版本在本文锁定；逐文件SHA-256只在最终规范清单生成且人类签署时回填，本候选不伪造hash。

## 1. Bundle身份与三种状态

| 字段 | 锁定值 |
|---|---|
| `bundle_id` | `PB-DROLE-01-PMA` |
| `bundle_version` | `0.3.0-freeze-candidate` |
| `bundle_design_status` | `freeze_candidate` |
| `role_lifecycle_state` | `defined` |
| `runtime_instance_state` | `not_created` |
| `role_id` | `DROLE-01` |
| `profile_id` | `s2-product-marketing` |
| `business_owner_role` | 产品营销负责人 |
| `technical_owner` | `PENDING-DEC-07` |
| `hermes_baseline` | `Hermes Agent v0.20.0`; tag `v2026.8.3`; commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb` |
| `bundle_file_hash_manifest` | `PENDING-FINAL-SPEC-MANIFEST` |

三种状态不可互相推导：`freeze_candidate`不等于岗位已入职，`defined`不等于Profile已创建，`not_created`不得被运行时心跳或测试记录代替。

## 2. 上游基线锁

| 上游路径 | SHA-256 | 锁定作用 |
|---|---|---|
| `组织架构设计/V1.1/S2_AI原生营销组织架构方案_v1.1.md` | `b15f046cac61ba21f47d64e519779e9566af906831a0e00e4d94e755de363e40` | PMA归属产品营销中心及人类责任 |
| `组织架构设计/V1.1/S2_技术实现设计业务需求交接包_v0.1.md` | `e4bd375b05af99236299bffedf3959e8a66eef325bfffa6e1c401ec4f187816e` | CAP/GOV/NFR/UAT/DEC |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md` | `6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a` | ORS/Hermes/权限/网络与部署边界 |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计_UML配套图包_v1.1_冻结候选.md` | `4a3db32fd90ea2ecdc1d9af0698d92700f293d30a8ae9ba7bf944c6c48fe8942` | 结构、协作、生命周期与承诺视图 |
| `技术方案设计/V1.1/S2_技术设计冻结决策签署包_v1.0.md` | `38b91c9f98ebe7bab10f4347aa8194ce75dff2b1a8eb0cc46f076ed8ec275fe6` | DEC-01～08和必签人确认 |

任一上游hash不匹配时，本Bundle立即转change-impact，不继续按原候选签署。

## 3. 岗位组件版本锁

Bundle根路径：`技术方案设计/Agent岗位设计/V0.3/`。

| 组件 | 锁定路径/版本 | PMA约束 |
|---|---|---|
| Role Manifest | `01_Role_Manifest/DROLE-01_Product_Marketing_Agent_Role_Manifest_v0.3.md@0.3.0-freeze-candidate` | 岗位使命、Owner、职责、指标、禁区和生命周期权威 |
| SOUL | `02_SOUL/DROLE-01_Product_Marketing_Agent_SOUL_v0.3.md@0.3.0-freeze-candidate` | 只放稳定身份、原则、拒绝和升级行为 |
| Skill Pack | `03_Skill_Spec/00_Skill目录与职责追溯_v0.3.md@0.3.0-freeze-candidate`；精确ID为 `SKL-SH-01,02,03,04,05` 与 `SKL-PM-01,02,03,04,05,06`，对应 `03_Skill_Spec/Shared/` 和 `03_Skill_Spec/PMA/` 同名v0.3文件 | 11项可加载Skill；Skill不授权Tool |
| Memory | `04_Memory_Policy/00_共享Memory治理合同_v0.3.md@0.3.0-freeze-candidate` + `04_Memory_Policy/DROLE-01_Product_Marketing_Agent_Memory_Policy_v0.3.md@0.3.0-freeze-candidate` | 只允许经批准的低敏术语、格式、审核与协作偏好 |
| Event/Inbox | `08_Collaboration_Protocol/02_OrganizationEventSubscription_合同_v0.3.md@0.3.0-freeze-candidate` + `11_EVT-01至11路由矩阵_v0.3.md@0.3.0-freeze-candidate` | 订阅 `EVT-01/02/03/04/06/07/10/11`；仅合法委派、承诺、证据/补证、审核和风险/恢复事件 |
| Tool allowlist | `07_Tool_Permission/00_Tool数据与权限总表_v0.3.md@0.3.0-freeze-candidate` + `07_Tool_Permission/DROLE-01_PMA_Tool_Allowlist_v0.3.md@0.3.0-freeze-candidate` | 只读授权证据、创建候选、送审、补证、交接、升级 |
| Structured outputs | `08_Collaboration_Protocol/09_StructuredOutputSchema_合同_v0.3.md@0.3.0-freeze-candidate` | 锁定 `OUT-SH-01, OUT-PM-01～08`；RoleHandoff使用独立合同 |
| Run/Attempt | `08_Collaboration_Protocol/08_AgentRun与TaskAttempt_合同_v0.3.md@0.3.0-freeze-candidate` | 仅Runtime在已接受Commitment与有效Context/Policy/Schema下启动Hermes run |
| Human Workspace | `08_Collaboration_Protocol/10_HumanCollaborationWorkspace_合同_v0.3.md@0.3.0-freeze-candidate` | 产品营销中心Inbox、Owner 1:1、证据/Claim候选审核、补证、修改差异、暂停和接管 |
| Evaluation | `06_Evaluation/00_数字岗位统一评价与任用框架_v0.3.md@0.3.0-freeze-candidate` + `06_Evaluation/DROLE-01_Product_Marketing_Agent_Evaluation_v0.3.md@0.3.0-freeze-candidate` + `06_Evaluation/00_UAT与岗位测试目录_v0.3.md@0.3.0-freeze-candidate` | 评价、任用与测试证据不由Agent自批 |
| Lifecycle/operation | Manifest生命周期 + 统一任用框架 + `05_Daily_Operation/00_三数字岗位日常运行公约_v0.3.md@0.3.0-freeze-candidate` + `05_Daily_Operation/DROLE-01_Product_Marketing_Agent_Daily_Operation_v0.3.md@0.3.0-freeze-candidate` | 初始`defined`；Major变更必须`retraining → shadow`；恢复不得绕过Shadow |
| Network policy | `技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md@sha256:6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a#9.4` + `07_Tool_Permission/00_Tool数据与权限总表_v0.3.md@0.3.0-freeze-candidate` | 出站默认deny；只访问内部Organization MCP和Model Gateway；无DB/对象存储/secret/平台/互联网 |

`model_policy_id/version`、实际服务身份、容器镜像digest和部署制品hash属实现交付项，当前均为`not_created/PENDING-TECH-OWNER`，不在设计包中伪造。

## 4. 十项公共合同锁

`contract_set_version: 0.3.0-freeze-candidate`，权威目录为 `08_Collaboration_Protocol/00_公共合同目录与权威关系_v0.3.md`。

| 合同ID | 锁定文件 | Bundle用法 |
|---|---|---|
| `IF-DROLE-MANIFEST-01` | `01_DigitalRoleManifest_合同_v0.3.md@0.3.0-freeze-candidate` | 验证PMA岗位/版本/生命周期 |
| `IF-EVENT-SUB-01` | `02_OrganizationEventSubscription_合同_v0.3.md@0.3.0-freeze-candidate` | 限定EVT订阅、去重和投递 |
| `IF-WORK-COMMITMENT-01` | `03_WorkCommitment_合同_v0.3.md@0.3.0-freeze-candidate` | 显式承诺；ORS-03唯一事实源 |
| `IF-ROLE-HANDOFF-01` | `04_RoleHandoff_合同_v0.3.md@0.3.0-freeze-candidate` | 候选/审核/补证带版本交接 |
| `IF-CONTEXT-SNAPSHOT-01` | `05_ContextSnapshot_合同_v0.3.md@0.3.0-freeze-candidate` | Attempt级最小证据与权限快照 |
| `IF-TOOL-CAP-POLICY-01` | `06_ToolCapabilityPolicy_合同_v0.3.md@0.3.0-freeze-candidate` | 逐次Tool验权/脱敏返回 |
| `IF-APPROVAL-GRANT-01` | `07_ApprovalGrant_合同_v0.3.md@0.3.0-freeze-candidate` | PMA只读批准状态，不签发/修改Grant |
| `IF-AGENT-RUN-01` | `08_AgentRun与TaskAttempt_合同_v0.3.md@0.3.0-freeze-candidate` | Run证据不等于业务完成 |
| `IF-OUTPUT-SCHEMA-01` | `09_StructuredOutputSchema_合同_v0.3.md@0.3.0-freeze-candidate` | 校验OUT-SH-01/OUT-PM-01～08 |
| `IF-HUMAN-WORKSPACE-01` | `10_HumanCollaborationWorkspace_合同_v0.3.md@0.3.0-freeze-candidate` | 人类委派、审核、修改、暂停/接管 |

Kanban仅为ORS-03只读、可重建投影；卡片拖拽、评论、Run/Tool成功均不能改写Commitment或生成ApprovalGrant。

## 5. DEC-01～08绑定

| DEC | PMA安全默认 | 对本Bundle的门 |
|---|---|---|
| DEC-01 | 询盘四状态只由销售写；PMA不推断 | 三岗位Shadow闭环前签署；不扩展PMA职责 |
| DEC-02 | MO仅MONITOR_ONLY；PMA无自动外发提醒 | 未签时限不编造SLA |
| DEC-03 | 新Claim、价格、交期、承诺或未分类外部内容要求额外Grant | 缺Grant时保持候选并升级；Shadow前安全默认必须已签 |
| DEC-04 | R0四平台MANUAL；PMA从不发布 | 不阻塞PMA A1/A3的Shadow/`active_limited`；阻塞任何平台A2 |
| DEC-05 | Source Registry；`authority=unknown/manual_reference` | 只读人工提供SourceRef；权威载体未定不建真实Connector |
| DEC-06 | 真实PII DISABLED | PII在Context/Memory/Session/日志一律fail-closed |
| DEC-07 | 具名技术Owner硬门 | 未具名不得冻结、实施或进`onboarding` |
| DEC-08 | BASELINE_ONLY | 可记录公式/样本/分布；阈值未批准不进`active_limited` |

## 6. 激活、验证与变更门

1. **`defined → onboarding`**：必签人批准Manifest/SOUL/Skill/Memory/Tool/Evaluation/Lifecycle/10合同/Network；DEC-07具名；实际Profile、服务身份、模型策略和制品hash由开发提供。
2. **`onboarding → shadow`**：仅合成/去敏上下文；PMA/Shared Skill、PMA-SR-01～10、适用UAT/UAT-R和Workspace人工审核/接管必须有实际执行证据；DEC-01～03安全默认已签。
3. **`shadow → active_limited`**：业务Owner审阅实际Shadow证据；DEC-08阈值已批准；接管、全人工和恢复对账已实际验证；只激活批准的A1/A3。
4. **Major变更**：任一职责/Owner/批准/数据/网络/Tool扩权、合同改义、Hermes基线或上游hash变化，都要新Bundle版本和新hash清单，并经`retraining → shadow`重新评价。
5. **恢复**：暂停/事故后不得从`suspended`直接回`active_limited`；必须根因关闭、重新授权、人工期间对账、必要的`retraining`和Shadow证据。

当前检查结论只是`设计覆盖`：未创建Profile，未运行测试，未连接R&D/平台/销售系统，未处理真实PII，不得将本Bundle标记为已激活。
