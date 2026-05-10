# 输入输出示例

## 情绪型输入

### 开心

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

---

**输入：**
```
"有点高兴"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [1, 0],
  "action_names": ["挥手", "站立"],
  "emotion_detected": "happy",
  "rationale": "检测到'高兴'情绪（轻度），选择挥手动作"
}
```

---

**输入：**
```
"超级爽！！！"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [1, 6, 9, 0],
  "action_names": ["挥手", "舞蹈歌曲", "前进 2 步", "站立"],
  "emotion_detected": "happy",
  "rationale": "检测到强烈正向情绪，选择完整庆祝序列"
}
```

---

### 难过

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

---

**输入：**
```
"心情很低落"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [2, 8, 0],
  "action_names": ["摇头", "下蹲", "站立"],
  "emotion_detected": "sad",
  "rationale": "检测到'低落'情绪，匹配难过类别"
}
```

---

### 紧张/害怕

**输入：**
```
"我现在有点紧张"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [8, 10, 0],
  "action_names": ["下蹲", "后退 2 步", "站立"],
  "emotion_detected": "nervous",
  "rationale": "检测到'紧张'情绪，选择躲藏和后退动作"
}
```

---

**输入：**
```
"好害怕"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [8, 10, 0],
  "action_names": ["下蹲", "后退 2 步", "站立"],
  "emotion_detected": "scared",
  "rationale": "检测到'害怕'情绪，选择防御性动作"
}
```

---

### 感谢

**输入：**
```
"谢谢"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [3, 4, 0],
  "action_names": ["一边致谢", "另一边致谢", "站立"],
  "emotion_detected": "grateful",
  "rationale": "检测到感谢表达，选择双向致谢动作"
}
```

---

**输入：**
```
"太感谢你了！"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [3, 4, 1, 0],
  "action_names": ["一边致谢", "另一边致谢", "挥手", "站立"],
  "emotion_detected": "grateful",
  "rationale": "检测到强烈感谢，添加挥手动作表达热情"
}
```

---

### 平静

**输入：**
```
"还好吧"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [0],
  "action_names": ["站立"],
  "emotion_detected": "calm",
  "rationale": "检测到平静情绪，保持待机姿态"
}
```

---

**输入：**
```
"没事"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [0],
  "action_names": ["站立"],
  "emotion_detected": "calm",
  "rationale": "无特殊情绪，返回默认待机动作"
}
```

---

### 生气

**输入：**
```
"我生气了"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [2, 5, 0],
  "action_names": ["摇头", "交通指挥", "站立"],
  "emotion_detected": "angry",
  "rationale": "检测到'生气'情绪，选择否定和指挥动作"
}
```

---

### 惊讶

**输入：**
```
"哇！没想到"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [10, 1, 0],
  "action_names": ["后退 2 步", "挥手", "站立"],
  "emotion_detected": "surprised",
  "rationale": "检测到惊讶情绪，选择后退和挥手动作"
}
```

---

## 故事型输入

### 示例 1

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

---

### 示例 2

**输入：**
```
"今天被老板批评了，心情很低落"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [2, 8, 0],
  "action_names": ["摇头", "下蹲", "站立"],
  "emotion_detected": "sad",
  "rationale": "故事描述负面经历，检测到低落情绪"
}
```

---

### 示例 3

**输入：**
```
"刚才遇到一只小猫，它冲我挥手，好可爱"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [1, 0],
  "action_names": ["挥手", "站立"],
  "emotion_detected": "happy",
  "rationale": "故事中有'挥手'动作和正向评价，选择友好回应"
}
```

---

## 错误示例

### 无效输入

**输入：**
```
"12345asdfg"
```

**输出：**
```json
{
  "status": "error",
  "error_code": "INVALID_INPUT",
  "error_message": "输入无法识别，请输入情绪描述或故事"
}
```

---

### 空输入

**输入：**
```
""
```

**输出：**
```json
{
  "status": "error",
  "error_code": "INVALID_INPUT",
  "error_message": "输入内容为空"
}
```

---

### 情绪不明确

**输入：**
```
"感觉怪怪的"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [0],
  "action_names": ["站立"],
  "emotion_detected": "unknown",
  "rationale": "情绪描述不明确，返回默认待机动作"
}
```

---

## 边界情况

### 混合情绪

**输入：**
```
"我又开心又紧张"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [1, 6, 0],
  "action_names": ["挥手", "舞蹈歌曲", "站立"],
  "emotion_detected": "happy",
  "rationale": "检测到混合情绪，取第一个情绪 (开心)"
}
```

---

### 否定句

**输入：**
```
"我不开心"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [2, 8, 0],
  "action_names": ["摇头", "下蹲", "站立"],
  "emotion_detected": "sad",
  "rationale": "检测到否定句，'不开心'映射为难过情绪"
}
```

---

### 疑问句

**输入：**
```
"你开心吗？"
```

**输出：**
```json
{
  "status": "success",
  "action_sequence": [0],
  "action_names": ["站立"],
  "emotion_detected": "unknown",
  "rationale": "输入为疑问句，无明确情绪，返回待机动作"
}
```
