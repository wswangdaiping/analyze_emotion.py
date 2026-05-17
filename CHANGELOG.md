# 变更记录：wdp    2026/5/16

## 方向十：AI 调用降级链

修改了 **1 个文件**：
`/home/admin/.openclaw/workspace/skills/robot-behavior/scripts/analyze_emotion.py`

本次改动围绕 DashScope API 异常时的可恢复能力展开，目标是让系统在网络、超时或依赖异常时仍能返回合法 JSON，并通过 `fallback_level` 标记本次分析是否发生降级。

------

### 修改 1：扩展 `call_dashscope_json()` 返回结构

在原有 `ok`、`data`、`error` 字段基础上新增：

```python
"fallback_level": 0
```

含义如下：

| fallback_level | 含义 |
| -------------- | ---- |
| 0 | 正常调用成功 |
| 1 | 首次调用失败，等待 2 秒后重试成功 |
| 2 | 重试后仍失败，进入默认/规则降级 |

保留原有 `ok/data/error` 读取方式，调用方仍可按原逻辑判断成功或失败。

------

### 修改 2：新增 DashScope 调用重试与降级日志

将单次 WebSocket 调用拆分为内部函数 `_call_dashscope_json_once()`，外层 `call_dashscope_json()` 负责降级链控制：

1. 第一级：正常调用 DashScope API。
2. 第二级：遇到网络或超时类错误后，等待 2 秒并自动重试一次。
3. 第三级：重试仍失败，返回失败结果并标记 `fallback_level=2`。

每次降级会向 stderr 输出：

```text
[FALLBACK] 原因 → 降级到第X级
```

非重试类错误（如缺少 `websocket-client` 依赖）会直接进入第 2 级降级，不做无意义重试。

------

### 修改 3：打通 `fallback_level` 传递路径

为避免 `call_dashscope_json()` 的降级信息丢失，调整了三个业务函数的返回值：

```python
segment_story(...)     -> (segments, fallback_level)
generate_actions(...) -> (seq, fallback_level)
detect_emotion(...)   -> (emotion, fallback_level)
```

`mock` 模式不调用 API，因此固定返回 `fallback_level=0`。

------

### 修改 4：多段故事汇总最高降级级别

`build_story_actions()` 新增 `fallback_levels` 列表，收集：

- 分段调用的 `fallback_level`
- 每一段 `generate_actions()` 的 `fallback_level`
- 每一段 `detect_emotion()` 的 `fallback_level`

最终使用：

```python
max_fallback_level = max(fallback_levels) if fallback_levels else 0
```

并在最终 JSON 中输出：

```json
"fallback_level": 0
```

这样可以保证多段故事中间任意一段 API 调用失败时，最终监控字段不会被后续成功调用覆盖。

------

## 测试结果

### 本地验证

| 测试项 | 结果 |
| ------ | ---- |
| 语法检查（`compile(..., "exec")`） | 通过 |
| mock 模式正常路径 | 通过，`fallback_level=0` |
| DashScope 异常路径（本地缺少 `websocket-client`） | 通过，合法 JSON 输出，动作兜底为 `[0]`，`fallback_level=2` |
| 多段中间失败模拟 | 通过，第二段失败时最终 `fallback_level=2` |

### OpenClaw 侧验证

复制到 OpenClaw 后已验证：

| 测试项 | 结果 |
| ------ | ---- |
| 语法检查 | 正常 |
| 正常 DashScope 调用路径 | 符合预期 |
| 降级路径 | 符合预期 |
| 多段故事路径 | 符合预期 |

------

## 影响范围

| 影响项 | 说明 |
| ------ | ---- |
| 接口兼容性 | 保持兼容，原有 `ok/data/error` 字段不变 |
| 对外服务响应 | `server.py` 采用白名单式响应，不会把 `fallback_level` 直接暴露给 `/emotion` 调用方 |
| 动作兜底 | `generate_actions()` 失败时仍返回 `[0]` |
| 分段兜底 | `segment_story()` 失败时回退为原文单段 |
| 情绪兜底 | `detect_emotion()` 失败时回退规则引擎 |

本次改动完成了方向十的核心目标：**API 异常时系统不崩溃，仍返回可执行动作，并能通过 `fallback_level` 追踪最高降级级别**。


# 变更记录：ykx    2026/5/15

## 优化 1：修复分段阈值问题

修改了 **1 个文件**：
`/home/admin/.openclaw/workspace/skills/robot-behavior/scripts/analyze_emotion.py`

共进行了 **6 处修改**：

------

### 修改 1：优化分段提示词 `SEGMENT_SYSTEM_PROMPT`

**位置**：第 44-59 行

**修改后**：

