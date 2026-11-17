# agent-workstyle 2.0.0

让 Claude、Codex、Gemini **讲清进度与决策、记全要求，并在已授权的小步内持续完成工作**的公开 Skill。支持任一家或任意组合，按能力档位分工，如实记录降级；个人型号映射留在本机私有档案。

## 发给目标客户端安装

仓库地址：`https://github.com/Harviewang/agent-workstyle`。安装保留已有配置与权限，不复制账号；安装后开真正的新会话。三段任选对应客户端，不需要同时安装三家。

**Claude：**

```text
请把 https://github.com/Harviewang/agent-workstyle 的完整 Skill 仓库安装到 Claude Code 用户 Skill 目录
~/.claude/skills/agent-workstyle/，根部保留 SKILL.md。
不要覆盖未知目录或修改已有配置。安装后开新会话，用 /agent-workstyle 检查加载。
```

**Codex：**

```text
请用官方 skill-installer 安装 https://github.com/Harviewang/agent-workstyle，仓库技能路径为 .，名称 agent-workstyle。
等价参数：--repo Harviewang/agent-workstyle --path . --name agent-workstyle。
只安装 Skill，保留已有配置。安装后开新会话，使用 $agent-workstyle 检查加载。
```

**Gemini（agy / Antigravity CLI）：**

```text
请把 https://github.com/Harviewang/agent-workstyle 克隆到 ~/.gemini/config/skills/agent-workstyle/（全局）
或项目根的 .agents/skills/agent-workstyle/（仅该项目），根部保留 SKILL.md。
保留已有配置。安装后开新会话，确认能发现 agent-workstyle。
```

**Gemini CLI：**

```text
请用 gemini skills install https://github.com/Harviewang/agent-workstyle 安装 agent-workstyle，然后用 gemini skills list 确认已启用。
```

部分账号层级可能无法使用 Gemini CLI（例如报 IneligibleTierError），这时改用 agy。

更多安装、新会话与只读检查命令见 [clients.md](references/clients.md)。安装方式由客户端提供，本包不新增调度程序，不要求指定型号或其他厂商。

## 协作与审查

先读取项目说明、完整要求、进度及有效授权；已有流程就沿用。普通问答直接回答，工程工作按 [workflow.md](references/workflow.md) 分级。正文解释结果与影响，技术依据放附录；同一已授权小步连续做完，新增范围和发布等独立权限继续确认。

独立性：新会话（未参与产出）< 跨模型 < 跨厂。L0 用新会话；L1 优先跨厂，不可用时同厂新会话并记原因；L2 至少一名跨厂审查者。单厂 L0/L1 标“同厂回退”；L2 只能推进到“已修改、待审”，用户明确接受同厂结论才可完成。独立测试、代码审计、回归各用未参与对应产出的不同新会话，自检不代替独立结论。

七种组合和能力档位见 [routing.md](references/routing.md)，切换信号与接替见 [failover.md](references/failover.md)。无档案时按探测到的 CLI 决定可用厂商；命令存在不证明鉴权或额度可用，未知就记未知。个人档案约定 `~/.config/agent-workstyle/profile.toml`，格式见 [example.toml](profiles/example.toml)，实际型号映射不入库。

## 两种模式与旧版迁移

**推荐原生 Skill 模式：** 三家按各自客户端安装，只加载 Skill，不写持久全局配置。从 `codex-workstyle` 迁移时，先按原客户端安装/卸载机制移除旧名，再原生安装 `agent-workstyle`。不删除未知文件，不以本仓库 setup.py 撤销原生安装。

**可选 Codex 持久配置模式：** 仅 Codex 适用，Python 3.11+ 标准库，默认预览，显式安装才写配置，详情见 [README.zh-CN.md](README.zh-CN.md)。从旧版迁移时，先用 **1.0.1 的原始 setup.py** 执行 `uninstall` 预览，再执行 `uninstall --apply` 撤销旧配置段；保留私有备份，然后安装新名。新版脚本不负责撤销旧名。

两种模式不叠加。旧显式调用 `$codex-workstyle` 改为 `$agent-workstyle`；Claude 使用 `/agent-workstyle`。切换模式先按原模式撤销，核对保留内容再安装。目录名称对应：`codex-workstyle/` → `agent-workstyle/`；不搬运源电脑的历史授权。

## 验证与边界

在独立 Git 仓库内运行：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py --index --extra-terms ~/.config/agent-workstyle/private-terms.txt
```

第二条检查暂存内容，更新清单与 SHA256 后先 `git add`。`--extra-terms` 指向仓库外的私有词表（每行一个，如你的用户名、订阅名），只在发布者本机使用，不入库。Windows 可用 `py -3` 或 `python`，Python 至少 3.11。CI 配置三种系统与两个 Python 版本；实际结果以 Actions 为准，配置矩阵不等于已经通过。

本地静态检查、情境回答与真实客户端原生加载是不同证据。若只能显式读 SKILL.md，标“非原生加载”，只算部分验证，该客户端原生加载记待完成，不得宣称三家均已验证。安装检查不保证每次行为正确；本包不是 hook、权限门禁或浏览器/生产授权。

## 隐私与许可

只发布 `PUBLIC_FILES.json` 列明的通用资料、工具、合成测试与 CI。不得提交个人型号、订阅、用户名、本机绝对路径、聊天原话、工作记录、账号或秘密；真实私有档案和安装备份不入库。扫描仅辅助，仍需人工审查，见 [SECURITY.md](SECURITY.md)。

遵循 [Agent Skills](https://agentskills.io) 的目录结构；结构参考 [Anthropic Skills](https://github.com/anthropics/skills) 与 [OpenAI Plugins](https://github.com/openai/plugins)，不复制第三方正文，不是厂商官方项目。原创内容使用 [MIT License](LICENSE)。
