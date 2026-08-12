# BGA五平台增长Skill集成目录 v0.3

> 状态：`PLATFORM-SKILL-INTEGRATION-FREEZE-CANDIDATE`  
> 适用岗位：`DROLE-02 Brand & Growth Agent`  
> 形成原因：2026-08-11收到五个已完成的增长Playbook Skill压缩包，经只读审计后纳入Agent岗位设计；本目录不复制、不安装、不执行这些Skill。  
> 变更影响：原设计23个Skill扩展为28个Skill（共享5、PMA 6、BGA 11、MO 6）；数字岗位数量仍为3。

## 1. 集成决定

五个Playbook属于BGA的“平台原生内容判断方法”，不是独立数字岗位、Tool、平台Connector或发布权限。统一由`SKL-BG-03 内容母稿与平台原生适配`选择并加载：

```text
ContentMaster候选
→ 选择已授权的平台Playbook Skill
→ 生成PlatformVariant候选与平台原生扩展
→ 产品/品牌/合规人工审核
→ SKL-BG-04准备ManualPublishTask
→ 具名人类执行平台操作并登记回执
```

前四个平台继承上游R0范围并保持`MANUAL`。微信视频号的Skill可以进入设计包和离线评测候选，但视频号不在上游已批准的四平台范围内，当前固定为`DORMANT_SCOPE_CANDIDATE`；未经公司负责人和品牌营销负责人完成上游scope change-impact，不得进入Profile启用清单、真实任务、Shadow或平台操作。

源Playbook还包含账号定位、账号阶段与内容诊断方法。它们不独立形成经营决策：账号/渠道诊断由`SKL-BG-01`承接为`ChannelResearch`，增长诊断由`SKL-BG-06`承接为`ExperimentReview/AttributionCandidate`；SKL-BG-07～11只提供平台方法和候选判断，不绕过BG-01/BG-06。源文档的账号阶段统一命名为`platform_account_stage`，与DigitalRole的`defined/shadow/active...`生命周期完全分离；多平台任务为每个平台建立独立AccountContext，不共享一个阶段结论。

## 2. 源包锁定

五个源包均未声明独立语义版本，因此V0.3以`source_skill_name + ZIP SHA-256`精确锁定。各包`.generated`都声明`repo_version=0.7.0`，但共同库内容hash并不完全相同，必须逐包登记，不能把一个包的hash外推给其他包。实现导入时必须分配正式Skill版本并重新核验解包内容；文件名相同不代表内容相同。

| 设计Skill | 源Skill名称 | 源ZIP SHA-256 | 共享库content_hash | V0.3状态 / R0边界 |
|---|---|---|---|---|
| SKL-BG-07 | `douyin-growth-playbook` | `1fe1e4dd44b000ddbf7326e22348b1c8add71977da6b0abc716219d3671a80f8` | `f07dcc50d2cfa129834194774175a9f1ae663b2e8a248485d6ce9f3d8188dea8` | 设计启用候选；抖音候选，MANUAL |
| SKL-BG-08 | `xiaohongshu-growth-playbook` | `69638b446bf040a20c742db842bac0b0e18742b2a9220b6f9ce6efb4a8301fcc` | `fbd4e4c979a55aeaf5852579f3ae41c9d06d7c7b4969c333228c182d8e58aea4` | 设计启用候选；小红书候选，MANUAL |
| SKL-BG-09 | `bilibili-growth-playbook` | `950344e3c9877d232a2c4dbca0db2886598e11be21d29e1e16bd508830461a72` | `fbd4e4c979a55aeaf5852579f3ae41c9d06d7c7b4969c333228c182d8e58aea4` | 设计启用候选；B站候选，MANUAL |
| SKL-BG-10 | `wechat-official-account-growth-playbook` | `b73c6fc1abf8508b1b9754ae2efc3300d3cfc2bde8e572a0d7803cfcfc22e7d0` | `f07dcc50d2cfa129834194774175a9f1ae663b2e8a248485d6ce9f3d8188dea8` | 设计启用候选；公众号候选，MANUAL |
| SKL-BG-11 | `wechat-channels-growth-playbook` | `7a48e372bb3021d7ea80111650a2da1b3bf18425ae72abc40ce4ad2f8168b667` | `36dfcc37409f60b9bd98bfa0dc2eb60808986cf3b459d03486b3d2e9784fe0b6` | `DORMANT_SCOPE_CANDIDATE`；视频号未获范围批准 |

