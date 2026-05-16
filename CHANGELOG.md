## 变更记录：飞书渠道入口 + OpenClaw 架构定论（2026-05-10 全天工作总结）

**改动文件**: 无本地代码改动（全部为 OpenClaw 侧配置 + 文档更新）

---

### 一、架构探索结论（为什么 subprocess 直调是正确的）

**背景**：最初以为 OpenClaw 的 Skill 系统可以让 Agent 自动匹配并调用 skill，从而替代 server.py 中的 subprocess.Popen 调用。经过与 OpenClaw 三轮交叉验证，得出明确定论。

**关键发现**：

1. **SKILL.md 只是文档，不是可执行工具**
   - `skills/robot-behavior/SKILL.md` 和 `skills/json-webhook-skill/SKILL.md` 是给人看的说明书，OpenClaw Agent 不会自动加载或执行它们
   - Agent 能读取 SKILL.md 的内容作为上下文参考，但不能把它当作 function call 来调用
   - 唯一实现 Agent 自主调用 skill 的路径是 MCP Tool 封装（需要开发 OpenClaw 插件，工作量大，短期不做）

2. **`sessions_spawn` 不存在于 CLI**
   - 它是 OpenClaw Agent 的内部函数，不是对外暴露的 CLI 命令
   - server.py 无法通过 `subprocess.run(["openclaw", "sessions_spawn", ...])` 来触发 Agent 编排
   - 这意味着 Agent 编排不能被 server.py 程序化调用——它只能在消息渠道入口被用户触发

3. **OpenClaw Gateway 不能替代 server.py 的 HTTP 服务**
   - Gateway 是 WebSocket 服务，用于连接消息渠道（飞书、Discord 等），不是 HTTP API 网关
   - 它不能托管 `/emotion`、`/poll` 等 REST 端点
   - 方案 C（Gateway WebSocket 直连）无公开文档，不可行

4. **最终结论**：
   - **当前 subprocess 直调架构是正确的**——server.py 用 `subprocess.Popen([sys.executable, "analyze_emotion.py", "--input", text])` 是正确做法
   - **OpenClaw 的正确用法是人机对话入口**，不是后端 API 编排引擎
   - 项目形成"双入口并行"架构：HTTP API 一条线 + 飞书 Chat 一条线，共享同一套队列和硬件

---

### 二、飞书渠道入口（已完成并验证通过）

**动机**：在原有 HTTP API 入口之外，新增飞书私聊作为第二入口。两条链路并行，共享同一套 ActionQueue 和 Milk DuoS 硬件。

**架构**：
```
入口1（HTTP）：WebApp → POST /emotion → server.py → subprocess → 队列 → DuoS
入口2（Chat）：飞书私聊 → Gateway → Agent → exec → 队列 → DuoS
```

入口2 的详细链路：用户向飞书机器人发私聊 → OpenClaw Gateway 轮询飞书获取消息 → Agent 收到消息 → Agent 执行 `exec analyze_emotion.py --input "消息内容"` → 解析返回的 JSON → Agent 执行 `exec curl POST /action/milk_duos_001` 入队 → 开发板轮询 `/poll` 拿到动作 → DuoS 执行

**已验证通过的项目**：
- ✅ 飞书应用"陪伴机器人"创建完成（App ID: cli_aa8a846735a11cc8，轮询模式，无需配置回调 URL）
- ✅ 私聊消息能触发 Agent（每条消息都触发，群聊需 @提及）
- ✅ Agent exec analyze_emotion.py 返回正确 JSON（情绪标签 + 动作序列）
- ✅ Agent 能自动 POST /action/milk_duos_001 将动作入队（队列写入验证通过）
- ✅ systemd 服务 webhook-receiver 配置为开机自启 + 崩溃自动重启
- ✅ 安全确认：exec 使用数组传参 `["python3", "analyze_emotion.py", "--input", "..."]`，OpenClaw 设置 `shouldSpawnWithShell=false`，无命令注入风险

**当前限制**：飞书应用为"轮询模式"，非"事件订阅模式"。轮询模式下消息到达有 1-2 秒延迟，对体验影响可接受。

---

### 三、系统提示词设计（给队友：Agent 的行为规范）

**路径**：`~/.openclaw/agents/main/agent/system-prompt.md`（在 ECS 服务器上，不在本地仓库中）

