# ADR-001：Hermes凭据与Profile隔离

状态：Accepted for R0

Hermes 0.20.0的OpenAI Codex OAuth刷新令牌为单次使用，不能为PMA、BGA、MO复制三份凭据。R0使用一个项目专用Hermes根凭据库，三个进程分别以`profiles/pma`、`profiles/bga`、`profiles/mo`为`HERMES_HOME`，通过Hermes全局Profile回退、文件锁和刷新写回共享认证状态。

项目认证必须创建独立OAuth会话，不导入、不复制、不修改用户现有`~/.hermes`与`~/.codex/auth.json`。由于Hermes自带Proxy不支持Codex OAuth，Mac Codex模式由Hermes直接访问Provider，出口由网络代理限制；Linux API Key模式使用Model Gateway集中持有Secret。

