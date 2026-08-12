# SKL-PM-02 用户、竞品和场景研究 v0.3

> `skill_id: SKL-PM-02` · `version: 0.3.0-freeze-candidate` · 适用：`DROLE-01`

## 业务与追溯

对应`PMA-R02`、`CAP-03`、`EVT-03`、`DATA-04`、`GOV-02`、`UAT-04`。

## 触发与不触发

- 触发：明确研究任务、定位复核、市场变化或去敏销售反馈聚合。
- 不触发：自行浏览或抓取外部来源；处理客户级画像/PII；把研究候选正式化。

## 前置与输入

研究问题、目标决策、范围、时间窗、允许来源类别、人类提供的SourceRef、输出受众、截止与数据限制。若没有SourceRef，只能提出研究计划与资料清单。

## 方法与人工点

拆分问题→设计来源组合→用SKL-SH-01分类→分离观察/反馈/观点/推测→比较细分、场景、替代方案→寻找反证→说明样本与时效偏差→形成可行动发现和待验证项。研究方法取舍和正式洞察由产品营销负责人判断。

## 输出、停止与完成

`ResearchFinding`含question、method、source refs、findings、contradictions、scope、limitations、confidence note、opportunity candidates、unknowns、validation plan。停止：来源不可合法使用、要求无授权画像、证据不足却要求确定结论、竞品材料时效未知。完成：回答原问题；单条反馈未泛化；网页文案未当产品事实；所有结论保持候选。

## Tool、降级与测试

最小Tool族：`knowledge.search_scoped`、`evidence.create_note_candidate`、`knowledge.submit_candidate`；R0不存在浏览/HTTP/平台Connector。降级：只交研究设计、缺口和需人工提供SourceRef清单。测试：PM02-T01多源研究；T02单一来源；T03反证；T04时效失效；T05外部搜索诱导；T06 PII画像；T07注入；T08无答案。验收以诚实边界而非结论数量为准。

