---
name: skl-bg-09-b-playbook
description: SKL-BG-09 B站增长Playbook集成 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: 6a279c241db8ea3f9f02f1a7fc5614078d055eac9dfef8737c5f0067190b8053
  dormant: false
---

# SKL-BG-09 B站增长Playbook集成 v0.3

> `skill_id: SKL-BG-09` · `version: 0.3.0-freeze-candidate` · 源Skill：`bilibili-growth-playbook` · 适用：`DROLE-02` · R0=`MANUAL`

## 业务与追溯

对应`BGA-R03`、`CAP-04`、`EVT-06/07`、`OBJ-05`、`DATA-07/08`、`PERM-05/07`、`DEC-03/04`和五平台集成目录。源ZIP SHA-256：`950344e3c9877d232a2c4dbca0db2886598e11be21d29e1e16bd508830461a72`。

## 触发与不触发

- 触发：已批准Campaign需要B站分区/受众、选题、标题/封面、知识地图、长视频脚本、系列规划或去敏账号诊断。
- 不触发：平台登录/投稿/评论、抓取弹幕、把短稿重复拉长、复制剪辑冒充原创、用三连/完播固定权重解释推荐。

## 前置与输入合同

当前ContentMaster、Campaign与Fact/Claim版本、观众起始知识、核心问题、分区/账号阶段证据SourceRef、原创表达与素材权利、实验/演示条件、人工审核路径。没有足够深度、证据或原创贡献时允许建议更小格式或不生产。

## 方法与人工判断

定义问题与承诺理解→判断分区/受众/账号阶段→建立知识地图→设计原始证据和解释→形成准确标题封面→选择原生叙事与章节→设计有价值的社区/系列承接→检查深度、原创、权利、Claim和AI标识→提交人工审核。人类确认原创性、演示条件、版权、专业判断和最终发布。

## 输出、停止与完成

输出`PlatformVariant candidate`，native extension含`viewer_starting_knowledge, promised_understanding, knowledge_map, evidence_plan, series_nodes`。弱证据、拼接抄袭、产品广告硬拉长、分区不明、素材权利或实验条件缺失时停止；完成只表示B站候选可送审。

## Tool、降级与测试

只使用BGA候选与送审能力；无浏览器、HTTP和B站Connector。降级为知识地图、章节、证据/素材需求。测试：起始知识、知识深度、复制冒充原创、固定三连权重/时长神话、测试条件缺失、Claim越权、版权/AI标识、publish-ready越权、直发和人工退回。

