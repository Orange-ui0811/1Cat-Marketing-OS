# ADR-003：Hermes 0.20.0 可复现镜像构建

## 状态

已采纳，R0。

## 背景

固定源码快照为 Hermes Agent v0.20.0（2026.8.3），commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb`。直接执行该快照的上游 Dockerfile 时，Docker Desktop 代理对 Debian 软件源持续返回间歇性 502，导致依赖层无法稳定完成。官方 `nousresearch/hermes-agent:latest` 的镜像内版本是 0.20.0，但 OCI revision 为另一提交，因此不能直接作为本项目 Hermes 应用镜像。

## 决策

使用按摘要固定的官方 0.20.0 镜像作为二进制依赖底座，然后在项目构建中用 `vendor/hermes-agent` 全量覆盖 `/opt/hermes` 应用源码，并把固定 commit 写入 `.hermes_build_sha`。构建会同时断言 `pyproject.toml` 版本与 `UPSTREAM_COMMIT`。

容器运行时直接以 UID 10000 启动 Hermes CLI，不运行官方镜像的 root/s6 入口。三岗位使用 `-p pma|bga|mo` 与共享项目 Hermes 根目录，Profile 数据和锁仍由 Hermes 原生机制隔离。

## 后果与验证

- 不修改 vendor 快照，也不依赖未证明的浮动 `latest` 行为；底座使用不可变 digest。
- 原生依赖闭包来自同版本官方发布镜像，应用 Python、配置、Profile、Gateway 和 Tool 代码来自指定 commit。
- 每次构建后必须验证 Hermes 版本、`.hermes_build_sha`、非 root UID、三 Profile Gateway 和配置级 Tool 集合。
- 若 Debian 构建链恢复稳定，可重新评估直接从 vendor Dockerfile 全量构建；切换前需比较 SBOM 与端到端测试结果。
