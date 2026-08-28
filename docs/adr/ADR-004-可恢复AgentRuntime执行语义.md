# ADR-004：可恢复 Agent Runtime 执行语义

- 状态：Accepted
- 日期：2026-08-18
- 适用范围：Runtime API、Runtime Worker、Hermes Gateway、Organization MCP、Demo1 API 模式

## 背景

原始 Worker 直接把 `AgentRun.status` 从 `queued` 改为 `accepted/running/终态`。如果 Worker 在启动 Hermes 前后崩溃，系统无法回答三个问题：谁正在执行、旧 Worker 是否还能写回、再执行是否会重复外部副作用。单一 Run 记录也会覆盖失败历史，不足以支持审计和故障复盘。

## 决策

### Run 与 Attempt 分离

`AgentRun` 表示用户可见的任务意图与最终结果；`AgentRunAttempt` 表示一次可租约的物理执行。Attempt 只追加，以 `(run_id, attempt_no)` 保证唯一，旧 Attempt 不会被新结果覆盖。

### 原子 Claim 与 Fencing

Worker 通过 `SELECT ... FOR UPDATE SKIP LOCKED` 锁定一条 `queued` Run，并在同一事务中创建 Attempt、设置 Lease、保存随机 `lease_token`。任何 heartbeat、Hermes Run ID 记录或终态写回都要同时匹配：

```text
run.current_attempt_id == attempt.id
attempt.lease_token == worker.lease_token
attempt.lease_until >= now
```

默认 Lease 为 30 秒，Heartbeat 为 10 秒。只要上述任一条件不成立，旧 Worker 的写回就被拒绝。

### 恢复规则

| 过期时的外部状态 | 决策 | 理由 |
|---|---|---|
| 尚未记录外部启动意图且未超 Attempt 上限 | 旧 Attempt 标记 `lost`，Run 重新 `queued` | 尚未向 Hermes 发起创建请求，可安全恢复 |
| 尚未记录外部启动意图但已达 Attempt 上限 | Run `failed` | 防止无限重试 |
| 已记录外部启动意图，结果不明 | Run `unknown` | 即使 `hermes_run_id` 尚未来得及回写，也可能已有外部副作，禁止自动重试 |
| 已有 `hermes_run_id`，结果不明 | Run `unknown` | 可能已有外部副作，禁止自动重试 |
| Hermes 明确 `failed` 且 `retryability=safe` | 在上限内创建新 Attempt | 失败方明确声明可安全重试 |
| Hermes 明确 `cancelled` | Run `cancelled` | 只信任外部执行器的明确终态 |

### 取消语义

`queued` Run 可直接取消。`accepted/running` Run 只记录 `cancellation_requested_at`，Worker 调用 Hermes `/stop`后继续查询；只有 Hermes 明确返回 `cancelled` 才写入该终态，停止结果不明则进入 `unknown`。

Worker 在发送 `POST /v1/runs` 前把 Attempt 标记为 `external_starting`。这是一个保守的派发意图点：崩溃可能发生在请求发送前，也可能发生在 Hermes 已接受请求但响应尚未持久化时。恢复器无法证明哪种情况发生，因此该状态租约过期必须进入 `unknown`，不能仅凭 `hermes_run_id` 为空自动重试。

### 审计与观测

所有 Run 状态变化经过同一个迁移服务，记录顺序号、原因、执行者、Attempt 和 correlation ID。API 创建 Run 时持久化 W3C Trace Context，Worker 消费时恢复上下文。MCP 交通无法保证原始父子传播时，使用 Attempt Trace 作为 Span Link，不伪造连续 Trace。

## 结果与取舍

- 优点：崩溃语义可解释；可防止旧 Worker 写回；失败历史可审计；恢复策略有测试证据。
- 代价：增加了事务和状态机复杂度；运行中撤权与真正的工具级幂等仍需下一阶段完善。
- 非目标：本轮不实现完整 DAG、动态插件市场、生产级沙箱或 Kubernetes。
