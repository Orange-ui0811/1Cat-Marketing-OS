# 1Cat Human × Agent OS 前端原型

这是 1Cat 的统一正式前端源码。八类页面现在直接读写服务端 Marketing Case、Commitment、
Handoff、Approval、Knowledge、Run、Attempt 与最终方案；不再把独立“完整流程页”作为主操作入口。
Compose 的 `workspace` 镜像将它交付到 8080，PMA Runtime 研修页继续保留。

正常使用时执行项目根目录的 `./bin/1cat up`，然后打开
`http://localhost:8080`。进入“Agent 配置 → 模型与权限”即可安全配置和验证 DeepSeek
Key；Key 只写入项目 `.runtime/secrets`，不会进入浏览器存储。

## 本地原型模式（默认）

```bash
npm install
npm run dev
```

开发服务器打开：`http://localhost:4173/`，并把后端请求代理到 8080。

API 模式下，任务、协作、对象、决策、异常、Daily、Agent 配置和运行诊断共用同一个服务端 Case；
用 `/?view=runtime` 可进入 PMA 研修页。`/?view=workflow` 仅作为旧链接兼容入口。

## Runtime API 模式

先在 `D:\媒体架构\1Cat-Marketing-OS` 启动后端，然后在 Git Bash 中运行：

```bash
cd /d/媒体架构/demo1/demo1
VITE_RUNTIME_MODE=api npm run dev
```

打开 `http://localhost:4173/?view=tasks`，使用 Runtime 的 `admin` 账号登录。完整流程使用服务端九阶段 Case 状态机：

```text
Brief → MO规划 → PMA Fact/Claim → BGA Campaign/Content
→ simulated发布 → 合成反馈 → MO复盘；每个关键阶段由人类门禁推进
```

Token 只保存在 `sessionStorage`；401 会清除 Token 并返回登录页。Run 每 2 秒轮询，网络失败时保留最后可信状态。

## 验证

```bash
npm run build
npm run e2e
```

Playwright 覆盖登录、只通过八类页面完成案例、blocked/unknown 对账、刷新/历史恢复、
PMA 黄金链路和 401 恢复。`apps/workspace` 是正式源码，镜像同步脚本保证 `demo1/demo1` 不漂移。

## 推荐演示路径

1. 默认以“产品营销负责人”进入“我的今天”。
2. 点击“审核小红书成品中的产品表达”，查看锁定版本、证据、PMA建议和人工决定。
3. 点击“与MO协作”，进入唯一默认对话入口；可以直接描述业务目标，或上传图片、PDF、Word、表格、PPT等资料。
4. 发送消息后，查看Marketing Orchestrator如何复述目标、识别Owner与审批边界，并给出类似Codex Plan Mode的协作计划。
5. 在计划卡中选择“按建议计划推进”“只整理候选”或“暂不开始，保持HOLD”，也可以先点“调整计划”继续对话。
6. 确认选择后，查看MO把任务并行分派给PMA/BGA，并标明每项专业结果最终由哪位人类Owner判断；Plan确认不是正式业务批准。
7. 从左上角切换为“品牌营销负责人”，查看风险优先的早检、最终内容批准和Lead移交；新工作仍统一从MO进入。
8. 打开“数字岗位运行”，查看唯一协作入口，以及PMA/BGA的只读执行详情、任务来源、Skill与Memory边界。
9. 打开“HOLD与风险”和“跨中心协作”，查看暂停、恢复条件和MO的推进方式。
10. 打开“日清与复盘”，确认系统怎样基于业务对象和人工决定生成日结。
11. 最后打开“运行诊断”，查看合成Runtime验证与Agent真实履职的隔离。

## 当前边界

- API 模式下八类页面的业务事实和操作均来自 Runtime；本地模式仍只用于离线界面原型；
- API 模式可显示 Hermes 运行结果，但 Run 成功不等于业务履约；
- 发布只生成 `simulated` 回执，`external_effect=false`，不登录或写入真实平台；
- 本前端用于学习、联调和演示，不是生产实现。
