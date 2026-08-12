# SKL-BG-11 视频号增长Playbook集成 v0.3

> `skill_id: SKL-BG-11` · `version: 0.3.0-freeze-candidate` · 源Skill：`wechat-channels-growth-playbook` · 适用：`DROLE-02` · `activation=DORMANT_SCOPE_CANDIDATE`

## 业务与追溯

候选对应`BGA-R03`、`CAP-04`、`OBJ-05`、`PERM-05/07`、`DEC-03`和五平台集成目录。源ZIP SHA-256：`7a48e372bb3021d7ea80111650a2da1b3bf18425ae72abc40ce4ad2f8168b667`。微信视频号不在上游已批准四平台范围；本Skill进入设计和离线候选，不构成R0启用或第五平台批准。

## 触发与不触发

- 设计触发：上游scope change-impact获公司负责人和品牌营销负责人批准后，才可为视频号选题、标题/封面、脚本、可信身份、分享场景和微信生态承接生成候选。
- 当前不触发：任何真实Commitment、Profile加载、Shadow、平台登录/发布、私信/联系人、关系图推断、未授权私域协调或自动外联。

## 前置与输入合同

除通用ContentMaster、Campaign、Fact/Claim、素材权利和审核路径外，必须有上游平台范围批准引用、可信出镜身份的人类确认、明确且隐私安全的关系场景、可选Share Destination Contract及发送者风险。不得读取或模拟真实好友关系、身份、对话、联系人或个人数据。

## 方法与人工判断

在启用后：定义观众与可信表达者→判断账号阶段/关系场景→仅在自然时定义分享目的地→选择平台原生题材与叙事→先交付有用判断和证据，再设计适度承接→检查隐私、关系真实性、Claim、素材、披露和AI标识→提交人工审核。人类决定身份授权、关系场景、私域边界、CTA和最终发布。

## 输出、停止与完成

输出`PlatformVariant candidate`，native extension含`credible_speaker_identity, relationship_context, share_destination, sender_risk, ecosystem_continuation`。无scope批准、身份不实、强迫转发、虚构关系/客户、暴露个人信息或连接无关漏斗时阻断。完成只表示视频号候选可送审；当前状态下不得产出真实任务。

## Tool、降级与测试

当前Tool allowlist为空；即使未来启用，也只继承BGA候选与送审能力，平台Connector仍需独立Major策略和Canary。测试：scope未批、虚构可信身份、关系图/联系人诱导、强迫分享、固定好友权重/流量池神话、Claim越权、隐私/AI标识、publish-ready越权、直发和人工退回。
