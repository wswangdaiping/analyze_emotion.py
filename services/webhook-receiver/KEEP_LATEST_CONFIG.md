# 最新优先策略配置说明

**版本**: v1.2  
**更新日期**: 2026-04-28  
**功能**: 新输入时自动清除未 ACK 的旧命令

---

## 📋 策略说明

### 工作原理

```
用户输入 1: "我今天很开心"
→ 队列：[开心命令 (pending)]

用户输入 2: "我很难过"
→ 清除未 ACK 的开心命令
→ 队列：[难过命令 (pending)]

用户输入 3: "我好害怕"
→ 清除未 ACK 的难过命令
→ 队列：[害怕命令 (pending)]
```

### 核心逻辑

- ✅ **新输入时**：自动清除队列中所有未 ACK 的命令
- ✅ **只保留**：最新输入对应的动作序列
- ✅ **已完成命令**：保留（已 ACK 的命令不受影响）

---

## ⚙️ 配置位置

**文件**: `services/webhook-receiver/server.py`

```python
class ActionQueue:
    # 是否启用最新优先策略
    KEEP_LATEST_ONLY = True     # True=启用，False=禁用
```

---

## 🔧 启用/禁用

### 启用最新优先（默认）

```python
KEEP_LATEST_ONLY = True
```

**效果**：每次新输入时，自动清除未 ACK 的旧命令

### 禁用最新优先

```python
KEEP_LATEST_ONLY = False
```

**效果**：新输入时保留所有旧命令，队列累加

---

## 📊 使用场景

### 场景 1：实时交互（推荐启用）

**适用**：对话式交互、实时情绪响应

```python
KEEP_LATEST_ONLY = True
```

**优点**：
- ✅ 机器人总是执行最新的情绪命令
- ✅ 避免旧命令堆积
- ✅ 响应用户最新状态

**示例**：
```
用户："我今天很开心" → 机器人准备执行开心动作
用户："等等，我其实很难过" → 清除开心，执行难过
```

### 场景 2：故事演绎（建议禁用）

**适用**：长故事分段演绎、多段动作序列

```python
KEEP_LATEST_ONLY = False
```

**优点**：
- ✅ 支持多段命令累加
- ✅ 完整演绎故事情节
- ✅ 批量执行多个动作序列

**示例**：
```
段落 1: 开心 → 入队
段落 2: 感谢 → 入队（保留段落 1）
段落 3: 害怕 → 入队（保留段落 1、2）
批量执行：开心→感谢→害怕
```

### 场景 3：混合模式

**适用**：平时实时交互，偶尔故事演绎

**方案 A**：动态切换
```python
# 默认实时交互
KEEP_LATEST_ONLY = True

# 故事演绎时临时禁用
# 调用 /action 端点直接发送（绕过自动清除）
```

**方案 B**：使用不同客户端 ID
```python
# 实时交互使用默认客户端
client_id = "milk_duos_001"

# 故事演绎使用专用客户端
client_id = "milk_duos_001_story"
```

---

## 📡 API 行为

### 启用最新优先时

**端点**: `POST /emotion`

**行为**:
```json
// 第 1 次输入
POST /emotion
{"content": "我很开心"}
→ 队列：[开心 (pending)]

// 第 2 次输入
POST /emotion
{"content": "我很难过"}
→ 清除开心，添加难过
→ 队列：[难过 (pending)]
```

### 禁用最新优先时

**端点**: `POST /emotion`

**行为**:
```json
// 第 1 次输入
POST /emotion
{"content": "我很开心"}
→ 队列：[开心 (pending)]

// 第 2 次输入
POST /emotion
{"content": "我很难过"}
→ 保留开心，添加难过
→ 队列：[开心 (pending), 难过 (pending)]
```

---

## 🎯 与其他配置的配合

### 配置组合 1：实时交互

```python
KEEP_LATEST_ONLY = True      # 启用最新优先
CLEANUP_INTERVAL_HOURS = 3   # 3 小时定期清理
MAX_AGE_HOURS = 3            # 保留 3 小时
```

**效果**：总是执行最新命令 + 定期清理过期数据

### 配置组合 2：故事演绎

```python
KEEP_LATEST_ONLY = False     # 禁用最新优先
CLEANUP_INTERVAL_HOURS = 6   # 6 小时定期清理
MAX_AGE_HOURS = 6            # 保留 6 小时
```

**效果**：支持多段累加 + 延长保留时间

### 配置组合 3：高性能模式

```python
KEEP_LATEST_ONLY = True      # 启用最新优先
CLEANUP_INTERVAL_HOURS = 1   # 1 小时定期清理
MAX_AGE_HOURS = 1            # 保留 1 小时
```

**效果**：快速响应 + 快速清理

