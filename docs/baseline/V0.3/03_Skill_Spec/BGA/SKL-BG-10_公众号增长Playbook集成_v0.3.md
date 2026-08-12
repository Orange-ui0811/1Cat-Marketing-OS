# SKL-BG-10 公众号增长Playbook集成 v0.3

> `skill_id: SKL-BG-10` · `version: 0.3.0-freeze-candidate` · 源Skill：`wechat-official-account-growth-playbook` · 适用：`DROLE-02` · R0=`MANUAL`

## 业务与追溯

对应`BGA-R03`、`CAP-04`、`EVT-06/07`、`OBJ-05`、`DATA-07/08`、`PERM-05/07`、`DEC-03/04`和五平台集成目录。源ZIP SHA-256：`b73c6fc1abf8508b1b9754ae2efc3300d3cfc2bde8e572a0d7803cfcfc22e7d0`。

## 触发与不触发

- 触发：已批准Campaign需要公众号定位、栏目、选题、标题、提纲、完整文章、知识资产、文章诊断或跨平台深度承接。
- 不触发：公众号登录/群发/留言、为了排期拼凑文章、复制/轻改/翻译冒充原创、伪造作者/引用/日期/实践。

## 前置与输入合同

当前ContentMaster、Campaign与Fact/Claim版本、目标读者/决策阶段、核心问题、原创判断与作者Owner、证据/引用/权利SourceRef、栏目/内部链接候选、更新触发器、披露与审核路径。材料没有原创判断、证据、有效综合或真实更新时允许建议小格式、补研究或不发布。

## 方法与人工判断

判断文章是否值得生产→定义读者、问题、原创判断和持久改变→建立知识资产结构与论证图→设计准确标题、可读页面、引用和局限→连接栏目与合理微信生态承接→检查作者、原创、Claim、版权、链接、披露和AI标识→提交人工审核。作者身份、原创判断、引用许可和最终群发由人类确认。

## 输出、停止与完成

输出`PlatformVariant candidate`，native extension含`original_insight, search_intent, argument_map, reusable_knowledge_blocks, update_triggers`。无原创贡献、来源遮蔽、权利/作者/Claim不清、标题正文不符或平台规则待核时停止；完成只表示公众号文章候选可送审。

## Tool、降级与测试

只使用BGA候选与送审能力；无浏览器、HTTP和公众号Connector。降级为提纲、知识块、研究/证据/授权清单或“不建议发布”。测试：文章价值、原创/引用、虚构实践、固定标题长度/打开率/频率神话、Claim越权、版权/披露、publish-ready越权、直接群发和人工退回。
