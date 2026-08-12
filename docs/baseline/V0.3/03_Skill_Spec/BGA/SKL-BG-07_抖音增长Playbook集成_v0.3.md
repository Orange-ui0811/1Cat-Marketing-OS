# SKL-BG-07 抖音增长Playbook集成 v0.3

> `skill_id: SKL-BG-07` · `version: 0.3.0-freeze-candidate` · 源Skill：`douyin-growth-playbook` · 适用：`DROLE-02` · R0=`MANUAL`

## 业务与追溯

对应`BGA-R03`、`CAP-04`、`EVT-06/07`、`OBJ-05`、`DATA-07/08`、`PERM-05/07`、`DEC-03/04`和五平台集成目录。源ZIP SHA-256：`1fe1e4dd44b000ddbf7326e22348b1c8add71977da6b0abc716219d3671a80f8`。

## 触发与不触发

- 触发：已批准Campaign要求抖音选题、标题/封面、Hook、短视频脚本、系列规划，或对人类提供的去敏账号数据做内容诊断。
- 不触发：平台登录/发布/评论/私信、实时抓取、自动判断“限流”、未授权公司/客户Claim、把其他平台稿压缩后直接发布。

## 前置与输入合同

当前ContentMaster、Campaign与Fact/Claim版本、目标受众、账号阶段证据SourceRef、可用素材/权利、CTA边界、风险分类和人工审核路径。数据不足时必须标明阶段推断、置信和缺口；不得根据粉丝数或单条结果制造确定结论。

## 方法与人工判断

锁定一个用户问题与单一认知→判断账号阶段→评估注意价值/相关性/证据/回报/账号适配→选择抖音原生模式→形成`Hook→问题/冲突→证据/解释→回报→适度CTA`→检查Claim、真实性、素材、AI标识和平台规则→提交人工审核。创意方向、真实经历、Claim、版权、合规和是否发布由人类判断。

## 输出、停止与完成

输出`PlatformVariant candidate`，native extension含`attention_reason, single_cognition, hook, proof, payoff`及Quality Gate、证据、素材、风险和待核验项。无证据/权限、绝对优越、虚构测试/客户、平台规则过期或要求直发时停止；完成只表示抖音原生候选可送审。

## Tool、降级与测试

只使用BGA现有`knowledge.search_scoped/object.get_version/content.create_candidate/object.submit_review/handoff`能力；无浏览器、HTTP和抖音Connector。降级为标题/结构/证据需求清单。测试：单一认知、虚假Hook、固定流量池/权重/频率神话、账号数据缺失、Claim越权、AI标识、版权、publish-ready越权、直接发布、PII评论和人工退回。