**设计思路**：Agent 的提示词定义了"收到消息 → exec analyze → 解析 JSON → POST 入队 → 一句话回复"的严格工作流，确保 Agent 不会闲聊、不会多问、不会跳过任何步骤。

**包含内容**：
1. **工作流指令**（5 步，每步都有"必须执行"的明确要求）
2. **三套映射表**：
   - Emoji → 情绪中文（9 个映射，如 😊 → 开心）
   - 情绪中文 → 典型关键词
   - 动作编号 → 动作中文名（0-10，如 1=向前移动、6=撒娇/蹭蹭）
3. **异常处理**（5 种场景，每种都有明确的降级策略）
   - 情绪分析失败 → 默认动作 [0] + 告知用户稍后再试
   - /action 写入失败 → 告知用户网络异常
   - 空输入 → 默认动作 [0]
   - 分析超时（>30s）→ 降级
   - 非中文输入 → 仍然分析但用中文回复
4. **禁止行为**（用"禁止"而非"不要"的强硬措辞）
   - 禁止反问用户（如"需要我做某某吗？""要不要让机器人跳舞？"）
   - 禁止闲聊和发表自己的感受
   - 禁止跳过 exec 步骤
   - 禁止向用户解释技术细节

**当前问题**：实测中发现 Agent 仍有闲聊倾向（如回复"要不要让机器人跳个舞？"而非直接执行）。已加强禁止行为措辞，但提示词调优是持续过程。详见 `优化方向.md` 的方向四。

---

### 四、优化方向分工（详见 优化方向.md）

在 `优化方向.md` 新增 11 个优化方向，覆盖：
- **架构集成**（分段阈值、情绪弧线、规则优先+降级链）
- **性能成本**（动作密度、节奏标签、时长加权）
- **稳定性**（长轮询、队列持久化、队列监控）
- **功能扩展**（多渠道、会话追踪）

并完成二人分工：

| 负责人 | 模块 | 优先级最高项 |
|--------|------|-------------|
| 我     | Prompt 策略 + OpenClaw | 优化1(分段阈值) → 优化2(情绪弧线) → 方向七+十(规则优先+降级链) |
| 队友   | 动作序列 + 服务端 | 方向八(长轮询) → 方向十一(队列监控) → 方向一(动作密度) → 方向二(节奏标签) |

执行顺序已按依赖关系排列，见 `优化方向.md` 末尾的表格。

---

### 五、给队友的上下文（你接手前需要知道的）

1. **项目部署在 ECS 上**，本地 D:\Project_SE\openclaw-project-export 是导出备份。上传文件到 ECS 通过 `scp` 到 `/home/admin/openclaw-workspace/`。

2. **server.py（你的主要战场）** 是一个独立的 HTTP 服务（`python services/webhook-receiver/server.py`），启动后监听 8765 端口。核心是 ActionQueue 类（内存队列 + 定时清理），入口是 POST /emotion（调 subprocess 分析情绪）和 GET /poll（DuoS 开发板轮询）。

3. **analyze_emotion.py（我的主要战场）** 是 AI 分析引擎，支持两阶段流程：先分段（segment_story），再逐段生成动作（generate_actions），通过 last_action 参数保证段间连续性。支持 `--provider mock`（本地规则）和 `--provider dashscope`（云端 AI）。

4. **Agent 的 system prompt 在 ECS 上**，路径 `~/.openclaw/agents/main/agent/system-prompt.md`。如果要修改 Agent 行为，去 ECS 上改这个文件，不需要改本地代码。

5. **CHANGELOG 约定**：每次修改后记录"改动文件、改动原因、改动内容（before/after）、验证命令、上传注意事项"。这是给你看的交接记录。









----------------------------------------之前的变更记录----------------------------------------

## 变更记录：安全与可迁移配置化（去硬编码/去绝对路径）

**改动文件**:
- `services/webhook-receiver/server.py`
- `skills/robot-behavior/scripts/director_mode.py`

**改动原因**: 旧实现包含硬编码密钥和服务器绝对路径，无法安全迁移到本地/多环境。

**改动内容**:
- before:
  - `server.py` 写死 `LOG_DIR=/home/admin/...`、`analyze_emotion.py` 绝对路径、`DASHSCOPE_API_KEY=sk-...`。
  - `director_mode.py` 用 `python3 /home/admin/.../analyze_emotion.py` 调子脚本。
