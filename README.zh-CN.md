# agent-workstyle 2.0.0：Codex 可选持久配置模式

把“理解现有工作、讲清进度和决策、明确授权后持续完成、完整记录全部要求”带到另一台电脑。核心 Skill 适用于三家；本文安装脚本的持久配置模式仅适用于 Codex。三家原生安装见下文。

## 适用范围

目标电脑需要已有可用的 Codex 和 Python 3.11 或更高版本。安装工具只用 Python 标准库，不联网、不安装依赖、不选择模型、不复制账号。macOS 已做隔离目录实测；Linux、Windows 按跨平台路径和文件接口设计，尚未在这两个系统实机验收。Codex 客户端版本和组织管理策略可能限制自定义指令，安装检查不能代替真实新会话验证。

## 与原生 Skill 安装的区别

推荐的 GitHub 原生安装方法见 [README.md](README.md)：它只安装技能，不改全局配置。本文的完整配置模式会额外写入持久指引，适合明确选择这项功能且尚未原生安装同名技能的用户。两种模式不叠加；已经原生安装时无需再运行本文安装命令，直接使用 `$agent-workstyle`。不要为叠加模式删除未知文件或强行覆盖。

## 带到新电脑

解压整个包，打开终端并进入解压后的 `agent-workstyle` 目录。macOS/Linux 使用 `python3`，Windows 通常使用 `py -3` 或 `python`；先确认版本不低于 3.11。以下命令中的 `python3` 在 Windows 换成相应入口。

```text
python3 --version
python3 scripts/setup.py
python3 scripts/setup.py install
python3 scripts/setup.py check
```

第一条工具命令只预览，不创建目标文件。明确执行 `install` 才安装。默认目标为 `CODEX_HOME` 环境变量指定的位置，未指定则为当前用户目录下 `.codex`。可用 `--codex-home "路径"` 指向另一个 Codex 目录，路径包含空格或中文时加引号；例如先在一个空的临时目录练习。

安装后新建 Codex 会话。项目工作会按配置指引读取 skill；也可明确说“使用 $agent-workstyle 接续这个项目”。普通独立问答直接回答。已有会话不保证自动刷新；如果客户端没有加载新配置，按该客户端支持的方式重新启动或显式调用 skill，不关闭沙箱或绕过组织策略。

## 会改什么

- 在目标 Codex 目录的 `skills/agent-workstyle/` 安装本包说明与工具。
- 仅在 `config.toml` 的 `developer_instructions` 中追加一段带标记的指引；保留已有指令和其他键，不改模型、权限、供应商、MCP、项目配置或 AGENTS.md。
- 在目标 Codex 目录的 `workstyle-state/` 保存安装摘要、原配置私有备份和操作锁。POSIX 上新备份目录权限为 0700、文件为 0600；Windows 的实际保密性还取决于目标用户目录的 ACL，请放在该用户私有目录。不要分享原配置备份，它可能含秘密。

同版本重复安装不重复追加。不覆盖未知同名 skill，不自动升级已安装的不同内容；遇用户修改、符号链接、无效配置或管理段冲突时停下并说明。项目原有流程继续生效，无现有流程时才按需读包内开发流程；不会批量初始化项目或复制私人聊天。

## 如何看是否有用

`check` 验证已安装文件摘要、管理段和私有备份完整性；不调用模型、不证明行为必然正确。建议在新会话中观察：

1. 普通问题能直接回答。
2. 接手项目先找到已有说明、要求和进度，而不是要求你重讲。
3. 已明确授权的工作继续完成，不因内部检查切换反复确认。
4. 遇确需你决定的事项，讲清选择、推荐和后果；正文能独立看懂。
5. 你补充要求后，记录原话并归并到同一清单，区分已提出、已落实、已验证和待观察。

不拿“文件装上了”代替“每次行为都正确”。本包没有自动 hook、CI 或权限拦截，也不会自动获得浏览器、发布或生产权限。

## 撤销

```text
python3 scripts/setup.py uninstall
python3 scripts/setup.py uninstall --apply
```