```python
SEGMENT_SYSTEM_PROMPT = """你是一个故事情节分析师。
把输入的故事按情节节点分段，每段代表一个独立的动作/情绪事件。

强制规则（必须遵守）：
- 超过 3 句话 → 必须至少分 2 段（硬性要求）
- 超过 6 句话 → 必须至少分 3 段（硬性要求）
- 场景变化（地点/环境改变）→ 触发新段
- 动作性质变化（主动/被动、前进/后退、站立/蹲下）→ 触发新段
- 情绪强度变化（平静→紧张、紧张→兴奋）→ 触发新段
- 时间推进词（突然、然后、接着、最后、此时、过了一会儿）→ 触发新段
- 每段保持 1-3 句话，不要过长

输出格式：
- 纯 JSON 数组，每个元素是字符串（情节片段）
- 不要解释，只输出 JSON
- 如果故事本身只有 1-2 句话，可以返回单元素数组
"""
```

------

### 修改 2：添加句子计数函数 `count_sentences`

**位置**：第 307-310 行（新增函数）

**新增代码**：

```python
def count_sentences(text):
    """计算句子数量（按中文/英文句末标点）"""
    sentences = [s.strip() for s in re.split(r"[。！？!?]", text) if s.strip()]
    return len(sentences)
```

------

### 修改 3：重构 `segment_story` 函数（核心修改）

**位置**：第 312-380 行

**主要新增逻辑**：

1. **计算句子数并构建强制分段提示**：

```python
sentence_count = count_sentences(text)

if sentence_count >= 7:
    force_segment_rule = f"这个故事有{sentence_count}句话，必须分成至少 4 段。"
elif sentence_count >= 5:
    force_segment_rule = f"这个故事有{sentence_count}句话，必须分成至少 3 段。"
elif sentence_count >= 4:
    force_segment_rule = f"这个故事有{sentence_count}句话，必须分成至少 2 段。"
else:
    force_segment_rule = "这个故事较短，可以保持 1 段。"

prompt = f"故事文本：{text}\n\n{force_segment_rule}\n请返回 JSON 数组。"
```

1. **增加分段请求的超时时间**：

```python
segment_timeout = max(timeout, 30)
result = call_dashscope_json(SEGMENT_SYSTEM_PROMPT, prompt, api_key, segment_timeout)
```

1. **添加分段合并逻辑**（防止模型每句切一段）：

```python
target_max = 4 if sentence_count >= 7 else 3

if len(segments) > target_max:
    print(f"[WARN] 分段过多：模型返回{len(segments)}段，将合并为{target_max}段", file=sys.stderr)
    sentences = [s.strip() for s in re.split(r"[。！？!?]", text) if s.strip()]
    segments = []
    chunk_size = max(2, (len(sentences) + target_max - 1) // target_max)
    for i in range(0, len(sentences), chunk_size):
        chunk_sentences = sentences[i:i+chunk_size]
        chunk = "。".join(chunk_sentences)
        if chunk:
            segments.append(chunk + "。")
```

1. **添加调试输出**：

```python
print(f"[DEBUG] 句子数={sentence_count}, 模型返回 segments={len(segments)}", file=sys.stderr)
print(f"[DEBUG] 期望最少分段={expected_min}", file=sys.stderr)
```

------

### 修改 4：修复 JSON 解析函数 `parse_json_maybe`

**位置**：第 171-186 行

**修改前**：

```python
def parse_json_maybe(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
```

**修改后**：

```python
def parse_json_maybe(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 对象或数组
        # 使用非贪婪匹配，但允许内部有换行
        match = re.search(r"(\{[\s\S]*?\}|\
```

------

### 修改 5：增加 WebSocket 接收循环次数

**位置**：第 263-265 行

**修改后**：

Copy

```python
ws.settimeout(timeout)
full_text = ""
# 增加最大迭代次数以接收长响应（如多段 JSON 数组）
max_iterations = 150 if timeout >= 30 else 60
for _ in range(max_iterations):
    data = json.loads(ws.recv())
```

------

## 修改效果对比

| 指标              | 修改前         | 修改后     |
| ----------------- | -------------- | ---------- |
| **长故事分段**    | 1 段（不分段） | 3-4 段 ✅   |
| **短故事超时**    | 5/5 超时       | 0/5 超时 ✅ |
| **JSON 解析失败** | 频繁发生       | 已修复 ✅   |
| **动作序列长度**  | 7-15 个        | 4-9 个 ✅   |

所有修改都围绕解决核心问题：**长故事不分段**，通过强制分段规则 + 句子计数 + 合并逻辑实现。



# 变更二：情绪弧线感知优化

2026-05-15

## 一、变更概述

**优化目标:** 多段故事的情绪输出从单一标签升级为情绪演变路径，使机器人能够感知并表达故事中的情绪变化过程。

**变更前:** 无论故事分多少段，最终只返回一个综合情绪标签（如 `"mixed"`）。

**变更后:** 返回完整的情绪弧线（如 `"nervous → nervous → happy"`），同时保留每段的情绪标注。

------

## 二、修改文件清单

| 文件路径                                           | 修改类型     | 修改内容                      |
| -------------------------------------------------- | ------------ | ----------------------------- |
| `skills/robot-behavior/scripts/analyze_emotion.py` | 核心逻辑修改 | `build_story_actions()` 函数  |
| `tests/batch_story_test.py`                        | 测试脚本更新 | 捕获并输出 `emotion_arc` 字段 |

