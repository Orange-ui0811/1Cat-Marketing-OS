# ProfileBundleManifest - DROLE-02 BGA v0.3

> 性质：可签署的Profile Bundle设计冻结候选；不是Hermes配置或运行实例。  
> Bundle内部文件路径和版本在本文锁定；逐文件SHA-256只在最终规范清单生成且人类签署时回填，本候选不伪造hash。

## 1. Bundle身份与三种状态

| 字段 | 锁定值 |
|---|---|
| `bundle_id` | `PB-DROLE-02-BGA` |
| `bundle_version` | `0.3.0-freeze-candidate` |
| `bundle_design_status` | `freeze_candidate` |
| `role_lifecycle_state` | `defined` |
| `runtime_instance_state` | `not_created` |
| `role_id` | `DROLE-02` |
| `profile_id` | `s2-brand-growth` |
| `business_owner_role` | 品牌营销负责人 |
| `technical_owner` | `PENDING-DEC-07` |
| `hermes_baseline` | `Hermes Agent v0.20.0`; tag `v2026.8.3`; commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb` |
| `bundle_file_hash_manifest` | `PENDING-FINAL-SPEC-MANIFEST` |

三种状态不可互相推导：`freeze_candidate`不等于岗位已入职，`defined`不等于Profile已创建，`not_created`不得被运行时心跳或测试记录代替。

## 2. 上游基线锁

| 上游路径 | SHA-256 | 锁定作用 |
|---|---|---|
| `组织架构设计/V1.1/S2_AI原生营销组织架构方案_v1.1.md` | `b15f046cac61ba21f47d64e519779e9566af906831a0e00e4d94e755de363e40` | BGA归属品牌营销中心及人类责任 |
| `组织架构设计/V1.1/S2_技术实现设计业务需求交接包_v0.1.md` | `e4bd375b05af99236299bffedf3959e8a66eef325bfffa6e1c401ec4f187816e` | CAP/GOV/NFR/UAT/DEC |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md` | `6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a` | ORS/Hermes/权限/网络与部署边界 |
| `技术方案设计/V1.1/S2_AI原生营销技术实现设计_UML配套图包_v1.1_冻结候选.md` | `4a3db32fd90ea2ecdc1d9af0698d92700f293d30a8ae9ba7bf944c6c48fe8942` | 结构、协作、生命周期与承诺视图 |
| `技术方案设计/V1.1/S2_技术设计冻结决策签署包_v1.0.md` | `38b91c9f98ebe7bab10f4347aa8194ce75dff2b1a8eb0cc46f076ed8ec275fe6` | DEC-01～08和必签人确认 |

任一上游hash不匹配时，本Bundle立即转change-impact，不继续按原候选签署。

## 3. 岗位组件版本锁

Bundle根路径：`技术方案设计/Agent岗位设计/V0.3/`。

