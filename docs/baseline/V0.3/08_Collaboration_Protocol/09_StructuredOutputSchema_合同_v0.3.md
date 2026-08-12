# StructuredOutputSchema 合同 v0.3

> `contract_id: IF-OUTPUT-SCHEMA-01` · 状态：`INTERFACE-FREEZE-CANDIDATE`  
> 目标：让岗位产物可以被Runtime校验、RoleHandoff交接和人类判断；本文定义逻辑Schema合同，不决定JSON Schema工具、接口或存储实现。

## 1. 通用Envelope

所有岗位结构化输出必须包含：

`schema_id, schema_version, output_id, output_status(candidate/draft/submitted), role_id, profile_id, commitment_id/version, attempt_id, correlation_id, purpose, object_refs(id/version/hash), source_refs[], created_at, created_by_role, confidence_or_unknowns, assumptions[], residual_risks[], approvals_required[], next_responsible_role, audit_ref`。

硬规则：Agent输出不得直接使用`approved/published/valid/official/fulfilled`等正式状态；真实PII、凭据、完整思维过程和无授权原件不得嵌入；SourceRef必须在接收者权限内可访问。

## 2. 岗位Schema注册表

| Schema ID | 产物 | 岗位 | 额外必填字段 |
|---|---|---|---|
| OUT-SH-01 | EvidenceNote | 三岗位 | `evidence_type, excerpt_or_summary, applicability, freshness, conflicts, citation` |
| OUT-PM-01 | ProductFactCandidate | PMA | `statement, evidence_refs, conditions, limitations, rd_owner, review_status` |
| OUT-PM-02 | ImpactFinding | PMA | `changed_object, affected_claims/assets, severity, stop_or_review_action` |
| OUT-PM-03 | ResearchFinding | PMA | `question, method, findings, counter_evidence, limits, validation_needed` |
| OUT-PM-04 | PositioningCandidate | PMA | `icp, problem, value, differentiation, evidence, alternatives` |
| OUT-PM-05 | ClaimCandidate | PMA | `claim_text, fact_refs, applicability, prohibited_interpretations, approvers` |
| OUT-PM-06 | ProductAssetDraft | PMA | `asset_type, content_ref, fact_claim_map, audience, version, review_route` |
| OUT-PM-07 | ProductReviewPacket | PMA | `review_object, checks, evidence, conflicts, requested_decision` |
| OUT-PM-08 | EvidenceRequest | PMA | `question, missing_evidence, rd_recipient, needed_scope, due_or_review_point` |
| OUT-BG-01 | ChannelResearch | BGA | `channel, period, sources, opportunities, constraints, risks, validation` |
| OUT-BG-02 | CampaignDraft | BGA | `objective, audience, channels, assets, schedule, budget_boundary_ref, metrics, dependencies, approvers` |
| OUT-BG-03 | ContentMaster | BGA | `body_ref, fact_claim_map, brand_checks, rights, risk_labels, review_status` |
| OUT-BG-04 | PlatformVariant | BGA | `master_ref, platform, variant_ref, difference_summary, cta, rights, risks, platform_quality_gate, native_extension` |
| OUT-BG-05 | PublishPreparation | BGA | `asset/version/hash, grant_refs, channel/account_alias, checks, revocation_status` |
| OUT-BG-06 | ManualPublishTask | BGA | `human_executor_role, immutable_asset_ref, channel, schedule, checks, receipt_requirements, idempotency_key` |
| OUT-BG-07 | PublishReceiptRecord | BGA | `manual_task_ref, actual_asset/version, executed_by_human_ref, occurred_at, result(success/failed/unknown), source_ref` |
| OUT-BG-08 | LeadStub | BGA | `lead_id, opaque_source_ref, touchpoints, campaign/content_refs, dedupe_features_non_pii, record_status(draft/transferred)` |
| OUT-BG-09 | MergeProposal | BGA | `candidate_lead_refs, deterministic_rule, evidence, uncertainty, human_check_required` |
| OUT-BG-10 | SalesHandoff | BGA | `lead_stub_ref, touchpoints, received_fields, unknowns, sales_recipient_role, acceptance_checks` |
| OUT-BG-11 | AttributionCandidate | BGA | `metric_definition, source_refs, associations, alternatives, data_gaps, confidence` |
| OUT-BG-12 | ExperimentReview | BGA | `hypothesis, variants, observations, costs, guardrails, interpretation, next_test` |
| OUT-BG-13 | SalesFeedbackReference | BGA | `lead_stub_ref, feedback_source_ref, sales_actor_ref, sales_judgement_status, reason_code/version, occurred_at`；只登记销售明确反馈 |
| OUT-OR-01 | MissingFieldReport | MO | `brief_ref, missing_or_invalid_fields, affected_work, responsible_role, safe_state` |
| OUT-OR-02 | CollaborationPlan | MO | `goal, candidate_roles, commitments, dependencies, approvals, review_points, risks` |
| OUT-OR-03 | DependencyMap | MO | `nodes, edges, owners, state_refs, cycles_or_conflicts` |
| OUT-OR-04 | CommitmentProposal/Response | MO/接收岗位 | `proposed_role, response, reason, dependencies, required_changes` |
| OUT-OR-05 | Reminder | MO | `subject_ref, responsible_role, impact, requested_action, review_point, aggregation_key` |
| OUT-OR-06 | EscalationPacket | MO | `issue, severity, evidence, affected_work, current_safe_state, decision_owner` |
| OUT-OR-07 | TakeoverPacket | MO | `last_confirmed_state, attempts, object_versions, unknowns, human_takeover_role, next_checks` |
| OUT-OR-08 | ReconciliationPlan | MO | `pre_failure_state, human_changes, differences, stale_items, new_attempts, approval_needed` |
| OUT-OR-09 | ReviewPacket | MO | `period, commitments, outcomes, waits, changes, incidents, costs, open_decisions` |
| OUT-OR-10 | DecisionAgenda | MO | `decision_questions, options, evidence, risks, decision_owners, safe_default` |

