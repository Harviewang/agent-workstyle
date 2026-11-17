# 客户端安装与独立新会话

以下是操作说明，不表示本版本已在三家真实加载。先确认目标客户端版本、组织策略与本机 `--help`；安装可能联网并需要用户授权。模型可用性与 CLI 可用性分别核实。本包不提供统一安装器或通用权限开关。

仓库地址 `https://github.com/Harviewang/agent-workstyle`。示例不携带源电脑用户名或路径。原生安装应保留完整仓库的 SKILL.md、references 和 profiles。

## Claude

把完整仓库克隆或复制到 Claude Code 的用户 Skill 目录 `~/.claude/skills/agent-workstyle/`，SKILL.md 位于该目录根部。已存在目录先核对，不能覆盖未知内容：

```sh
git clone https://github.com/Harviewang/agent-workstyle ~/.claude/skills/agent-workstyle
```

安装后开启新会话，显式调用 `/agent-workstyle` 并要求说明已读规则。独立检查另起进程，不使用继续/恢复参数：

```sh
claude -p --permission-mode plan --tools Read,Glob,Grep "使用 /agent-workstyle，只读检查指定产出；先读原始需求与任务书，不修改文件、不启动浏览器。"
```

这里只提供读取类工具与规划权限用于静态审计；需要执行测试时，由牵头方准备隔离副本、获准命令与写入边界后另行派发，不能把静态阅读当作已执行测试。

## Codex

使用已安装的官方 skill-installer，参数示意如下（脚本位置由目标客户端确定，本仓库不提供此命令）：

```text
install-skill-from-github.py --repo Harviewang/agent-workstyle --path . --name agent-workstyle
```

也可将公开仓库地址发给 Codex，要求按其 skill-installer 安装，保留已有配置。安装后开启新会话，显式使用 `$agent-workstyle`。独立检查使用新的 `codex exec`，不调用 resume 或 fork：

```sh
codex exec --sandbox read-only '使用 $agent-workstyle，只读检查指定产出；先读原始需求与任务书，不修改文件、不启动浏览器。'
```

只读沙箱用于静态审计；独立测试/回归放在隔离副本并给最小必要写入权限，不改业务源码和验收基线。Codex 可选持久配置模式见 README.zh-CN.md，仅适用 Codex，不与原生安装叠加。

## Gemini

Gemini CLI 使用自带的 Skill 安装命令；本地目录或 Git URL 的支持情况先查目标版本帮助：

```sh
gemini skills install https://github.com/Harviewang/agent-workstyle
```

安装后重新开启会话，要求使用 agent-workstyle，并检查技能发现及固定问题回答。独立检查不用恢复参数，另起进程：

```sh
gemini --approval-mode plan -p "使用 agent-workstyle，只读检查指定产出；先读原始需求与任务书，不修改文件、不启动浏览器。"
```

agy（Antigravity CLI）是另一调用器，不是另一厂商。按其内置 agy-customizations 文档，Skill 放在定制根的 `skills/<name>/`：项目级 `.agents/skills/`（也认 `.agent/`、`_agents/`、`_agent/`），全局 `~/.gemini/config/skills/`；版本变化时以该文档为准。

```sh
git clone https://github.com/Harviewang/agent-workstyle ~/.gemini/config/skills/agent-workstyle
```

部分账号层级可能无法使用 Gemini CLI（如 IneligibleTierError），改用 agy。可另起只读检查进程：

```sh
agy --mode plan --sandbox -p "只读检查指定产出，先明确读取 SKILL.md 和所需 references；不修改文件、不启动浏览器。"
```

上面检查命令显式读取文件，本身不证明原生加载；原生加载以新会话能自行发现并使用 agent-workstyle 为准。先按本机帮助核对参数，不能照搬其他 CLI 的选项。

## 验证与只读边界

新进程必须未参与对应产出的编写或修改，不能通过恢复作者会话充当独立者。静态审计只读；工具权限/沙箱是实际控制，提示词只表达要求。执行测试另用隔离副本，保留真实输出；不禁用权限检查，不赋予额外浏览器许可。

分别问：“只有本家可用，L2 改动谁审？”“三家都在，Claude 写的方案谁审？”要求读取 routing.md 并对照对应行，由独立测试会话判定，不能由实施方自签。鉴权无法复用时可显式读取 SKILL.md，标“非原生加载”，只算部分验证，原生加载保持待完成；不能宣称三家均已验证。命令退出成功、文件存在和回答正确均不能单独证明原生加载。