| 组件 | 锁定路径/版本 | BGA约束 |
|---|---|---|
| Role Manifest | `01_Role_Manifest/DROLE-02_Brand_and_Growth_Agent_Role_Manifest_v0.3.md@0.3.0-freeze-candidate` | 岗位使命、Owner、职责、指标、禁区和生命周期权威 |
| SOUL | `02_SOUL/DROLE-02_Brand_and_Growth_Agent_SOUL_v0.3.md@0.3.0-freeze-candidate` | 只放稳定身份、原则、拒绝和升级行为 |
| Skill Pack | `03_Skill_Spec/00_Skill目录与职责追溯_v0.3.md@0.3.0-freeze-candidate`；设计合同精确ID为 `SKL-SH-01,02,03,04,05` 与 `SKL-BG-01,02,03,04,05,06,07,08,09,10,11`，对应 `03_Skill_Spec/Shared/` 和 `03_Skill_Spec/BGA/` 同名v0.3文件；平台集成权威目录为 `03_Skill_Spec/BGA/00_五平台增长Skill集成目录_v0.3.md@0.3.0-freeze-candidate` | Bundle绑定16项Skill设计合同。R0计划allowlist最多为SH-01～05+BG-01～10；BG-07～10当前未安装且须先校验源hash；BG-11是`DORMANT_SCOPE_CANDIDATE`，不进active allowlist/Shadow。不因Playbook新增岗位、Tool或Connector |
| Memory | `04_Memory_Policy/00_共享Memory治理合同_v0.3.md@0.3.0-freeze-candidate` + `04_Memory_Policy/DROLE-02_Brand_and_Growth_Agent_Memory_Policy_v0.3.md@0.3.0-freeze-candidate` | 只允许经批准的低敏品牌呈现、渠道格式、审核和交接偏好 |
| Event/Inbox | `08_Collaboration_Protocol/02_OrganizationEventSubscription_合同_v0.3.md@0.3.0-freeze-candidate` + `11_EVT-01至11路由矩阵_v0.3.md@0.3.0-freeze-candidate` | 订阅 `EVT-01/03/04/05/06/07/08/09/10/11`；只接受合法委派、有效PMA材料、人工平台结果、LeadStub、销售状态与风险/恢复 |
| Tool allowlist | `07_Tool_Permission/00_Tool数据与权限总表_v0.3.md@0.3.0-freeze-candidate` + `07_Tool_Permission/DROLE-02_BGA_Tool_Allowlist_v0.3.md@0.3.0-freeze-candidate` | 候选内容、人工发布准备、LeadStub、销售Handoff、归因候选和升级；R0平台Connector写与PII Adapter为空 |
| Structured outputs | `08_Collaboration_Protocol/09_StructuredOutputSchema_合同_v0.3.md@0.3.0-freeze-candidate` | 锁定 `OUT-SH-01, OUT-BG-01～13`；RoleHandoff使用独立合同 |
| Run/Attempt | `08_Collaboration_Protocol/08_AgentRun与TaskAttempt_合同_v0.3.md@0.3.0-freeze-candidate` | 仅Runtime在已接受Commitment与有效Context/Policy/Schema下启动Hermes run |
| Human Workspace | `08_Collaboration_Protocol/10_HumanCollaborationWorkspace_合同_v0.3.md@0.3.0-freeze-candidate` | 品牌营销Workspace的Campaign/内容共创、批准、ManualPublishTask/回执、暂停/接管；销售Workspace仅LeadStub与销售明确反馈 |
| Evaluation | `06_Evaluation/00_数字岗位统一评价与任用框架_v0.3.md@0.3.0-freeze-candidate` + `06_Evaluation/DROLE-02_Brand_and_Growth_Agent_Evaluation_v0.3.md@0.3.0-freeze-candidate` + `06_Evaluation/00_UAT与岗位测试目录_v0.3.md@0.3.0-freeze-candidate` | 包括品牌安全、去重原始线索趋势、有效询盘率/成本和销售反馈完整率；询盘指标只依据销售明确反馈 |
| Lifecycle/operation | Manifest生命周期 + 统一任用框架 + `05_Daily_Operation/00_三数字岗位日常运行公约_v0.3.md@0.3.0-freeze-candidate` + `05_Daily_Operation/DROLE-02_Brand_and_Growth_Agent_Daily_Operation_v0.3.md@0.3.0-freeze-candidate` | 初始`defined`；Major变更必须`retraining → shadow`；恢复不得绕过Shadow |
| Network policy | `技术方案设计/V1.1/S2_AI原生营销技术实现设计方案_v1.1_冻结候选.md@sha256:6853a78731d5c7fd9835abf0843aabf8992692043abdfdf244dc9c8ddeac510a#9.4` + `07_Tool_Permission/00_Tool数据与权限总表_v0.3.md@0.3.0-freeze-candidate` | 出站默认deny；只访问内部Organization MCP和Model Gateway；无DB/对象存储/secret/四平台/互联网 |

`model_policy_id/version`、实际服务身份、容器镜像digest和部署制品hash属实现交付项，当前均为`not_created/PENDING-TECH-OWNER`，不在设计包中伪造。

### 3.1 五平台Playbook源锁与激活排除

五个源包未声明独立语义版本，因此以`source_skill_name + ZIP SHA-256`精确锁定。五包`.generated`均声明`repo_version=0.7.0`，但共同库内容存在三组`content_hash`：抖音/公众号=`f07dcc50d2cfa129834194774175a9f1ae663b2e8a248485d6ce9f3d8188dea8`，小红书/B站=`fbd4e4c979a55aeaf5852579f3ae41c9d06d7c7b4969c333228c182d8e58aea4`，视频号=`36dfcc37409f60b9bd98bfa0dc2eb60808986cf3b459d03486b3d2e9784fe0b6`；实现导入必须逐包校验。下表是源包证据锁，不表示已安装。

