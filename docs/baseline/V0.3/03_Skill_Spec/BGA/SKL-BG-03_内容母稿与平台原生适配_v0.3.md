# SKL-BG-03 内容母稿与平台原生适配 v0.3

> `skill_id: SKL-BG-03` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-02`

## 业务与追溯

对应`BGA-R03`、`CAP-04`、`EVT-06/07`、`OBJ-05`、`DATA-07`、`PERM-05`、`GOV-02/03`、`DEC-03/04`及`IF-APPROVAL-GRANT-01`。

## 触发与不触发

- 触发：Campaign已批准且资产任务成立，或获批母稿需要一个或多个已授权平台的原生变体候选。
- 不触发：未批Campaign的正式生产任务；成品批准或发布；平台连接或写入；绕过产品/品牌审核；把内容生成视为对外授权。

## 前置与输入

Campaign版本/批准、Fact/Claim版本、品牌规则、ContentMaster、资产类型、获批平台范围、人类确认的素材权利、CTA、审核路径、对象Owner、风险分类引用及所需批准角色。DEC-03未签署或内容未分类时，必须预置公司负责人额外`ApprovalGrant`要求；DEC-04下抖音、小红书、B站和公众号均为`MANUAL`，不得注入平台凭据、账号秘密或Connector能力。视频号只有上游scope change-impact获批后才能进入加载候选，当前为`DORMANT_SCOPE_CANDIDATE`。

## 方法与人工点

建立内容主张-证据映射→生成平台中立ContentMaster→产品/品牌边界自检→按当前授权范围选择SKL-BG-07～11中的最小平台Skill→分别生成PlatformVariant候选及native extension→记录每版删改/CTA/风险→核对素材权利→按`IF-APPROVAL-GRANT-01`形成所需批准清单→送产品表达与品牌成品人工审核。不得把一个平台的结构机械复制给另一个平台；源Skill中的`publish_ready`只映射为平台质量门候选。未分类外部内容必须列出公司负责人额外批准；价格、促销、交期、客户承诺、新Claim、法律/隐私和舆情类内容始终走高风险路径，Agent不得删除风险标签、改写为低风险或用渠道变体规避批准。创意方向、风险裁决与最终成品由具名人类判断。

## 输出、停止与完成

`ContentMaster/PlatformVariant`：source asset、platform、body/script、Fact/Claim refs、version/hash candidate、native extension、difference summary、asset list/rights、risk labels、risk classification ref、required approver roles、review status。停止进入发布准备：未批事实、平台未在授权范围、未分类外部内容缺公司负责人额外Grant要求、高风险类别被要求降级、敏感主题、绝对承诺、版权未知、当前平台规则不可核验或对象漂移。Skill完成只表示候选稿可送审：变体不改变核心事实、不形成新Claim、草稿标签明显；不表示内容获批或可发布。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`approval.status`、`content.create_variant_candidate`、`object.create_candidate`、`object.submit_review`、`handoff.create`；五个Playbook均不新增Tool，平台Connector allowlist为空。降级：生成一个安全ContentMaster/结构、风险与缺失素材清单，不伪造平台原生适配完成或发布就绪。测试：BG03-T01四个R0平台分别适配；T02多平台事实一致且结构原生；T03渠道变体新增Claim；T04未分类内容缺额外Grant；T05高风险降级诱导；T06版权/规则未知；T07版本漂移；T08审核退回；T09 PII/平台直发诱导；T10源Skill hash不符；T11源`publish_ready`越权；T12视频号scope gate；T13 Tool失败。