源Skill名称与ZIP哈希登记在冻结签署包第3.4节。V0.3规范不把微信接收路径当长期权威仓库，也不持久化该个人目录；实施前由具名技术Owner将经批准的同哈希源包转入受控制品库。

五包未附独立许可证/权属声明、企业Owner、变更日志或正式测试。`PLAT-SKL-OPEN-01`固定为实施导入门：公司负责人/内容资产Owner确认来源与内部使用权，具名技术Owner登记import Owner、许可证/权属依据、导入文件allowlist、企业版本和变更记录；未关闭时可以签署本设计选择，但不能安装、进入onboarding或加载到真实Profile。

## 3. 共同输入与输出适配

### 输入合同

使用源包的`Content Master`思想，但字段映射到V0.3对象：`content_id, CampaignRef/version, business_goal, target_audience, core_problem, core_message, key_points, approved_claim_refs, evidence SourceRefs, available_material_refs/rights, desired_action, sensitivity, assumptions, evidence_gaps`。

硬门：

- `approved_claim_refs`必须来自当前ContextSnapshot中的一猫权威Claim对象；源包自带的空`approved-claims.yaml`只能作为安全默认，不能成为正式Claim事实源。
- 源包的`brand-context/product-context/source-ledger`是随包参考快照，不得覆盖ORS-07或人类提供的当前SourceRef；冲突时当前权威对象优先并记录差异。
- 诊断任务只接受人类提供的去敏账号数据/截图SourceRef；不得登录平台、浏览账号、抓取评论、读取私信或推断个人关系图。
- 源包的source ledger含内部目录/File ID及具名案例候选，只能按当前Commitment最小引用；默认不注入完整账本、内部路径、具名案例或不相关品牌/产品快照。

### 输出合同

五个Skill统一输出`OUT-BG-04 ChannelVariant/PlatformVariant`候选，并保留平台原生`native_extension`：

- 抖音：注意理由、单一认知、Hook、证据、回报；
- 小红书：搜索/需求意图、点击承诺、结构化效用、收藏资产；
- B站：观众起始知识、承诺理解、知识地图、证据计划、系列节点；
- 公众号：原创判断、搜索意图、论证图、可复用知识块、更新触发器；
- 视频号：可信出镜身份、关系场景、分享目的地、发送者风险、微信生态承接。

源包中的`completion_level=publish_ready`在V0.3只能映射为`platform_quality_gate=pass_candidate`，绝不等于`approved`、ApprovalGrant有效、可发布或已发布。V0.3对外提交状态仍只能是`candidate/draft/submitted`。

## 4. 共同治理覆盖

1. 源包的`FACT/CONSENSUS/HEURISTIC/MYTH`分类保留，并映射到SKL-SH-01；平台算法公式、固定权重、流量池、时长和频率保证不得当作事实。
2. 公司、产品、客户、融资、专利、第一/唯一/最好、性能和测试数字，必须引用已批准Claim及完整条件；当前无有效引用即停止或改为明确标注的一般原理。
3. 版权、原创、人物/客户经历、素材权限、商业披露和AI生成内容标识由具名人类确认；当前法律与平台规则必须使用带复核日期的SourceRef，不从模型记忆推断UI步骤。
4. DEC-03的未分类外部内容和七类高风险额外批准门高于源Skill质量门。
5. DEC-04下四个已批准平台均MANUAL；视频号也默认MANUAL，但首先受上游范围门阻断。
6. 这些Skill不新增Tool能力；所有浏览器、HTTP、平台登录、发布、评论/私信、外联、账号数据抓取、PII和主凭据仍为deny。
7. 平台Playbook的更新属于Skill版本变化；若改变Claim、PII、外部动作或岗位责任，按Major执行`retraining→shadow`。
8. B站社区回复/置顶、公众号或视频号直播/小程序/企微/联系承接、ContentMaster的`lead/inquire`意图只能转为人工建议或已批准资产引用；不得因此新增评论、私信、链接创建、外联、关系图或PII能力。

