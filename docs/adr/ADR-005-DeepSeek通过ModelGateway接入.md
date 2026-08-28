# ADR-005：DeepSeek 通过 Model Gateway 接入

## 状态

已实现并于 2026-08-21 完成 PMA、BGA、MO 三岗位真实 Run 验收。

## 决策

R0 默认模型为 `deepseek/deepseek-v4-pro`。Runtime Worker 调用三个 Hermes
Gateway；Hermes 使用 `deepseek` Provider，但把 `DEEPSEEK_BASE_URL` 指向内部
`http://model-gateway:8010/v1`。DeepSeek Provider Key 仅保存在本机
`.runtime/secrets/model_api_key`，以只读目录挂载到 Model Gateway；Hermes 只持有
随机的项目内部 Gateway 令牌。

统一前端通过 Caddy 的本机 `/local-admin` 控制路径配置 Key。Caddy 注入内部令牌，
Runtime API 原子替换 Secret 文件并调用 Model Gateway 验真；失败时恢复旧 Key。
Worker 从 `.runtime/control/model-runtime.json` 动态读取真实执行开关，因此配置成功后
不需要从网页操作 Docker 或重启 Agent。

Model Gateway 只允许 `/v1/models`、`/v1/chat/completions` 和 `/v1/responses`，
并把生成请求锁定为 `deepseek-v4-pro`。它替换客户端 Authorization，不向上游
转发内部令牌；上游流式响应和请求 ID 原样返回。Key、内部令牌或上游错误正文
不得进入日志、Run failure 或测试证据。

## 失败关闭

- Secret 为空或内部令牌缺失时 `/health/ready` 返回 503。
- `auth deepseek` 在配置开始时先关闭真实执行。
- 只有 Model Gateway 通过 DeepSeek `/v1/models` 验真后，脚本才把
  `HERMES_EXECUTION_ENABLED` 设为 `true`。
- 不允许验真失败后静默切换 Codex、OpenRouter 或其他模型。
- 真实 Run 成功只产生 `evidence_accepted`，业务 `fulfilled` 仍由人类确认。

## 结果

凭据与岗位 Profile 解耦，PMA、BGA、MO 共用受控模型出口；Runtime 页面从服务端
读取 Provider、模型和真实/合成状态，不再把 Demo1 的原型配置当作运行证据。

2026-08-21 的三个受控合成场景均由 `deepseek/deepseek-v4-pro` 完成：Runtime 为
`evidence_accepted`、Hermes 为 `completed`、Commitment 为 `submitted`。PMA 只写入
`fact/claim`，BGA 只写入 `campaign/content`，MO 只写入 `review`；三者均未自动进入
`fulfilled`。可复现证据见 `docs/evidence/第2周_DeepSeek三岗位真实验收_2026-08-21.md`。
