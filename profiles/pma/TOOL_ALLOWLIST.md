# DROLE-01 PMA Tool Allowlist v0.3

> 状态：`ALLOWLIST-FREEZE-CANDIDATE` · 允许的是能力族，不是已存在端点或已授权工具。

| 能力族 | 允许动作 | 对象/数据 | 对应Skill | 必须拒绝 |
|---|---|---|---|---|
| `knowledge.search_scoped` | 授权SourceRef检索 | DATA-02～05当前任务子集 | SH-01、PM-01～05 | 任意外部搜索、PII、跨对象批量 |
| `object.get_version` | 读对象版本/hash/状态 | OBJ-01～05授权对象 | PM-01/03～05 | 修改正式状态 |
| `evidence.create_note_candidate` | 写EvidenceNote候选 | 当前Commitment | SH-01、PM-01/02/06 | 正式知识写 |
| `object.create_candidate` | 创建Fact/Claim/资产/研究候选 | 对应OBJ候选域 | PM-01～04 | approved/effective状态 |
| `fact.flag_gap` / `impact.analyze_candidate` | 标缺口/影响候选 | ProductFact及下游ref | PM-01 | 自动暂停正式对象 |
| `object.submit_review` | 送具名人类审核 | 候选与审核包 | PM-03～05、SH-04 | 代批、改Approval |
| `rd_evidence.request_candidate` | 准备补证请求 | R&D接口SourceRef | PM-06 | 索取受限原件/秘密 |
| `commitment.*` / `handoff.*` | 本岗位响应、交接 | 当前Commitment | SH-02 | 代替他人承诺 |
| `human.escalate` / `audit.get_scoped_trace` | 升级/读关联审计 | 当前关联ID | SH-03/05 | 任意日志读取 |

默认拒绝所有未列能力；尤其`publish.* write`、message/contact、budget/payment、sales judgement、platform credential、browser、HTTP、SQL、shell、filesystem任意读写。权限只在`active ContextSnapshot + accepted Commitment + active_limited/shadow`范围内有效；对象版本漂移立即失效。
