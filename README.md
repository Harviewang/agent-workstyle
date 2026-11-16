# Codex Workstyle

一个让 Codex **讲清进度、说明决策、记全要求，并在已授权范围内连续完成工作**的独立开源 Skill。

遵循 [Agent Skills](https://agentskills.io) 的自包含目录方式。只改善 Codex，不要求安装或修改 Claude，也不需要外部服务、指定模型或其他 Skill。

## 把地址发给另一台电脑上的 Codex

把下面这段话发给已经可用的 Codex：

```text
请用 skill-installer 安装 https://github.com/Harviewang/codex-workstyle 。
仓库中的技能路径是 .，安装名称为 codex-workstyle。
只安装技能，保留已有配置，不修改 Claude。安装后核对文件并告诉我如何使用。
```

安装后在新会话说：

```text
使用 $codex-workstyle 接续这个项目，先核对已有要求和进度，再继续已批准的工作。
```

技能可由客户端按描述自动选择，也可显式调用；贴链接只是安装入口，不意味着跳过安装、网络权限或客户端策略。旧会话不保证自动刷新。若当前客户端没有 skill-installer，可让它从此公开仓库下载并审阅文件，再安装到该客户端支持的 Codex skills 目录，不复制账号或关闭权限控制。

给能运行官方安装器的环境，等价参数是：

```text
install-skill-from-github.py --repo Harviewang/codex-workstyle --path . --name codex-workstyle
```

上面是官方 skill-installer 辅助脚本的参数示意，不是本仓库提供的独立命令。脚本实际位置由目标电脑的技能目录决定，不硬编码源电脑路径。

## 它会怎样协作

- **接手**：找到现有项目说明、完整要求、进度与有效授权；项目已有流程就沿用，没有时按需使用包内流程。
- **沟通**：说清做了什么、结果怎样、下一步和确需用户决定的事项；给推荐与后果，技术依据作补充。
- **推进**：同一已授权小步内完成实施、检查、修复和交付，减少重复确认；新增范围和独立权限继续区分。
- **记录**：保留原话来源，累加前后要求，明确已提出、已落实、已验证和待观察。

普通问答直接回答。不会为安装技能而修改 Claude、读取私人聊天或自动操作生产、浏览器、提交和部署。

## 两种安装模式

**推荐：原生 Skill 安装。** 上面的 URL 方法只安装技能，便于显式使用，不修改 `config.toml`。原生安装的移除/更新沿用安装它的客户端机制，本仓库完整模式的撤销命令不管理它。

**可选：持久工作指引。** 如果明确希望每次项目工作都加载规范，而且尚未原生安装同名 Skill，可从仓库源码使用 [完整模式说明](README.zh-CN.md)。该工具仅依赖 Python 3.11+ 标准库，默认只预览，显式安装才追加指引，并提供备份、检查和撤销。不要叠加两种模式或覆盖同名未知文件。

## 验证与边界

在仓库目录运行：

```text
python3 -B -m unittest discover -s tests -v
python3 scripts/check_public.py --index
```

Windows 可用 `py -3` 或 `python` 替换 `python3`，Python 版本需不低于 3.11。GitHub Actions 配置了 macOS、Linux、Windows 与 Python 3.11/3.13；实际通过情况见仓库 Actions，不能把配置矩阵说成已经实测通过。

已有本地 macOS 隔离测试和新 Codex 会话情境验证。这些不保证每次模型行为正确，不是浏览器/生产权限，不是自动 hook 或 CI 门禁，也不迁移源电脑的历史授权。

## 隐私和开源范围

只发布 `PUBLIC_FILES.json` 明确列出的通用说明、原创工具、合成测试和 CI；新建独立 Git 历史，不携带来源项目历史。公开目录不包含个人配置、私有备份、凭据、真实项目数据、聊天原话、工作台账、主机信息或会话日志。扫描仅是辅助，发布前仍须逐文件核对。

安装工具在用户自己的 Codex 目录生成的私有备份**不属于开源内容**，不能上传到 Issue 或公开仓库。见 [安全说明](SECURITY.md)。

## 结构参考与许可

结构参考 [Anthropic Skills](https://github.com/anthropics/skills)、[OpenAI Plugins](https://github.com/openai/plugins) 和 Agent Skills 标准。只借鉴目录/元数据/引用方式，不复制第三方技能正文；不是 OpenAI 或 Anthropic 官方项目。

本仓库原创内容使用 [MIT License](LICENSE)。
