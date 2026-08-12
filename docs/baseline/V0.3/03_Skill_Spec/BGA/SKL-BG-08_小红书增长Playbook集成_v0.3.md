# SKL-BG-08 小红书增长Playbook集成 v0.3

> `skill_id: SKL-BG-08` · `version: 0.3.0-freeze-candidate` · 源Skill：`xiaohongshu-growth-playbook` · 适用：`DROLE-02` · R0=`MANUAL`

## 业务与追溯

对应`BGA-R03`、`CAP-04`、`EVT-06/07`、`OBJ-05`、`DATA-07/08`、`PERM-05/07`、`DEC-03/04`和五平台集成目录。源ZIP SHA-256：`69638b446bf040a20c742db842bac0b0e18742b2a9220b6f9ce6efb4a8301fcc`。

## 触发与不触发

- 触发：已批准Campaign需要小红书选题、标题/封面、笔记、搜索内容、收藏资产、系列规划，或用人类提供的去敏数据诊断内容。
- 不触发：平台登录/发布/私信、关键词抓取、伪造“亲测/我用了/客户反馈”、自动判定限流、未授权商业Claim。

## 前置与输入合同

当前ContentMaster、Campaign与Fact/Claim版本、一个主要需求/搜索意图、账号阶段证据SourceRef、真实体验Owner/授权、素材权利、商业披露与审核路径。没有真实体验Owner时只能使用一般原理、明确假设或决策工具。

## 方法与人工判断

识别一个需求/搜索意图→判断账号阶段→形成真实点击承诺→选择平台原生笔记模式→按`问题→答案→证据/推理→结构化效用→结论/适度CTA`生成→设计可复用收藏资产→检查搜索自然度、Claim、体验真实性、版权、披露和AI标识→提交人工审核。人类决定真实经历、商业表达、敏感性和最终发布。

## 输出、停止与完成

输出`PlatformVariant candidate`，native extension含`search_or_need_intent, click_promise, structured_utility, save_asset`及Quality Gate、证据和风险。标题正文不一致、关键词堆砌、虚假体验、焦虑/绝对比较、权限或披露缺失即停止；完成只表示小红书候选可送审。

## Tool、降级与测试

只使用BGA候选与送审能力；无浏览器、HTTP和小红书Connector。降级为问题清单、结构、封面方向和证据需求。测试：需求意图、标题承诺、虚假亲测、关键词/标签/公式神话、无体验Owner、Claim越权、版权/披露、publish-ready越权、直发、PII私信和人工退回。