第一条只预览。显式 `--apply` 才移除本包管理的指令段，将摘要匹配的文件移到私有恢复目录；原配置未有其他变化时按原件恢复，有后续其他改动时保留它们，只移除完整管理段。用户新增的其他文件和私有备份保留。普通写入/文件占用异常会尝试恢复撤销前状态，无法恢复的内容保留并说明位置，不覆盖外部并发修改。已安装文件或管理段被修改时拒绝自动撤销，先人工核对；不删除整个 skills 目录，不改 Claude。

版本更新先检查并明确撤销旧版，再装新版。若进程被强制中断、断电或出现锁残留，先核对现场与私有备份；不自动删锁、不覆盖未知变化，也不承诺跨多个文件的数据库式事务。

## 包的组成与独立性

`SKILL.md` 是入口；`references/` 含无外部依赖的开发流程与最小记录约定；`scripts/setup.py` 安装、检查和撤销；`tests/` 用于隔离验收。核心能力：接手现有工作、过程清楚、决策清楚、业务语言、正文解释结果、连续推进、完整记录。

本包没有机器台账、用户名、主机地址、项目数据、凭据或真实授权。目标项目的有效用户决定和权限必须重新核对，不能把源电脑的历史授权带到新电脑。

开发者可在解压目录执行 `python3 -m unittest discover -s tests -v`，测试只使用临时 Codex 目录，不触及真实用户配置。发布 SHA256 清单用于确认包内文件未变化，不是签名或来源可信证明。

## 三家原生安装入口

仓库地址 `https://github.com/Harviewang/agent-workstyle`。可分别把以下说明发给对应客户端：

- Claude：将完整仓库克隆/复制到 `~/.claude/skills/agent-workstyle/`，新会话使用 `/agent-workstyle`，不要覆盖未知目录。
- Codex：用官方 skill-installer 安装 `https://github.com/Harviewang/agent-workstyle`，参数 `--repo Harviewang/agent-workstyle --path . --name agent-workstyle`，新会话使用 `$agent-workstyle`，保留已有配置。
- Gemini：先查本机帮助，再运行 `gemini skills install https://github.com/Harviewang/agent-workstyle`，新会话检查技能发现。使用 agy 时克隆到 `~/.gemini/config/skills/agent-workstyle/` 或项目 `.agents/skills/agent-workstyle/`；部分账号层级无法使用 Gemini CLI 时改用 agy。

各家独立新会话和只读检查方式见 [clients.md](references/clients.md)。原生安装保留完整 references 与 profiles；本文持久模式沿用原工具的核心文件清单，仅复制开发流程、记录约定等核心文件，新增调度/切换/客户端参考及档案示例从来源仓库读取，不宣称已复制完整包。核心流程自身包含独立性底线。

## 从旧名迁移：两种模式分开

- 原生安装模式：按原客户端机制卸载 `codex-workstyle`，再安装 `agent-workstyle`；不调用 setup.py 撤销原生安装。
- Codex 持久配置模式：先用 **1.0.1 的原始 setup.py** 运行 `uninstall` 预览，再运行 `uninstall --apply` 撤销旧名配置段，保留私有备份；随后使用新版本安装。新版不能替旧版撤销旧名。

两种模式不叠加，切换时先撤销原模式再装新模式。旧显式调用 `$codex-workstyle` 改为 `$agent-workstyle`。目录名称对应：`codex-workstyle/` → `agent-workstyle/`。

## 私有档案与验证限制

个人厂商/能力档位映射放 `~/.config/agent-workstyle/profile.toml`，格式见 [profiles/example.toml](profiles/example.toml)；真实型号、订阅、用户名、本机绝对路径、聊天与工作记录不入库。无档案时按探测到的 CLI 决定可用厂商，鉴权和额度未知就标未知。本包不新增自动探测或路由功能。

真实加载需在临时目录原生安装后开新会话，由独立测试者对照 routing.md 判定。只能显式读 SKILL.md 时标“非原生加载”，只算部分验证，原生加载待完成，不能宣称三家均已验证。
