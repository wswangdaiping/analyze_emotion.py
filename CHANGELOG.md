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
