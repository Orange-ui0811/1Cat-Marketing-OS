# 1Cat Hermes OS

一猫营销实验性 AI 原生组织运行系统 R0。系统由三个长期数字岗位组成：

- PMA：产品营销 Agent
- BGA：品牌与增长 Agent
- MO：营销协同 Agent

R0 只生成候选、协作、审核和人工发布任务。抖音、小红书、B站、公众号均为人工发布；视频号保持休眠；真实 PII、自动发布、A2A、关键 Cron 和生产高可用不在范围内。

## Mac 快速开始

```bash
./bin/1cat doctor
./bin/1cat init
./bin/1cat up
./bin/1cat smoke
./bin/1cat e2e
```

打开 <http://localhost:8080>。首次登录用户为 `admin`，密码在初始化后写入 `.env` 的 `INITIAL_ADMIN_PASSWORD`；不要复制到文档、日志或部署包，共享部署应在首次使用后立即修改。

需要运行真实 Hermes Agent 时：

```bash
./bin/1cat auth codex
./bin/1cat restart-agents
```

该认证创建项目专用 Hermes 会话，不读取或改写用户现有 `~/.hermes`。

## 常用命令

```bash
./bin/1cat status
./bin/1cat logs
./bin/1cat backup
./bin/1cat restore <backup-directory> --confirm
./bin/1cat package arm64
./bin/1cat package amd64
```

详细说明见 `docs/deployment/部署与运维手册.md`。

业务人员请按 `docs/一猫营销_R0业务使用说明_v1.0.md` 完成 Brief → PMA → BGA → 人工发布 → LeadStub → 销售反馈 → MO复盘闭环。
