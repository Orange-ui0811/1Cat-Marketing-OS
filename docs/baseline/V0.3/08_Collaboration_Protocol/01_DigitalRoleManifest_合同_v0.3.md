# DigitalRoleManifest 合同 v0.3

> `contract_id: IF-DROLE-MANIFEST-01` · 状态：`INTERFACE-FREEZE-CANDIDATE`  
> 用途：岗位目录、入职评审、Context构建和权限决策的语义来源；不是Hermes配置或IAM策略。

## 1. 必填字段

| 字段 | 语义/约束 |
|---|---|
| `role_id, manifest_version, status` | 稳定岗位ID、语义版本、`draft/approved/superseded`；V0.3为draft |
| `display_name, mission, organization_unit` | 身份、使命、归属；MO显式`cross-center service`而非第三中心 |
| `profile_id, profile_service_identity_ref` | 目标Hermes profile与独立服务身份；profile不是安全边界 |
| `business_owner_role, risk_owner_roles, technical_owner` | 技术Owner在DEC-07前为待指定，不能省略 |
| `service_recipients` | 可服务的人类角色、岗位和接口 |
| `responsibilities[], non_responsibilities[]` | 稳定职责ID、业务结果与禁止事项 |
| `capability_refs[], skill_refs[]` | CAP与精确Skill版本；不得出现无职责Skill |
| `event_subscriptions[], inbox_channels[]` | 事件订阅版本、合法请求者与消息类型 |
| `data_scopes[], tool_policy_ref` | DATA读/候选写范围和ToolCapabilityPolicy |
| `autonomy_by_action[]` | H/A1/A2/A3及人工点；R0无平台A2 |
| `human_reserved_rights[]` | 目标、事实、批准、预算、发布、外联、询盘、经营判断 |
| `memory_policy_ref, output_schema_refs[]` | Memory差异策略与产物合同 |
| `success_metric_refs[], guardrail_refs[], evaluation_policy_ref` | 业务结果、协作质量、成本、风险硬门和岗位任用评价 |
| `escalation_matrix_ref, lifecycle_policy` | 触发、Owner、安全状态、进入/退出门 |
| `profile_bundle_ref, compatible_versions` | Manifest/SOUL/Skill/Memory/Tool/Run/Schema/Runtime/Hermes组合 |
| `workspace_ref, network_policy_ref` | Owner 1:1/审批/接管界面和仅MCP+Model Gateway的网络边界 |
| `upstream_refs_with_hash[], assumptions[], blockers[]` | 组织/业务/技术/UML/签署基线及DEC-01～08 |

## 2. 不变量与校验

- role_id不可复用；Major变更不得原地覆盖。
- business_owner必须是人类角色；Agent/Runtime不能成为最终Owner。
- 每项职责映射Skill、输入、输出、权限、Owner和测试；每个Skill/Tool反向映射职责/CAP。
- 每项评价指标和风险护栏必须有Owner、公式/证据、适用阶段及DEC-08前的baseline处理。
- `human_reserved_rights`和R0禁区不能被SOUL、Skill、Memory、Commitment或紧急请求放宽。
- 生命周期公共状态固定为`defined/onboarding/shadow/active_limited/active_extended/suspended/retraining/retired`；Major变更必须`retraining→shadow`，不得直接恢复active。
- status从draft到approved需公司负责人、对应业务Owner、风险/数据Owner及具名技术Owner按签署包签署；本版未满足。

## 3. 三岗位实例引用

权威实例为`01_Role_Manifest/`下DROLE-01～03 v0.3；开发团队不得从SOUL文本反推职责或权限。验证：schema完整、引用存在、版本兼容、Owner非Agent、非职责与Tool deny一致、生命周期迁移合法。
