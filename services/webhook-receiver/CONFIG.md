# Webhook 队列配置说明

**版本**: v1.1  
**更新日期**: 2026-04-28  
**功能**: 队列定期自动清理

---

## 📋 配置概览

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 清理间隔 | 3 小时 | 每隔 3 小时自动清理一次 |
| 保留时间 | 3 小时 | 只保留 3 小时内的命令 |
| 清理范围 | 所有客户端 | 清理所有注册客户端的过期命令 |

---

## ⚙️ 配置位置

文件：`services/webhook-receiver/server.py`

```python
class ActionQueue:
    """动作指令队列（每个客户端独立）"""
    
    # 配置
    CLEANUP_INTERVAL_HOURS = 3  # 清理间隔（小时）
    MAX_AGE_HOURS = 3           # 命令最大保留时间（小时）
```

---

## 🔧 修改配置

### 方式 1：修改清理间隔

```python
# 改为每 6 小时清理一次
CLEANUP_INTERVAL_HOURS = 6
```

### 方式 2：修改保留时间

```python
# 保留 6 小时内的命令
MAX_AGE_HOURS = 6
```

### 方式 3：独立配置

```python
# 每 6 小时清理一次，但只保留 3 小时内的命令
CLEANUP_INTERVAL_HOURS = 6
MAX_AGE_HOURS = 3
```

**建议**：清理间隔 ≤ 保留时间，避免命令堆积

---

## 📊 清理策略

### 清理逻辑

```
当前时间：2026-04-28 21:00:00
保留时间：3 小时
清理截止时间：2026-04-28 18:00:00

结果：
- 18:00:00 之后创建的命令 → 保留 ✅
- 18:00:00 之前创建的命令 → 清理 ❌
```

### 清理范围

- ✅ pending 状态的命令（未被轮询）
- ✅ processing 状态的命令（已轮询但未确认）
- ✅ completed 状态的命令（已完成）

**注意**：所有状态的命令都会清理，只要超过保留时间

---

## 🎯 使用场景

### 场景 1：开发环境

```python
# 快速清理，避免测试数据堆积
CLEANUP_INTERVAL_HOURS = 1
MAX_AGE_HOURS = 1
```

### 场景 2：生产环境

```python
# 适中配置，平衡性能和数据保留
CLEANUP_INTERVAL_HOURS = 3
MAX_AGE_HOURS = 3
```

### 场景 3：演示环境

```python
# 延长保留时间，方便演示回顾
CLEANUP_INTERVAL_HOURS = 6
MAX_AGE_HOURS = 6
```

---

## 📡 API 端点

### 手动触发清理

**端点**：`GET /cleanup`

**请求**：
```bash
curl http://localhost:8765/cleanup
```

**响应**：
```json
{
  "status": "success",
  "message": "队列清理完成",
  "cleanup_policy": {
    "interval_hours": 3,
    "max_age_hours": 3
  }
}
```

**用途**：
- 手动清理过期命令
- 测试清理功能
- 释放内存空间

---

## 📝 日志示例

### 启动日志

```
2026-04-28 21:54:44,864 - INFO - 已启动定期清理任务：每 3 小时清理一次（保留 3 小时内命令）
```

### 清理日志

```
2026-04-28 21:00:00,000 - INFO - 定期清理完成：共清理 15 条旧命令（保留 3 小时内）
```

### 手动清理日志

```
2026-04-28 21:55:16,805 - INFO - ('127.0.0.1', 49592) - "GET /cleanup HTTP/1.1" 200 -
```

---

## 🔍 监控建议

### 1. 队列大小监控

```bash
# 查看队列中的命令数量
curl -s http://localhost:8765/poll/milk_duos_001 | python3 -c "import sys,json; d=json.load(sys.stdin); print('队列命令数:', len(d.get('commands', [d])))"
```

### 2. 清理效果监控

```bash
# 查看最近的清理日志
tail -50 /home/admin/.openclaw/workspace/services/webhook-receiver/logs/webhook.log | grep "清理"
```

### 3. 健康检查

```bash
# 检查服务状态
curl http://localhost:8765/health
```

---

## ⚠️ 注意事项

### 1. 内存管理

- 队列无大小限制，依赖定期清理
- 如果命令量很大，建议缩短清理间隔
- 生产环境建议监控内存使用

### 2. 命令丢失风险

- 清理后无法恢复过期命令
- 重要命令建议外部存储
- 清理前会记录日志

### 3. 时间同步

- 使用 UTC 时间戳
- 确保服务器时间准确
- 时区不影响清理逻辑

---

## 🛠️ 故障排查

### 问题 1：清理未生效

**检查**：
```bash
# 查看日志确认清理任务已启动
tail -20 /tmp/webhook-receiver.log | grep "定期清理"
```

**解决**：重启服务
```bash
pkill -f "python3 server.py"
cd /home/admin/.openclaw/workspace/services/webhook-receiver
nohup python3 server.py > /tmp/webhook-receiver.log 2>&1 &
```

### 问题 2：清理过于频繁

**解决**：修改配置
```python
CLEANUP_INTERVAL_HOURS = 6  # 延长清理间隔
```

### 问题 3：命令过早被清理

**解决**：延长保留时间
```python
MAX_AGE_HOURS = 6  # 延长保留时间
```

---

## 📚 相关文件

- `services/webhook-receiver/server.py` - 主服务代码
- `services/webhook-receiver/logs/webhook.log` - 日志文件
- `project-docs/队列清理配置说明.md` - 本文档

---

## 🎯 最佳实践

1. **开发环境**：1 小时间隔 +1 小时保留
2. **生产环境**：3 小时间隔 +3 小时保留
3. **演示环境**：6 小时间隔 +6 小时保留
4. **高负载环境**：考虑添加队列大小限制
5. **重要场景**：外部持久化存储命令历史

---

**维护人**：技术团队  
**最后更新**：2026-04-28
