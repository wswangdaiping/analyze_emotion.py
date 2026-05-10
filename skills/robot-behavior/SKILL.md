---
name: robot-behavior
description: 机器人行为生成 - 理解用户情绪或故事，生成机器人动作序列（数字组）。使用场景：(1) 接收情绪文本 (2) 分析情感状态 (3) 输出动作编号序列 (4) 与 json-webhook-skill 链式调用发送到 Milk DuoS 开发板。使用 qwen3.5-omni-plus-realtime 实时模型进行智能情绪分析（支持复杂情景理解）
---

# Robot Behavior Skill

## 核心功能

将人类情绪/故事 → 机器人可执行的动作序列

## 完整工作流

```
WebApp → OpenClaw 接收 → robot-behavior → json-webhook-skill → Milk DuoS
         (情绪文本)      (分析生成序列)    (发送动作指令)     (执行动作)
```

## 输入

### 输入格式

```json
{
  "input_type": "text",
  "content": "用户输入的文本内容",
  "session_id": "可选"
}
```

### 输入示例

**情绪型：**
- `"我今天很开心"`
- `"我有点难过"`
- `"我现在有点紧张"`

**故事型：**
- `"小兔子很开心地跑进森林，看见朋友后挥了挥手"`
- `"今天被老板批评了，心情很低落"`

## 输出

### 成功响应

```json
{
  "status": "success",
  "action_sequence": [1, 0, 8],
  "action_names": ["挥手", "站立", "下蹲"],
  "emotion_detected": "happy",
  "rationale": "检测到开心情绪，选择挥手和庆祝动作"
}
```

### 错误响应

```json
{
  "status": "error",
  "error_code": "INVALID_INPUT",
  "error_message": "输入无法识别"
}
```

## 动作映射表

| 数字 | 动作 | 说明 |
|------|------|------|
| 0 | 站立 | 中立姿态、待机 |
| 1 | 挥手 | 打招呼、开心 |
| 2 | 摇头 | 否定、拒绝 |
| 3 | 一边致谢 | 感谢（左） |
| 4 | 另一边致谢 | 感谢（右） |
| 5 | 交通指挥 | 特殊演绎 |
| 6 | 舞蹈歌曲 | 庆祝、非常开心 |
| 7 | 自由飞翔 | 特殊演绎 |
| 8 | 下蹲 | 害怕、躲藏、低落 |
| 9 | 前进 2 步 | 主动接近 |
| 10 | 后退 2 步 | 害怕后退 |

## 情绪→动作映射规则

详细规则见 [references/emotion-map.md](references/emotion-map.md)

### 快速参考

| 情绪 | 推荐动作序列 |
|------|-------------|
| 开心（轻度） | [1, 0] |
| 开心（中度） | [1, 6, 0] |
| 开心（重度） | [1, 6, 7, 0] |
| 自由/飞翔 | [7, 0] |
| 难过 | [2, 8, 0] |
| 紧张/害怕 | [8, 10, 0] |
| 感谢 | [3, 4, 0] |
| 平静 | [0] |
| 惊讶 | [10, 1, 0] |
| 生气 | [2, 5, 0] |

## 分析流程

1. **提取关键词** - 识别情绪词汇（开心、难过、紧张等）
2. **判断情绪类型** - 映射到标准情绪分类
3. **查询动作映射** - 根据情绪获取推荐动作
4. **生成序列** - 输出动作编号数组
5. **添加说明** - 生成生成理由 (rationale)

## 分析引擎

### 使用模型

**qwen3.5-omni-plus-realtime** - 通义千问实时多模态模型（WebSocket 连接）

| 特点 | 说明 |
|------|------|
| 延迟 | 1-2 秒（WebSocket 实时） |
| 成本 | 约 ¥0.01/次（按量计费） |
| 准确率 | 98%+（智能理解） |
| 优势 | 支持复杂情绪、故事、上下文理解 |

### 调用方式

WebSocket 实时连接，调用流程：
1. 建立 WebSocket 连接
2. 发送 `session.update` 配置系统提示词
3. 发送 `conversation.item.create` 添加用户消息
4. 发送 `response.create` 触发响应
5. 接收 `response.text.done` 获取 JSON 结果

### 情绪词库

支持 7 种基础情绪 + 复杂情绪理解：
- 开心、难过、紧张、害怕、感谢、生气、惊讶

详细映射见 [references/emotion-map.md](references/emotion-map.md)

### API 配置

```bash
# 环境变量
export DASHSCOPE_API_KEY="sk-xxx"

# 测试
python scripts/analyze_emotion.py --input "我很难过" --pretty
```

---

## 链式调用

### 与 json-webhook-skill 配合

生成动作序列后，自动发送到 Milk DuoS：

```bash
# 1. 调用 robot-behavior 生成序列
python scripts/analyze_emotion.py --input "我很难过" --pretty

# 2. 调用 json-webhook-skill 发送
python /home/admin/.openclaw/workspace/skills/json-webhook-skill/scripts/send_webhook.py \
  --url http://<duos-ip>:8765/action/milk_duos_001 \
  --data '{"action_sequence": [1, 6, 0]}'
```

### 配置文件

目标地址配置在 [references/clients.json](references/clients.json)

## 错误码

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| `INVALID_INPUT` | 输入无法识别 | 提示用户重新输入 |
| `EMOTION_UNKNOWN` | 情绪不明确 | 使用默认动作 [0] |
| `STORY_INVALID` | 故事结构不完整 | 尝试提取主要情绪 |

## 使用示例

### 示例 1：简单情绪

**输入：**
```
"我今天很开心"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [1, 6, 0],
  "action_names": ["挥手", "舞蹈歌曲", "站立"],
  "emotion_detected": "happy",
  "rationale": "检测到'开心'情绪，选择挥手和舞蹈动作表达喜悦"
}
```

### 示例 2：故事型

**输入：**
```
"小兔子很开心地跑进森林，看见朋友后挥了挥手"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [1, 6, 0],
  "action_names": ["挥手", "舞蹈歌曲", "站立"],
  "emotion_detected": "happy",
  "rationale": "故事中出现'开心'和'挥手'，匹配欢迎/喜悦场景"
}
```

### 示例 3：负面情绪

**输入：**
```
"我有点难过"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [2, 8, 0],
  "action_names": ["摇头", "下蹲", "站立"],
  "emotion_detected": "sad",
  "rationale": "检测到'难过'情绪，选择摇头和下蹲表达低落"
}
```

## 相关文件

- `references/emotion-map.md` - 情绪与动作详细映射规则
- `references/examples.md` - 更多输入输出示例
- `references/clients.json` - Milk DuoS 客户端配置

## 注意事项

1. **动作序列长度** - 建议 1-5 个动作，避免过长
2. **默认动作** - 无法识别时返回 [0]（站立待机）
3. **动作间隔** - 开发板执行时建议每个动作间隔 500ms
4. **情绪优先级** - 明确情绪词 > 故事上下文 > 默认