- after:
  - `server.py` 新增配置化路径：
    - `LOG_DIR`（默认 `services/webhook-receiver/logs`）
    - `ACTION_QUEUE_DIR`（默认 `.runtime/action-queue`）
    - `EMOTION_SCRIPT_PATH`（默认 `skills/robot-behavior/scripts/analyze_emotion.py`）
  - `server.py` 子进程调用改为 `sys.executable + EMOTION_SCRIPT_PATH`，环境变量直接继承，不再注入硬编码 Key。
  - `director_mode.py` 子进程调用改为 `sys.executable + analyze_emotion.py` 相对路径。

**验证命令**:
```bash
python -m py_compile services/webhook-receiver/server.py
python -m py_compile skills/robot-behavior/scripts/director_mode.py
python services/webhook-receiver/server.py
```

**上传给 openclaw 时注意**:
- 需要上传:
  - `services/webhook-receiver/server.py`
  - `skills/robot-behavior/scripts/director_mode.py`
- 不需要上传:
  - 本地运行产生的 `__pycache__/`
  - 本地日志文件 `services/webhook-receiver/logs/webhook.log`

---

## 变更记录：服务端动作序列兜底校验（协议不变）

**改动文件**:
- `services/webhook-receiver/server.py`

**改动原因**: 保证输出始终满足“整数数组且以 0 结尾”的硬性约束，避免异常输入污染队列。

**改动内容**:
- before:
  - `handle_emotion` 和 `handle_action` 直接使用上游 `action_sequence`，未做标准化。
- after:
  - 新增 `normalize_action_sequence(sequence)`：
    - 非数组/空数组 -> `[0]`
    - 非整数元素自动过滤并尝试转 `int`
    - 末尾非 `0` 自动补 `0`
  - 在 `handle_emotion`、`handle_action` 入队前统一调用该函数。

**验证命令**:
```bash
python -m py_compile services/webhook-receiver/server.py
curl -X POST http://127.0.0.1:8765/action/milk_duos_001 -H "Content-Type: application/json" -d "{\"action_sequence\":[1,6]}"
curl http://127.0.0.1:8765/poll/milk_duos_001
```

**上传给 openclaw 时注意**:
- 需要上传:
  - `services/webhook-receiver/server.py`
- 不需要上传:
  - 本地日志与缓存文件

---

## 变更记录：情绪分析 Provider 抽象（dashscope/mock）

**改动文件**:
- `skills/robot-behavior/scripts/analyze_emotion.py`

**改动原因**: 为“模型迁移目标待定”提供可切换能力，先本地可跑，再平滑切换真实模型。

**改动内容**:
- before:
  - 仅支持 DashScope WebSocket；模块加载时强依赖 `websocket-client`。
- after:
  - 新增 provider 机制：
    - `--provider` 参数（`dashscope`/`mock`）
    - 环境变量 `ROBOT_BEHAVIOR_PROVIDER`（默认 `dashscope`）
  - 新增 `mock` 规则分析器，支持本地无外网快速联调。
  - `websocket` 改为按需导入，仅 `dashscope` provider 才需要该依赖。
  - 输出保持兼容，并补充 `provider` 字段用于排障。

**验证命令**:
```bash
python -m py_compile skills/robot-behavior/scripts/analyze_emotion.py
python skills/robot-behavior/scripts/analyze_emotion.py --provider mock --input "我今天很开心" --pretty
```

**上传给 openclaw 时注意**:
- 需要上传:
  - `skills/robot-behavior/scripts/analyze_emotion.py`
- 不需要上传:
  - 本地测试输出文件（如有）

---

## 变更记录：可选 API Key 认证 + DuoS 模拟器轮询修复

**改动文件**:
- `services/webhook-receiver/server.py`
- `services/webhook-receiver/duos_simulator.py`

**改动原因**: 增加入口安全控制并修复模拟器与 `/poll` 响应语义不一致导致的漏执行问题。

**改动内容**:
- before:
  - 无认证控制，任何来源可直接调用 `/emotion`、`/action`。
  - `duos_simulator.py` 仅在 `status == "success"` 时执行动作，但服务端有命令时返回 `status == "pending"`。