RoleHandoff、WorkCommitment、ApprovalGrant、ContextSnapshot和TaskAttempt使用各自独立合同，不重复定义为岗位输出Schema。

### 2.1 五个平台native extension

`native_extension`只包含当前平台适用字段：抖音`attention_reason/single_cognition/hook/proof/payoff`；小红书`search_or_need_intent/click_promise/structured_utility/save_asset`；B站`viewer_starting_knowledge/promised_understanding/knowledge_map/evidence_plan/series_nodes`；公众号`original_insight/search_intent/argument_map/reusable_knowledge_blocks/update_triggers`；视频号`credible_speaker_identity/relationship_context/share_destination/sender_risk/ecosystem_continuation`。

源Playbook返回的`completion_level=publish_ready`必须规范化为`platform_quality_gate=pass_candidate`，Envelope仍为`candidate/draft/submitted`；不得映射为正式批准、Grant有效、可执行发布或已发布。视频号在scope未获批时Schema校验必须返回`blocked_scope`而非候选成品。

## 3. 版本、校验与兼容

- 每个Schema独立版本化；Profile Bundle必须绑定精确版本或兼容范围。
- 字段缺失、类型错误、对象版本漂移、SourceRef不可访问、PII污染或正式状态越权均校验失败。
- 校验通过只表示结构和策略合格，不表示专业结论正确或人类已经接受。
- Major变更需要更新生产Skill、接收者、RoleHandoff、AgentRun、回归集和UML追踪。

## 4. 测试

每个Schema至少覆盖：正常、缺字段、未知显式、SourceRef失效、对象漂移、错误正式状态、越权字段、PII/凭据、旧版本消费者和人类退回。实现团队需选择机器Schema格式并提供可复现验证证据。
