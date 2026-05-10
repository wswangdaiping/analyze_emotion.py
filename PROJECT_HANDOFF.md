# 机器人情绪系统 - 技术交接文档

**项目名称：** 机器人情绪控制系统  
**版本：** 1.0  
**更新日期：** 2026-04-23  
**维护者：** Claw 🦞

---

## 📋 目录

1. [系统架构](#系统架构)
2. [组件说明](#组件说明)
3. [API 接口文档](#api 接口文档)
4. [部署配置](#部署配置)
5. [测试指南](#测试指南)
6. [故障排查](#故障排查)

---

## 系统架构

```
┌─────────────┐      HTTP       ┌──────────────┐      HTTP      ┌─────────────┐
│   WebApp    │ ─────────────> │  OpenClaw    │ ────────────> │  Milk DuoS  │
│ (情绪输入)   │   POST /emotion│  (情绪分析)   │  GET /poll    │  (动作执行)  │
└─────────────┘                └──────────────┘               └─────────────┘
                                      ↓
                              qwen3.5-omni-plus-realtime
                                 (情绪分析模型)
```

### 数据流

1. **WebApp** 发送情绪文本 → OpenClaw `/emotion` 端点
2. **OpenClaw** 调用 AI 模型分析情绪 → 生成动作序列
3. **OpenClaw** 将动作指令存入队列
4. **Milk DuoS** 每 2 秒轮询 → OpenClaw `/poll` 端点
5. **Milk DuoS** 获取动作指令 → 执行机器人动作

---

## 组件说明

### 1. OpenClaw 服务器

| 项目 | 配置 |
|------|------|
| **公网 IP** | `47.93.27.196` |
| **服务端口** | `8765` |
| **位置** | 阿里云 ECS |
| **安全组** | 已开放 8765 端口 |

**运行服务：**
- `webhook-receiver` - HTTP 接收服务
- `robot-behavior` - 情绪分析 Skill
- `json-webhook-skill` - 动作发送 Skill

---

### 2. Milk DuoS 开发板

| 项目 | 配置 |
|------|------|
| **型号** | Milk DuoS (ESP32-S3) |
| **客户端 ID** | `milk_duos_001` |
| **轮询间隔** | 2 秒 |
| **连接方式** | WiFi → HTTP 轮询 |

---

### 3. WebApp（情绪输入）

| 项目 | 配置 |
|------|------|
| **输入方式** | 文本（可扩展音频） |
| **发送格式** | JSON POST |
| **端点** | `POST /emotion` |

---

## API 接口文档

### 基础信息

| 项目 | 值 |
|------|-----|
| **基础 URL** | `http://47.93.27.196:8765` |
| **Content-Type** | `application/json` |
| **字符编码** | UTF-8 |

---

### 1. 发送情绪数据

**用途：** WebApp 发送情绪文本到 OpenClaw

**端点：** `POST /emotion`

**请求头：**
```
Content-Type: application/json
```

**请求体：**
```json
{
  "content": "我很难过",
  "session_id": "user_001"
}
```

**响应（成功）：**
```json
{
  "status": "success",
  "emotion": "sad",
  "action_sequence": [2, 8, 0],
  "command_id": "cmd_xxx",
  "client_id": "milk_duos_001"
}
```

**响应（失败）：**
```json
{
  "error": "Emotion analysis failed",
  "details": {...}
}
```

---

### 2. 轮询动作指令

**用途：** DuoS 轮询待执行的动作

**端点：** `GET /poll/{client_id}`

**示例：**
```
GET /poll/milk_duos_001
```

**响应（有动作）：**
```json
{
  "command_id": "cmd_xxx",
  "action_sequence": [2, 8, 0],
  "emotion": "sad",
  "created_at": "2026-04-23T15:00:00Z",
  "status": "pending"
}
```

**响应（无动作）：**
```json
{
  "status": "no_action",
  "message": "No pending actions"
}
```

---

### 3. 直接发送动作

**用途：** 直接发送动作指令到指定客户端

**端点：** `POST /action/{client_id}`

**请求体：**
```json
{
  "action_sequence": [1, 6, 0],
  "emotion": "happy"
}
```

**响应：**
```json
{
  "status": "success",
  "command_id": "cmd_xxx"
}
```

---

### 4. 确认动作完成

**用途：** DuoS 确认动作已执行

**端点：** `POST /ack/{client_id}`

**请求体：**
```json
{
  "command_id": "cmd_xxx"
}
```

**响应：**
```json
{
  "status": "success"
}
```

---

### 5. 健康检查

**用途：** 检查服务是否运行

**端点：** `GET /health`

**响应：**
```json
{
  "status": "ok",
  "timestamp": "2026-04-23T15:00:00Z",
  "service": "openclaw-webhook-receiver"
}
```

---

## 部署配置

### OpenClaw 服务器配置

**服务位置：**
```
/home/admin/.openclaw/workspace/services/webhook-receiver/
```

**启动命令：**
```bash
cd /home/admin/.openclaw/workspace/services/webhook-receiver
nohup python3 server.py > /dev/null 2>&1 &
```

**查看日志：**
```bash
tail -f logs/webhook.log
```

**停止服务：**
```bash
pkill -f "python3 server.py"
```

---

### Milk DuoS 配置

**代码位置：**
```
/home/admin/.openclaw/workspace/services/webhook-receiver/duos_simulator.py
```

**测试命令（Windows）：**
```powershell
# 轮询模式（模拟 DuoS）
python duos_simulator.py

# 测试情绪发送
python duos_simulator.py 我很难过
```

---

## 测试指南

### 测试 1：服务器连通性

**Windows PowerShell：**
```powershell
Test-NetConnection -ComputerName 47.93.27.196 -Port 8765
```

**预期：** `TcpTestSucceeded : True`

---

### 测试 2：健康检查

```powershell
curl http://47.93.27.196:8765/health
```

**预期：** `{"status": "ok", ...}`

---

### 测试 3：发送情绪

```powershell
curl -X POST http://47.93.27.196:8765/emotion `
  -H "Content-Type: application/json" `
  -d "{\"content\":\"我很难过\"}"
```

**预期：**
```json
{
  "status": "success",
  "emotion": "sad",
  "action_sequence": [2, 8, 0]
}
```

---

### 测试 4：轮询动作

```powershell
curl http://47.93.27.196:8765/poll/milk_duos_001
```

**预期：**
- 有动作：返回动作序列
- 无动作：`{"status": "no_action"}`

---

### 测试 5：Python 模拟器

**Windows 上运行：**

```powershell
# 窗口 1：启动轮询模式（模拟 DuoS）
python duos_simulator.py

# 窗口 2：发送测试动作
python test_duos.py -e happy

# 或直接发送动作序列
python test_duos.py -a 1,6,0
```

**预期：** 轮询窗口收到动作并执行

---

## 故障排查

### 问题 1：无法连接服务器

**症状：** `TcpTestSucceeded : False`

**排查步骤：**
1. 检查阿里云安全组 8765 端口是否开放
2. 检查服务器是否运行：`curl http://localhost:8765/health`
3. 检查防火墙设置

---

### 问题 2：情绪分析失败

**症状：** `Emotion analysis failed`

**排查步骤：**
1. 检查 API Key 是否有效
2. 查看日志：`tail -f logs/webhook.log`
3. 手动测试：`python3 skills/robot-behavior/scripts/analyze_emotion.py --input "我很难过"`

---

### 问题 3：DuoS 无法获取动作

**症状：** 轮询一直返回 `no_action`

**排查步骤：**
1. 确认客户端 ID 正确（`milk_duos_001`）
2. 确认已发送情绪数据
3. 查看服务器日志是否有动作入队

---

### 问题 4：动作序列为空

**症状：** `action_sequence: []`

**排查步骤：**
1. 检查情绪分析模型是否正常
2. 查看模型响应日志
3. 必要时降级到本地规则分析

---

## 附录

### A. 情绪 - 动作映射表

| 情绪 | 动作序列 | 动作名称 |
|------|----------|----------|
| sad (难过) | [2, 8, 0] | 摇头→下蹲→站立 |
| happy (开心) | [1, 6, 0] | 挥手→舞蹈→站立 |
| scared (害怕) | [8, 10, 0] | 下蹲→后退→站立 |
| grateful (感谢) | [3, 4, 0] | 两边致谢→站立 |
| angry (生气) | [2, 5, 0] | 摇头→交通指挥→站立 |
| calm (平静) | [0] | 站立 |
| surprised (惊讶) | [10, 1, 0] | 后退→挥手→站立 |

---

### B. 常用命令速查

```bash
# 查看服务状态
ps aux | grep server.py

# 查看日志
tail -f /home/admin/.openclaw/workspace/services/webhook-receiver/logs/webhook.log

# 重启服务
pkill -f "python3 server.py"
cd /home/admin/.openclaw/workspace/services/webhook-receiver
nohup python3 server.py > /dev/null 2>&1 &

# 测试情绪分析
python3 /home/admin/.openclaw/workspace/skills/robot-behavior/scripts/analyze_emotion.py --input "我很难过"
```

---

### C. 联系方式

**技术支持：** Claw 🦞  
**文档版本：** 1.0  
**最后更新：** 2026-04-23

---

**祝部署顺利！** 🎉