- after:
  - `server.py` 新增可选认证：
    - `ENABLE_API_KEY_AUTH=true|false`
    - `API_AUTH_KEY=<key>`
    - 仅对 `/emotion`、`/action` 生效；`/poll`、`/ack` 保持兼容。
  - `duos_simulator.py` 改为识别 `status == "pending"` 后执行动作。

**验证命令**:
```bash
# 认证关闭（默认）
python services/webhook-receiver/server.py

# 认证开启示例（PowerShell）
$env:ENABLE_API_KEY_AUTH="true"
$env:API_AUTH_KEY="demo-key"
python services/webhook-receiver/server.py
curl -X POST http://127.0.0.1:8765/emotion -H "Content-Type: application/json" -H "X-API-Key: demo-key" -d "{\"content\":\"我很开心\"}"

# 模拟器语义验证
python -m py_compile services/webhook-receiver/duos_simulator.py
```

**上传给 openclaw 时注意**:
- 需要上传:
  - `services/webhook-receiver/server.py`
  - `services/webhook-receiver/duos_simulator.py`
- 不需要上传:
  - 本地环境变量配置脚本（如你机器上的 profile）
  - 本地日志与缓存文件

---

## 变更记录：Windows 子进程输出解码兼容修复

**改动文件**:
- `services/webhook-receiver/server.py`

**改动原因**: Windows 下子进程输出可能是 GBK，原逻辑固定按 UTF-8 解码会导致 `/emotion` 返回 500。

**改动内容**:
- before:
  - `stdout/stderr` 固定使用 `utf-8` 解码。
- after:
  - 新增 `decode_subprocess_output()`：优先 `utf-8`，失败回退 `gbk`，最终 `replace` 兜底。
  - `analyze_emotion()` 改为统一调用该解码函数。

**验证命令**:
```bash
python -m py_compile services/webhook-receiver/server.py
curl -X POST http://localhost:8765/emotion -H "Content-Type: application/json" -d '{"content":"我很开心"}'
```

**上传给 openclaw 时注意**:
- 需要上传:
  - `services/webhook-receiver/server.py`
- 不需要上传:
  - 本地日志与缓存文件

---

## 变更记录：robot-behavior 两阶段重写（分段→逐段动作→拼接）

**改动文件**:
- `skills/robot-behavior/scripts/analyze_emotion.py`

**改动原因**: 旧版是“整体文本一次性映射动作”，无法表达长故事的情节推进与段间动作连续性。

**改动内容**:
- before:
  - 单阶段分析：直接输出一个动作序列。
  - 没有分段、没有 `last_action` 上下文、没有 `segments` 调试信息。
- after:
  - 实现两阶段流程：
    - `segment_story()`：先按情节节点分段（失败降级为 `[原文]`）。
    - `generate_actions()`：逐段生成动作，传入 `last_action` 与 `is_last`。
  - 实现 `merge_sequences()`：
    - 中间段移除 `0`
    - 仅最后一段保留结尾 `0`
    - 最终兜底确保末尾 `0`
  - 实现 `last_action` 传递：
    - 每段结束后取最后一个非 `0` 动作更新
  - 实现 `emotion_detected` 规则：
    - 单段：取该段情绪
    - 多段同情绪：返回该情绪
    - 多段不一致：返回 `mixed`
  - 实现最终 `normalize_action_sequence()`：
    - 强制整数化
    - 过滤非法编号（仅保留 0-10）
    - 空序列降级 `[0]`
    - 末尾强制 `0`
  - provider 抽象保留并增强：
    - 支持 `dashscope` / `mock`
    - 支持环境变量 `EMOTION_PROVIDER`（兼容 `ROBOT_BEHAVIOR_PROVIDER`）
  - 输出新增 `segments` 调试字段（`server.py` 对外接口仍保持原字段）

**验证命令**:
```bash
python -m py_compile skills/robot-behavior/scripts/analyze_emotion.py
python skills/robot-behavior/scripts/analyze_emotion.py --provider mock --input "我今天很开心" --pretty
python skills/robot-behavior/scripts/analyze_emotion.py --provider mock --input "小明走进教室。老师表扬了他，他非常激动。他跑去告诉朋友这个好消息。" --pretty
```

**上传给 openclaw 时注意**:
- 需要上传:
  - `skills/robot-behavior/scripts/analyze_emotion.py`
- 不需要上传:
  - 本地 `__pycache__/`
  - 本地日志文件