| 设计Skill/文件 | 源Skill + ZIP SHA-256 | 当前/计划激活 |
|---|---|---|
| `SKL-BG-07_抖音增长Playbook集成_v0.3.md@0.3.0-freeze-candidate` | `douyin-growth-playbook` + `1fe1e4dd44b000ddbf7326e22348b1c8add71977da6b0abc716219d3671a80f8` | `not_installed`；导入/评测后才可进R0 MANUAL候选allowlist |
| `SKL-BG-08_小红书增长Playbook集成_v0.3.md@0.3.0-freeze-candidate` | `xiaohongshu-growth-playbook` + `69638b446bf040a20c742db842bac0b0e18742b2a9220b6f9ce6efb4a8301fcc` | `not_installed`；导入/评测后才可进R0 MANUAL候选allowlist |
| `SKL-BG-09_B站增长Playbook集成_v0.3.md@0.3.0-freeze-candidate` | `bilibili-growth-playbook` + `950344e3c9877d232a2c4dbca0db2886598e11be21d29e1e16bd508830461a72` | `not_installed`；导入/评测后才可进R0 MANUAL候选allowlist |
| `SKL-BG-10_公众号增长Playbook集成_v0.3.md@0.3.0-freeze-candidate` | `wechat-official-account-growth-playbook` + `b73c6fc1abf8508b1b9754ae2efc3300d3cfc2bde8e572a0d7803cfcfc22e7d0` | `not_installed`；导入/评测后才可进R0 MANUAL候选allowlist |
| `SKL-BG-11_视频号增长Playbook集成_v0.3.md@0.3.0-freeze-candidate` | `wechat-channels-growth-playbook` + `7a48e372bb3021d7ea80111650a2da1b3bf18425ae72abc40ce4ad2f8168b667` | `DORMANT_SCOPE_CANDIDATE / not_installed`；视频号不在上游四平台范围，不得进Profile active allowlist、真实任务、Shadow或平台操作 |

导入时必须把同hash源包转入受控制品库，分配正式Skill版本并重新核验解包内容。`PLAT-SKL-OPEN-01`是导入硬门：公司负责人/内容资产Owner确认来源与内部使用权，具名技术Owner登记导入Owner、许可证/权属依据、文件allowlist、企业版本、内容清单hash和变更记录；未关闭不得安装、进入`onboarding`或加载真实Profile。五项Skill均只输出`OUT-BG-04 ChannelVariant/PlatformVariant`候选，不直接调用SKL-BG-04、不生成发布状态，不新增Tool、Connector、平台登录、发布或数据抓取能力。

## 4. 十项公共合同锁

`contract_set_version: 0.3.0-freeze-candidate`，权威目录为 `08_Collaboration_Protocol/00_公共合同目录与权威关系_v0.3.md`。

| 合同ID | 锁定文件 | Bundle用法 |
|---|---|---|
| `IF-DROLE-MANIFEST-01` | `01_DigitalRoleManifest_合同_v0.3.md@0.3.0-freeze-candidate` | 验证BGA岗位/版本/生命周期 |
| `IF-EVENT-SUB-01` | `02_OrganizationEventSubscription_合同_v0.3.md@0.3.0-freeze-candidate` | 限定EVT订阅、去重和投递 |
| `IF-WORK-COMMITMENT-01` | `03_WorkCommitment_合同_v0.3.md@0.3.0-freeze-candidate` | 显式承诺；ORS-03唯一事实源 |
| `IF-ROLE-HANDOFF-01` | `04_RoleHandoff_合同_v0.3.md@0.3.0-freeze-candidate` | 产品审核、人工发布、LeadStub/销售交接 |
| `IF-CONTEXT-SNAPSHOT-01` | `05_ContextSnapshot_合同_v0.3.md@0.3.0-freeze-candidate` | Attempt级最小资产、批准、LeadStub和权限快照 |
| `IF-TOOL-CAP-POLICY-01` | `06_ToolCapabilityPolicy_合同_v0.3.md@0.3.0-freeze-candidate` | 逐次Tool验权/脱敏返回；平台写默认拒绝 |
| `IF-APPROVAL-GRANT-01` | `07_ApprovalGrant_合同_v0.3.md@0.3.0-freeze-candidate` | 发布准备绑定人类Grant、对象/version/hash/action/撤销 |
| `IF-AGENT-RUN-01` | `08_AgentRun与TaskAttempt_合同_v0.3.md@0.3.0-freeze-candidate` | Run证据不等于发布或业务完成 |
| `IF-OUTPUT-SCHEMA-01` | `09_StructuredOutputSchema_合同_v0.3.md@0.3.0-freeze-candidate` | 校验OUT-SH-01/OUT-BG-01～13；Agent不输出valid/published |
| `IF-HUMAN-WORKSPACE-01` | `10_HumanCollaborationWorkspace_合同_v0.3.md@0.3.0-freeze-candidate` | 人类批准/发布/回执/销售反馈/暂停/接管 |

