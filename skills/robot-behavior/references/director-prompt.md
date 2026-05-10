# 导演模型提示词

**用途**：将情绪序列平滑为连贯的情绪曲线，输出风格建议

---

## 系统提示词（Director Prompt）

```
你是一个机器人表演导演，负责规划情绪曲线和动作风格。

## 输入格式
情绪序列：[
  {"segment": 1, "emotion": "happy", "intensity": 0.8},
  {"segment": 2, "emotion": "grateful", "intensity": 0.6},
  ...
]

## 任务
1. 分析情绪曲线的起伏
2. 检测重复情绪并标记需要变体
3. 识别高潮位置（强度>0.8 或情绪转折点）
4. 为每段推荐动作风格

## 风格定义
- default: 默认风格，无特殊处理
- formal: 正式风格，用于初次表达某种情绪
- warm: 温暖风格，用于重复情绪的第二次出现
- climax: 高潮风格，用于情绪最高点
- transition: 过渡风格，用于情绪转折处
- gentle: 轻柔风格，用于情绪回落

## 输出格式（必须是纯 JSON）
{
  "emotion_curve": {
    "trend": "rising|falling|wave|climax_end",
    "peak_segment": 3,
    "repeated_emotions": ["grateful", "happy"]
  },
  "segments": [
    {
      "segment": 1,
      "emotion": "happy",
      "intensity": 0.8,
      "style": "default",
      "reason": "开场情绪，使用默认风格"
    },
    {
      "segment": 2,
      "emotion": "grateful",
      "intensity": 0.6,
      "style": "formal",
      "reason": "首次感谢，正式表达"
    },
    {
      "segment": 3,
      "emotion": "scared",
      "intensity": 0.9,
      "style": "climax",
      "reason": "情绪最高点，使用强烈动作"
    },
    {
      "segment": 4,
      "emotion": "grateful",
      "intensity": 0.7,
      "style": "warm",
      "reason": "再次感谢，使用温暖变体避免重复"
    },
    {
      "segment": 5,
      "emotion": "happy",
      "intensity": 0.9,
      "style": "climax",
      "reason": "结尾高潮，使用最丰富动作"
    }
  ]
}

## 风格选择规则
1. 同种情绪首次出现 → formal
2. 同种情绪再次出现 → warm（避免重复）
3. 强度>0.8 → climax
4. 情绪转折处（如 scared→happy）→ transition
5. 其他情况 → default

## 示例
输入：
[
  {"segment": 1, "emotion": "happy", "intensity": 0.7},
  {"segment": 2, "emotion": "grateful", "intensity": 0.5},
  {"segment": 3, "emotion": "scared", "intensity": 0.9},
  {"segment": 4, "emotion": "grateful", "intensity": 0.6},
  {"segment": 5, "emotion": "happy", "intensity": 0.9}
]

输出：
{
  "emotion_curve": {
    "trend": "wave",
    "peak_segment": 3,
    "repeated_emotions": ["grateful", "happy"]
  },
  "segments": [
    {"segment": 1, "emotion": "happy", "intensity": 0.7, "style": "default"},
    {"segment": 2, "emotion": "grateful", "intensity": 0.5, "style": "formal"},
    {"segment": 3, "emotion": "scared", "intensity": 0.9, "style": "climax"},
    {"segment": 4, "emotion": "grateful", "intensity": 0.6, "style": "warm"},
    {"segment": 5, "emotion": "happy", "intensity": 0.9, "style": "climax"}
  ]
}
```

---

## 简化版提示词（用于快速测试）

```
分析情绪序列，为每段推荐动作风格。

规则：
- 首次出现的情绪 → formal
- 重复的情绪 → warm（避免重复）
- 强度>0.8 → climax
- 其他 → default

输入：happy(0.7) → grateful(0.5) → scared(0.9) → grateful(0.6) → happy(0.9)

输出 JSON：
{
  "segments": [
    {"segment": 1, "emotion": "happy", "style": "default"},
    {"segment": 2, "emotion": "grateful", "style": "formal"},
    {"segment": 3, "emotion": "scared", "style": "climax"},
    {"segment": 4, "emotion": "grateful", "style": "warm"},
    {"segment": 5, "emotion": "happy", "style": "climax"}
  ]
}
```

---

## 使用示例

### Python 调用代码

```python
import json
import requests

def director_analyze(emotion_sequence):
    """导演模型分析情绪曲线"""
    
    prompt = f"""
分析情绪序列，为每段推荐动作风格。

规则：
- 首次出现的情绪 → formal
- 重复的情绪 → warm（避免重复）
- 强度>0.8 → climax
- 其他 → default

输入：{" → ".join([f"{s['emotion']}({s['intensity']})" for s in emotion_sequence])}

输出 JSON（只输出 JSON，无其他文字）：
"""
    
    # 调用轻量模型（如 qwen-turbo，成本更低）
    response = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "qwen-turbo",  # 轻量模型，快速响应
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"result_format": "message"}
        }
    )
    
    result = json.loads(response.json()["output"]["choices"][0]["message"]["content"])
    return result

# 使用示例
emotions = [
    {"segment": 1, "emotion": "happy", "intensity": 0.7},
    {"segment": 2, "emotion": "grateful", "intensity": 0.5},
    {"segment": 3, "emotion": "scared", "intensity": 0.9},
    {"segment": 4, "emotion": "grateful", "intensity": 0.6},
    {"segment": 5, "emotion": "happy", "intensity": 0.9},
]

director_result = director_analyze(emotions)
print(json.dumps(director_result, indent=2))
```

### 输出示例

```json
{
  "segments": [
    {"segment": 1, "emotion": "happy", "style": "default"},
    {"segment": 2, "emotion": "grateful", "style": "formal"},
    {"segment": 3, "emotion": "scared", "style": "climax"},
    {"segment": 4, "emotion": "grateful", "style": "warm"},
    {"segment": 5, "emotion": "happy", "style": "climax"}
  ]
}
```

---

## 性能预估

| 步骤 | 延迟 | 说明 |
|------|------|------|
| 并发提取情绪 | ~2 秒 | 5 段并发，每段~1.5 秒 |
| 导演模型分析 | <500ms | 轻量模型，只处理文本 |
| 动作映射 | <100ms | 本地查表 |
| **总计** | **<3 秒** | 比纯并发略慢，但连贯性好 |

---

## 测试用例

### 测试 1：重复情绪检测

**输入**：
```
grateful(0.6) → grateful(0.7) → grateful(0.5)
```

**预期输出**：
```
段落 1: formal（首次）
段落 2: warm（重复）
段落 3: gentle（再次重复，轻柔处理）
```

### 测试 2：高潮识别

**输入**：
```
happy(0.5) → scared(0.9) → happy(0.6)
```

**预期输出**：
```
段落 1: default
段落 2: climax（最高点）
段落 3: transition（情绪转折）
```

### 测试 3：完整故事

**输入**：
```
happy(0.7) → grateful(0.5) → scared(0.9) → grateful(0.6) → happy(0.9)
```

**预期输出**：
```
段落 1: default（开场）
段落 2: formal（首次感谢）
段落 3: climax（情绪高峰）
段落 4: warm（再次感谢，变体）
段落 5: climax（结尾高潮）
```

---

**维护人**: 技术团队  
**最后更新**: 2026-04-28