---

## 📝 日志示例

### 启用最新优先

```
2026-04-28 21:59:21,511 - INFO - 情绪分析完成：happy → [1, 6, 0]
2026-04-28 21:59:23,732 - INFO - 【最新优先】清除客户端 milk_duos_001 的 1 条未 ACK 旧命令
2026-04-28 21:59:23,732 - INFO - 情绪分析完成：sad → [2, 8, 0]
2026-04-28 21:59:25,999 - INFO - 【最新优先】清除客户端 milk_duos_001 的 1 条未 ACK 旧命令
2026-04-28 21:59:26,000 - INFO - 情绪分析完成：scared → [8, 10, 0]
```

### 禁用最新优先

```
2026-04-28 21:59:21,511 - INFO - 情绪分析完成：happy → [1, 6, 0]
2026-04-28 21:59:21,512 - INFO - 添加动作指令到 milk_duos_001: [1, 6, 0]
2026-04-28 21:59:23,732 - INFO - 情绪分析完成：sad → [2, 8, 0]
2026-04-28 21:59:23,733 - INFO - 添加动作指令到 milk_duos_001: [2, 8, 0]
```

---

## 🧪 测试方法

### 测试 1：验证最新优先

```bash
# 输入 1
curl -X POST http://localhost:8765/emotion \
  -H "Content-Type: application/json" \
  -d '{"content": "我很开心"}'

# 输入 2
curl -X POST http://localhost:8765/emotion \
  -H "Content-Type: application/json" \
  -d '{"content": "我很难过"}'

# 查看队列（应该只有难过）
curl http://localhost:8765/poll/milk_duos_001
```

### 测试 2：验证累加模式

```bash
# 修改配置 KEEP_LATEST_ONLY = False
# 重启服务后...

# 输入 1
curl -X POST http://localhost:8765/emotion \
  -H "Content-Type: application/json" \
  -d '{"content": "我很开心"}'

# 输入 2
curl -X POST http://localhost:8765/emotion \
  -H "Content-Type: application/json" \
  -d '{"content": "我很难过"}'

# 查看队列（应该有开心和难过）
curl http://localhost:8765/poll/milk_duos_001
curl http://localhost:8765/poll/milk_duos_001  # 第二次轮询
```

---

## ⚠️ 注意事项

### 1. ACK 状态

- **pending** → 会被清除
- **processing** → 会被清除
- **completed** → 保留（已 ACK）

**建议**：确保硬件端及时发送 ACK 确认

### 2. 多客户端

每个客户端独立管理队列：

```python
# 客户端 A 的命令不会被客户端 B 的输入清除
client_A: [命令 A1, 命令 A2]
client_B: [命令 B1, 命令 B2]
```

### 3. 直接发送动作

使用 `/action/{client_id}` 端点直接发送时，也会应用最新优先策略。

如需绕过，可临时修改配置或修改代码。

---

## 🛠️ 故障排查

### 问题 1：旧命令未被清除

**检查**：
```bash
# 查看配置
grep "KEEP_LATEST_ONLY" services/webhook-receiver/server.py

# 查看日志
tail -50 /tmp/webhook-receiver.log | grep "清除"
```

**解决**：
```bash
# 确认配置为 True
KEEP_LATEST_ONLY = True

# 重启服务
pkill -f "python3 server.py"
nohup python3 server.py > /tmp/webhook-receiver.log 2>&1 &
```

### 问题 2：故事演绎被中断

**原因**：启用了最新优先，分段命令被逐个清除

**解决**：
```python
KEEP_LATEST_ONLY = False  # 禁用最新优先
```

### 问题 3：日志中没有清除记录

**检查**：
```bash
# 查看是否有新输入
tail -50 /tmp/webhook-receiver.log | grep "情绪分析完成"

# 确认有旧命令待清除
curl http://localhost:8765/poll/milk_duos_001
```

---

## 📚 相关文件

- `services/webhook-receiver/server.py` - 主服务代码
- `services/webhook-receiver/CONFIG.md` - 队列配置说明
- `services/webhook-receiver/logs/webhook.log` - 日志文件

---

## 🎯 推荐配置

### 默认配置（实时交互）

```python
KEEP_LATEST_ONLY = True      # 启用最新优先
CLEANUP_INTERVAL_HOURS = 3   # 3 小时清理
MAX_AGE_HOURS = 3            # 保留 3 小时
```

### 故事演绎配置

```python
KEEP_LATEST_ONLY = False     # 禁用最新优先
CLEANUP_INTERVAL_HOURS = 6   # 6 小时清理
MAX_AGE_HOURS = 6            # 保留 6 小时
```

---

**维护人**：技术团队  
**最后更新**：2026-04-28