## 5. 导入文件allowlist与最小加载

源包不能原样安装。实施导入至少分三层：

| 层 | 允许候选 | 默认排除/处理 |
|---|---|---|
| 程序性核心 | 根`SKILL.md`中经企业合同覆盖的方法、平台`mental-model/topic-selection/content-patterns/decision-heuristics/quality-gate` | 删除任何可能被解释为平台权限或自动执行的表述 |
| 共同合同 | `content-master/platform-variant/evidence-standard/claim-policy/content-compliance/ai-generated-content` | 映射到V0.3 Schema、SourceRef、DEC-03和人工门；不作第二权威源 |
| 按需参考 | `lifecycle/diagnosis/myths/1cat-adaptation/examples`及平台专属结构 | 按Commitment最小加载；标来源日期、事实层级、适用范围和复核点 |
| 默认不整包注入 | 完整`source-ledger.yaml`、brand/product/approved-claims快照、内部路径/File ID、具名案例候选 | 仅经业务Owner确认的单条SourceRef可进入Context；Memory禁止保存 |

实现前还要为每个企业Skill登记`enterprise_skill_id/version, source_zip_sha256, imported_file_manifest/hash, business_owner, technical_owner, provenance/license_ref, supported_outputs, tool_capability_refs(empty for external action), test_suite_ref`。

## 6. 加载与回退

- BGA只加载当前Commitment所需的平台Skill，不把五套参考全部注入Context。
- 账号诊断任务由BG-01/BG-06持有输出合同；平台Skill只提供可追溯的启发式/事实分类，不独立作增长结论。
- 多平台任务以同一ContentMaster为事实和意图基线，各Skill独立生成变体；不得把一个平台的native extension机械复制给另一个平台。
- Skill缺失、源hash不符、平台规则过期或必要参考不可访问时，回退为通用结构/问题清单并保持候选，不声称平台原生适配完成。
- `SKL-BG-03`负责跨平台一致性与选择；`SKL-BG-07～11`负责平台原生判断；`SKL-BG-04`负责批准检查和人工发布准备，三者不得合并为“生成即发布”。

## 7. 集成测试合同

每个源Skill至少覆盖：正常候选、ContentMaster缺失、无批准Claim、证据冲突、平台规则过期、版权/原创不明、AI内容标识待核、账号数据缺失、算法神话诱导、`publish_ready`越权映射、直接发布/登录诱导、PII/私信/关系图诱导、Tool缺失和人工退回。

跨平台另覆盖：同一事实不被五个平台改强、不同平台保留原生结构、多Skill只注入必要参考、四平台MANUAL、视频号scope gate、对象版本变化使所有变体失效。这里只定义测试，不声称已安装、执行或通过。

## 8. 视频号启用的上游变更影响

SKL-BG-11从dormant转可加载前，至少需要更新并重签上游平台范围相关的组织能力、CAP-04、EVT-06、DATA-08、DEC-04、技术方案平台边界和UML外部平台视图，再同步更新BGA Manifest/SOUL、BG-01/03/04、Schema native extension、事件平台allowlist、Memory隐私、评价/UAT、Profile Bundle、冻结签署和规范hash。启用仍从新Major Bundle的`retraining→shadow`开始，R0默认MANUAL；未来A2仍按“视频号+账号+动作”独立Canary。
