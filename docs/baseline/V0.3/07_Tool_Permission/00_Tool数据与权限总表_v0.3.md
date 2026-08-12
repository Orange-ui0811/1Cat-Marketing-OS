# 三岗位 Tool、数据与权限总表 v0.3

> 状态：`TOOL-POLICY-FREEZE-CANDIDATE` · 本文是最小能力需求，不是Connector/MCP/Profile配置。  
> 原则：Profile不是安全边界；每次调用由Runtime和外部IAM共同执行`ToolCapabilityPolicy`。

## 1. R0权限结论

| 岗位 | 允许范围 | R0显式禁止 |
|---|---|---|
| PMA | 读取授权证据/对象版本；创建候选；送审；补证；影响标记；升级/交接 | 正式Fact/Claim/批准、发布、外联、预算、询盘、任意HTTP/SQL/终端/浏览器 |
| BGA | 读取授权对象；创建Campaign/内容/归因候选；准备人工发布任务；登记去敏LeadStub与人工回执；交接/升级 | 平台写、主凭据、正式批准、预算修改、客户外联、销售判断、明文PII、任意通用执行能力 |
| MO | 读事件/组织目录/最小摘要；计划协作；提出/跟踪承诺；提醒、升级、人工接管和复盘组织 | 专业对象改写、业务批准、发布、Lead/PII正文、预算、外联、询盘、任意通用执行能力 |

三岗位均不得拥有`approvals.mode`替代业务授权、平台主账号、任意网络、任意文件、任意代码/终端、任意SQL、任意浏览器、任意消息发送或跨对象批量写。不存在“管理员模式”或紧急绕过。

## 2. 数据范围

| DATA | PMA | BGA | MO | R0控制 |
|---|---|---|---|---|
| DATA-01 Brief/目标 | 读授权、草拟产品侧输入 | 读授权、草拟Campaign输入 | 读状态与最小摘要 | 正式批准仅人类 |
| DATA-02 产品原始证据 | 按SourceRef只读 | 不读原件；只收PMA摘要 | 不读 | DEC-05前无通用Connector |
| DATA-03 ProductFact | 读/候选/缺口 | 只读有效版本 | 只读状态摘要 | 正式确认仅R&D |
| DATA-04 研究 | 读/候选 | 读授权子集/候选 | 只读交接摘要 | 外部来源人工提供SourceRef |
| DATA-05 ICP/定位/Claim | 读/候选/送审 | 只读有效；可引用 | 只读状态摘要 | 正式批准仅人类 |
| DATA-06 Campaign/预算边界 | 读相关摘要 | 读/候选；预算只读边界 | 只读状态/依赖 | Agent不改预算 |
| DATA-07 内容/批准 | 读待审版本/审核包 | 候选、人工发布准备、回执引用 | 只读状态摘要 | Agent不批准；R0不平台写 |
| DATA-08 平台结果 | 不读或授权摘要 | 登记人工回执/读授权结果 | 只读状态摘要 | 外部结果unknown保护 |
| DATA-09 原始线索/触点 | 禁止 | 只处理无PII LeadStub/不透明ref | 只读计数/状态 | DEC-06前真实PII fail-closed |
| DATA-10 销售反馈 | 读去敏研究摘要 | 登记明确回传引用 | 只读状态/unknown | Agent不推断 |
| DATA-11任务/审批/异常日志 | 读本岗位范围 | 读写本岗位关联 | 读写协作关联 | 追加、不可静默改历史 |
| DATA-12实验/复盘/决定 | 读/候选专业分析 | 读/候选归因 | 汇总摘要/议程 | 正式知识/决定仅人类 |

## 3. PERM映射

| PERM | PMA | BGA | MO | 人类保留 |
|---|---|---|---|---|
| 01正式任务 | 草拟输入 | 草拟输入 | 完整性/承诺建议 | 公司负责人批准 |
| 02事实整理 | A1/A3候选 | 只读 | 状态协调 | R&D确认 |
| 03定位/Claim | A1候选 | 只读有效 | 协调审批 | 公司负责人批准 |
| 04 Campaign | 提供产品输入 | A1候选 | 协调 | 品牌负责人批准 |
| 05内容 | 产品资产候选/审核准备 | 内容候选 | 协调 | 人类审核 |
| 06批准内容 | 条件检查 | 条件检查 | 提醒/记录 | 人类批准 |
| 07发布 | 禁止 | R0仅人工任务 | 跟踪人工结果 | 人类平台操作 |
| 08预算 | 禁止写，可证据建议 | 禁止写，可分析建议 | 协调决定 | 人类决定 |
| 09/10线索 | 禁止 | 去敏登记/确定规则建议 | 状态协调 | 不确定由人类 |
| 11外联 | 禁止 | 禁止 | 禁止 | 品牌/销售人类 |
| 12询盘判断 | 禁止 | 仅登记销售明确反馈 | 只跟踪unknown | 销售判断 |
| 13路由提醒 | 本岗位交接 | 本岗位交接 | A3协调 | 人类可暂停/改派 |
| 14正式知识/决定 | 候选 | 候选 | 议程/关联 | 对应Owner确认 |

## 4. 统一Tool响应合同

每次响应必须含：`request_id, tool_call_id, correlation_id, role_id, profile_id, service_identity_id, commitment_id, attempt_id, object_refs(id/type/version/hash), action, approval_grant_ref(optional), policy_decision(allow/deny/require_human), policy_reason_code, policy_version, authority_snapshot_id, idempotency_key, success, result_code, result_status(success/failed/unknown/not_executed), retryable(boolean), retryability(safe/unsafe/conditional), human_task_id(optional), audit_ref, redacted_message`。`success=true`只表示该技术动作及执行后验证被确认，不表示Commitment或业务对象完成。错误不得暴露PII、凭据、原始正文、内部地址或安全策略细节。

只有`policy_decision=allow`且role、profile、service identity、Commitment、attempt、对象、动作和时间窗均匹配时执行；`deny/require_human`返回`not_executed`。外部结果unknown时`retryable=false, retryability=unsafe`，创建人工对账任务。Runtime校验技术幂等；岗位解释业务影响并升级。

## 5. 反向业务理由检查

Tool allowlist中的每个能力必须回溯到DROLE职责、Skill和CAP/PERM；无映射的Tool默认拒绝。确定性对象状态、批准绑定、去重、权限、幂等和审计由普通软件/规则自动化实现，不包装成新Agent Skill。
