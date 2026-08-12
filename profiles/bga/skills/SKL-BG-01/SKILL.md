---
name: skl-bg-01
description: SKL-BG-01 渠道与内容环境研究 v0.3。仅用于一猫营销R0候选产物与人工协作，不授予平台写入能力。
metadata:
  source_sha256: c48cf9a0555b00a0bec6a9c5288a4a13492d2048072536ac35dbce76eefc0594
  dormant: false
---

# SKL-BG-01 渠道与内容环境研究 v0.3

> `skill_id: SKL-BG-01` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-02`

## 业务与追溯

对应`BGA-R01`、`CAP-04`、`EVT-03/11`、`DATA-04/08`、`GOV-02/10`。

## 触发与不触发

- 触发：Campaign准备、平台规则/趋势变化、内容表现异常或周期复盘。
- 不触发：自主浏览/抓取平台；登录账号；把热点直接变成发布指令。

## 前置与输入

研究问题、抖音/小红书/B站/公众号范围、受众、品牌边界、人类提供的SourceRef、时间窗、目标决策与批准路径。没有SourceRef时只能形成研究计划。

## 方法与人工点

识别平台约束→证据分类→区分规则、观察与推测→比较内容形态、受众信号和风险→寻找反例→形成机会候选与验证设计。品牌营销负责人判断是否采纳；敏感议题、舆情和账号权限交人类。

## 输出、停止与完成

`ChannelResearch`：platform、time window、source refs、audience signals、content opportunities、constraints、risks、reusable patterns、hypotheses、validation plan。停止：政策不明、来源不合法、版权/舆情/敏感议题、需要外部账号。完成：时效可见，不把热度当业务价值，不建议违规采集或跟风发布。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`evidence.create_note_candidate`、`knowledge.submit_candidate`；R0无浏览/HTTP/平台Connector。降级为资料请求和验证清单。测试：BG01-T01多平台；T02过期规则；T03单一爆款偏差；T04敏感热点；T05版权未知；T06外部登录诱导；T07注入；T08无来源。