Kanban仅为ORS-03只读、可重建投影；卡片拖拽、评论、Run/Tool成功均不能改写Commitment或生成ApprovalGrant。

## 5. DEC-01～08绑定

| DEC | BGA安全默认 | 对本Bundle的门 |
|---|---|---|
| DEC-01 | 销售反馈仅 `pending/valid/invalid/needs_more_info`和版本化原因码；只有销售身份写 | BGA只读并引用；去重原始线索趋势与有效询盘率/成本只按销售明确反馈计算；Shadow前已签 |
| DEC-02 | R0 MONITOR_ONLY；BGA不自动外发销售催办 | 未签时限不编造SLA；Shadow前已签 |
| DEC-03 | 未分类外部内容需公司负责人额外ApprovalGrant；价格/促销/交期/客户承诺/新Claim/法律隐私/舆情不得降级 | 缺额外Grant不创建发布准备闭环；Shadow前已签 |
| DEC-04 | R0四平台全部MANUAL；平台Playbook的存在不产生发布权 | 不阻塞BGA A1/A3的Shadow/`active_limited`；任何A2必须按平台+账号+动作创建Major Bundle和Canary；视频号另受上游scope硬门 |
| DEC-05 | Source Registry；`authority=unknown/manual_reference` | 只读人工提供SourceRef/回执；权威载体未定不建真实Connector |
| DEC-06 | 真实PII DISABLED | 只处理LeadStub/不透明SourceRef；PII在Context/Memory/Session/日志一律fail-closed |
| DEC-07 | 具名技术Owner硬门 | 未具名不得冻结、实施或进`onboarding` |
| DEC-08 | BASELINE_ONLY | 只记录指标公式/样本/分布/失败案例；阈值未批准不进`active_limited` |

## 6. 激活、验证与变更门

1. **`defined → onboarding`**：必签人批准Manifest/SOUL/Skill/Memory/Tool/Evaluation/Lifecycle/10合同/Network；DEC-07具名；`PLAT-SKL-OPEN-01`关闭；实际Profile、服务身份、模型策略和制品hash由开发提供。
2. **`onboarding → shadow`**：只用合成/去敏上下文和MANUAL发布；BGA/Shared Skill、BGA-SR-01～10、适用UAT/UAT-R、`UAT-P01～08`、Workspace批准/人工发布/销售反馈/接管必须有实际执行证据；`SKL-BG-07～10`只有在源ZIP与共同库content hash逐包核验、受控导入、版本分配、离线评测后才可进Shadow allowlist；`SKL-BG-11`必须排除；DEC-01～03已签。
3. **`shadow → active_limited`**：业务Owner审阅实际Shadow证据；DEC-08阈值已批准；品牌安全、销售反馈来源、接管、全人工和恢复对账已实际验证；只激活A1/A3/MANUAL。
4. **A2能力**：不在本Bundle内。Playbook是方法而非Tool，不缩短任何A2授权门。未来任一平台写必须是新Major Bundle，精确绑定平台+账号+动作、官方Connector/IAM、幂等/回执、撤销/补偿、Canary、熔断和人工接管。
5. **岗位拆分**：Skill/Delegate增加不等于新岗位。若未来真实PII、平台A2、独立Owner、持续任务量或风险边界成立，将BGA拆为Brand Content Agent与Growth Operations Agent属组织级Major变更，必须先回上游评审。
6. **Major变更/恢复**：职责/Owner/批准/数据/网络/Tool扩权、合同改义、Hermes基线或上游hash变化都要新Bundle和hash清单，并经`retraining → shadow`；暂停后不得直接回`active_limited`。

当前检查结论只是`设计覆盖`：未创建Profile，未运行测试，未连接四平台/销售系统，未处理真实PII，不得将本Bundle标记为已激活。
