# DROLE-02 BGA Tool Allowlist v0.3

> 状态：`ALLOWLIST-FREEZE-CANDIDATE` · R0平台=`MANUAL` · 真实PII禁止。

| 能力族 | 允许动作 | 对象/数据 | 对应Skill | 必须拒绝 |
|---|---|---|---|---|
| `knowledge.search_scoped` | 读有效Fact/Claim/品牌/渠道SourceRef | DATA-04～08授权子集 | BG-01～03/06～11 | 外部浏览、PII/客户正文 |
| `object.get_version` / `approval.status` | 读版本/hash/批准/撤销 | OBJ-03～05 | BG-02～04 | 改批准/正式状态 |
| `campaign/content.create_candidate` | 创建计划、母稿、平台原生变体候选 | OBJ-04/05 | BG-02/03/07～11 | 发布或正式化 |
| `object.submit_review` | 送人工产品/品牌审核 | 候选版本 | BG-02/03/06 | 默认/代替批准 |
| `publish.prepare_manual` / `manual_task.prepare` | 生成锁定人工任务 | 获批ContentAsset | BG-04 | 平台写、账号登录、自动排期执行 |
| `publish_receipt.record_candidate` | 登记人工提供的回执引用 | DATA-08 | BG-04 | 伪造/推断成功 |
| `lead_stub.record` | 写无PII LeadStub/触点ref | DATA-09去敏代理 | BG-05 | 明文PII、私信正文、客户联系 |
| `dedupe.evaluate_rule` | 执行已批准确定规则，产出建议 | 去敏特征 | BG-05 | 不确定强并 |
| `sales_feedback.record_reference` | 记录销售明确回传引用 | DATA-10 | BG-05/06 | 推断有效询盘 |
| `attribution.submit_candidate` / `review.create_packet` | 候选归因与复盘 | DATA-08/10/12 | BG-06 | 正式经营决定/预算修改 |
| `commitment/handoff/human/audit` | 本岗位交接、升级、关联审计 | 当前关联 | Shared | 代签/任意日志 |

SKL-BG-07～11是程序性Playbook，不因加载而新增任何Tool。SKL-BG-11视频号当前为`DORMANT_SCOPE_CANDIDATE`，其候选Tool作用域也不得激活。平台Connector、官方账号、广告账户、私信回复、预算写入、客户外联、真实PII Adapter、浏览/HTTP/SQL/终端/任意文件均不在allowlist。未来A2必须按平台+账号+动作新建独立Major策略和Canary，不得修改本R0条目偷偷扩权。
