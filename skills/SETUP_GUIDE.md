# 机器人情绪系统 - 配置清单

本文档列出所有需要在部署前完成的配置事项。

---

## ✅ 已完成

- [x] 创建 `robot-behavior` skill
- [x] 创建 `json-webhook-skill` skill
- [x] 配置模型为 `qwen3-omni-flash-realtime` (WebSocket 实时模型)
- [x] 测试情绪分析功能
- [x] 安装 `websocket-client` 依赖

---

## ⚠️ 待配置事项

### 1. 环境变量持久化

**用途：** DashScope API Key 配置

**当前状态：** 仅当前 shell 会话有效

**操作：**

```bash
# 添加到 ~/.bashrc（永久生效）
echo 'export DASHSCOPE_API_KEY="sk-8e08c4db21e1485197dfd3571cc51f0a"' >> ~/.bashrc

# 使配置立即生效
source ~/.bashrc

# 验证
echo $DASHSCOPE_API_KEY
```

**验证命令：**
```bash
python3 -c "import os; print('API Key 已配置' if os.environ.get('DASHSCOPE_API_KEY') else '未配置')"
```

**依赖检查：**
```bash
# 确认 websocket-client 已安装
python3 -c "import websocket; print('websocket-client 已安装')"
```

---

### 2. Milk DuoS 客户端地址配置

**用途：** 指定动作指令发送到哪个开发板

**文件：** `/home/admin/.openclaw/workspace/skills/robot-behavior/references/clients.json`

**当前内容：**
```json
{
  "clients": {
    "milk_duos_001": {
      "webhook_url": "http://192.168.1.xxx:8765/action/milk_duos_001",
      ...
    }
  }
}
```

**需要修改：**
- 将 `192.168.1.xxx` 替换为 **OpenClaw 服务器的实际 IP 地址**

**操作步骤：**

1. 查看 OpenClaw 服务器 IP：
   ```bash
   hostname -I | awk '{print $1}'
   ```

2. 编辑配置文件：
   ```bash
   nano /home/admin/.openclaw/workspace/skills/robot-behavior/references/clients.json
   ```

3. 替换 IP 地址并保存

---

### 3. HTTP 接收服务部署

**用途：** 接收 WebApp 发送的情绪数据

**状态：** 尚未创建

**需要创建的文件：**
```
/home/admin/.openclaw/workspace/services/webhook-receiver/
├── server.py              # HTTP 服务器
├── config.json            # 服务配置
└── logs/                  # 日志目录
```

**服务功能：**
- 接收 WebApp 的 POST 请求（`/emotion` 端点）
- 调用 `robot-behavior` 分析情绪
- 调用 `json-webhook-skill` 发送动作到 DuoS
- 返回处理结果

**端口：** 默认 8765（可配置）

**启动方式：**
```bash
# 后台运行
nohup python3 /home/admin/.openclaw/workspace/services/webhook-receiver/server.py > /dev/null 2>&1 &

# 或作为 systemd 服务（推荐生产环境）
```

---

### 4. OpenClaw Gateway 重启

**用途：** 加载新创建的 skills

**命令：**
```bash
openclaw gateway restart
```

**验证：**
```bash
openclaw gateway status
```

---

### 5. Milk DuoS 开发板配置

**用途：** 开发板连接 WiFi 并注册到 OpenClaw

**文件：** Milk DuoS 的 Arduino 代码

**需要修改：**
```cpp
const char* WIFI_SSID = "你的 WiFi 名称";
const char* WIFI_PASSWORD = "你的 WiFi 密码";
const char* OPENCLAW_SERVER = "http://<OpenClaw 服务器 IP>:8765";
const char* CLIENT_ID = "milk_duos_001";  // 每块板子唯一
```

**操作步骤：**

1. 在 Arduino IDE 中打开代码
2. 修改 WiFi 和服务器地址
3. 编译并上传到开发板
4. 打开串口监视器查看日志

---

### 6. 防火墙/网络配置

**用途：** 确保开发板和 WebApp 能访问 OpenClaw 服务

**需要开放的端口：**
| 端口 | 用途 | 方向 |
|------|------|------|
| 8765 | HTTP 接收服务 | 入站 |

**防火墙命令（如使用 ufw）：**
```bash
sudo ufw allow 8765/tcp
sudo ufw status
```

**验证：**
```bash
# 从其他设备测试
curl http://<OpenClaw 服务器 IP>:8765/health
```

---

### 7. 服务自启动配置（可选）

**用途：** 系统重启后自动运行 HTTP 接收服务

**方式 A：systemd 服务（推荐）**

创建文件 `/etc/systemd/system/openclaw-webhook.service`：

```ini
[Unit]
Description=OpenClaw Webhook Receiver
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/.openclaw/workspace/services/webhook-receiver
ExecStart=/usr/bin/python3 /home/admin/.openclaw/workspace/services/webhook-receiver/server.py
Restart=always
Environment=DASHSCOPE_API_KEY=sk-8e08c4db21e1485197dfd3571cc51f0a

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable openclaw-webhook
sudo systemctl start openclaw-webhook
sudo systemctl status openclaw-webhook
```

---

## 📋 配置检查清单

部署前逐项检查：

- [ ] 环境变量已持久化（`~/.bashrc`）
- [ ] `clients.json` 中的 IP 地址已更新
- [ ] HTTP 接收服务已创建并测试
- [ ] OpenClaw Gateway 已重启
- [ ] Milk DuoS 代码已上传并连接 WiFi
- [ ] 防火墙端口 8765 已开放
- [ ] （可选）systemd 服务已配置

---

## 🧪 测试流程

配置完成后，按顺序测试：

### 1. 测试情绪分析
```bash
export DASHSCOPE_API_KEY="sk-8e08c4db21e1485197dfd3571cc51f0a"
python3 /home/admin/.openclaw/workspace/skills/robot-behavior/scripts/analyze_emotion.py \
  --input "我今天很开心" \
  --pretty
```

### 2. 测试 HTTP 接收服务
```bash
curl -X POST http://localhost:8765/emotion \
  -H "Content-Type: application/json" \
  -d '{"content":"我很难过"}'
```

### 3. 测试开发板连接
- 查看开发板串口日志
- 确认 WiFi 连接成功
- 确认注册到 OpenClaw 成功

### 4. 端到端测试
- WebApp 发送情绪 → OpenClaw → DuoS 执行动作

---

## 📞 问题排查

### API Key 问题
```bash
# 检查是否配置
echo $DASHSCOPE_API_KEY

# 测试 API
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-omni-flash","messages":[{"role":"user","content":"test"}]}'
```

### 网络连通性
```bash
# 从开发板所在网络测试
ping <OpenClaw 服务器 IP>
curl http://<OpenClaw 服务器 IP>:8765/health
```

### 服务状态
```bash
# OpenClaw Gateway
openclaw gateway status

# HTTP 接收服务（如配置 systemd）
sudo systemctl status openclaw-webhook
```

---

## 📝 联系信息

如遇问题，记录以下信息：

1. OpenClaw 服务器 IP：_________________
2. Milk DuoS 客户端 ID：_________________
3. WebApp 地址：_________________
4. 问题描述：_________________

---

**文档版本：** 1.0  
**更新日期：** 2026-04-23  
**维护者：** Claw 🦞