------

## 三、详细变更内容

### 1. `analyze_emotion.py` (核心脚本)

**位置:** `build_story_actions()` 函数（约第 518-575 行）

#### 变更点 1: segment_debug 结构增强

```python
# 变更前
segment_debug.append({"text": segment, "actions": [int(x) for x in seq if isinstance(x, int)]})

# 变更后
segment_debug.append({
    "text": segment,
    "actions": [int(x) for x in seq if isinstance(x, int)],
    "emotion": emotion,  # 新增：每段独立情绪标注
})
```

#### 变更点 2: 情绪弧线构建逻辑

```python
# 变更前
if len(segments) == 1:
    emotion_detected = segment_emotions[0] if segment_emotions else "calm"
else:
    uniq = {e for e in segment_emotions if e}
    emotion_detected = segment_emotions[0] if len(uniq) == 1 and segment_emotions else "mixed"

# 变更后
if len(segments) == 1:
    emotion_detected = segment_emotions[0] if segment_emotions else "calm"
    emotion_arc = emotion_detected
else:
    # 构建情绪弧线：如 "calm → nervous → happy"
    emotion_arc = " → ".join(segment_emotions)
    # 如果所有段情绪相同，简化为单一标签
    uniq = {e for e in segment_emotions if e}
    emotion_detected = segment_emotions[0] if len(uniq) == 1 and segment_emotions else "mixed"
```

#### 变更点 3: 返回值新增字段

```python
return {
    "status": "success",
    "action_sequence": merged,
    "action_names": [...],
    "emotion_detected": emotion_detected,
    "emotion_arc": emotion_arc,  # 新增字段
    "rationale": rationale,
    "segments": segment_debug,
}
```

------

### 2. `batch_story_test.py` (测试脚本)

#### 变更点 1: 结果捕获

```python
results.append({
    # ... 原有字段 ...
    "emotion": json_output.get("emotion_detected", ""),
    "emotion_arc": json_output.get("emotion_arc", ""),  # 新增
    "segments_data": json_output.get("segments", []),   # 新增
    "expected_emotion": case["emotion"],
})
```

#### 变更点 2: 控制台输出

```python
# 变更后支持显示情绪弧线
if arc_info:
    print(f"  -> emotion={...}, arc={arc_info}, actions={...}, duration={...}s")
else:
    print(f"  -> emotion={...}, actions={...}, duration={...}s")
```

#### 变更点 3: Markdown 报告表格

Copy

```python
# 表头新增 Emotion Arc 列
report.append("| Case | Group | Segments | Actions | Duration(s) | Emotion | Emotion Arc | Warning | Expected | Actual |")
```

------

## 四、测试结果对比

### 短故事（单段）

| Case | 情绪弧线    | 说明                |
| ---- | ----------- | ------------------- |
| A    | `surprised` | 单段，弧线=单一情绪 |
| B    | `scared`    | 单段，弧线=单一情绪 |
| C    | `happy`     | 单段，弧线=单一情绪 |
| D    | `happy`     | ✅ 完全匹配          |

### 长故事（多段）

| Case | 分段 | 情绪弧线                        | 情绪演变解读                                  |
| ---- | ---- | ------------------------------- | --------------------------------------------- |
| E    | 2    | `calm → happy`                  | 平静购物 → 开心离开                           |
| L1   | 3    | `nervous → nervous → happy`     | 紧张进入密林 → 紧张探索 → 开心发现宝藏        |
| L2   | 3    | `nervous → scared → scared`     | 紧张出发 → 害怕进入火场 → 害怕救援            |
| L3   | 4    | `nervous → calm → calm → happy` | 紧张待发 → 平静比赛 → 平静跨越障碍 → 开心庆祝 |

------

## 五、影响范围

| 影响项         | 说明                                                         |
| -------------- | ------------------------------------------------------------ |
| **向后兼容性** | ✅ 完全兼容 - `emotion_detected` 字段保持不变，仅新增 `emotion_arc` |
| **下游消费方** | 需要消费情绪弧线的代码可直接读取 `emotion_arc` 字段          |
| **测试脚本**   | 已更新以捕获和展示新字段                                     |
| **性能影响**   | 无 - 情绪检测原本就在逐段执行，只是之前未输出                |

------

## 八、文件位置

| 文件      | 路径                                                         |
| --------- | ------------------------------------------------------------ |
| 核心脚本  | `/home/admin/.openclaw/workspace/skills/robot-behavior/scripts/analyze_emotion.py` |
| 测试脚本  | `/home/admin/.openclaw/workspace/tests/batch_story_test.py`  |
| 测试报告  | `/home/admin/.openclaw/workspace/tests/batch_story_report_dashscope.md` |
| JSON 数据 | `/home/admin/.openclaw/workspace/tests/batch_story_report_dashscope.json` |







## 变更记录：飞书渠道入口 + OpenClaw 架构定论（2026-05-10 全天工作总结 - wdp）

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


