# Webhook 端点配置

配置目标地址、认证方式和环境切换。

---

## 配置方式

### 方式 A：直接使用 URL

在请求中直接指定完整 URL：

```bash
--url https://api.example.com/webhook
```

### 方式 B：使用环境变量（推荐生产环境）

```bash
export WEBHOOK_URL="https://api.example.com/webhook"
export WEBHOOK_AUTH_TOKEN="your_token_here"
```

脚本中引用：
```bash
--url "$WEBHOOK_URL" --header "Authorization=Bearer $WEBHOOK_AUTH_TOKEN"
```

### 方式 C：在 Skill 中记录常用端点

 Below 列出常用端点，使用时复制 URL。

---

## 生产环境端点

| 名称 | URL | 认证方式 | 说明 |
|------|-----|----------|------|
| 主服务 | `https://api.example.com/webhook` | Bearer Token | 主要接收端 |
| 备用服务 | `https://backup.example.com/events` | API Key | 故障转移 |
| 数据分析 | `https://analytics.example.com/ingest` | HMAC | 数据归档 |

### 认证头示例

**Bearer Token:**
```
Authorization: Bearer your_token_here
```

**API Key:**
```
X-API-Key: your_api_key_here
```

**Custom Auth:**
```
X-Auth-Token: your_custom_token
```

---

## 测试环境端点

| 名称 | URL | 说明 |
|------|-----|------|
| 本地开发 | `http://localhost:8080/webhook` | 本地服务 |
| 内网测试 | `http://192.168.1.100:3000/events` | 内网服务器 |
| Webhook.site | `https://webhook.site/你的 UUID` | 临时测试 |
| RequestBin | `https://requestbin.com/r/你的 ID` | 请求调试 |

### 使用 Webhook.site 测试

1. 访问 https://webhook.site
2. 复制生成的唯一 URL
3. 发送到该 URL 查看请求详情

---

## 环境切换

### 开发环境
```bash
WEBHOOK_ENV=dev
WEBHOOK_URL=http://localhost:8080/webhook
```

### 测试环境
```bash
WEBHOOK_ENV=test
WEBHOOK_URL=https://test-api.example.com/webhook
```

### 生产环境
```bash
WEBHOOK_ENV=prod
WEBHOOK_URL=https://api.example.com/webhook
```

---

## 超时配置

| 场景 | 推荐超时 |
|------|----------|
| 内网服务 | 10 秒 |
| 公网 API | 30 秒 |
| 慢速服务 | 60 秒 |

使用 `--timeout` 参数调整：
```bash
--timeout 60
```

---

## 重试策略

当前脚本不自动重试。如需重试：

1. 检查返回的 `success` 字段
2. 如为 `false` 且为网络错误，手动重试
3. 生产环境建议添加重试逻辑到调用方

---

## 安全建议

1. ✅ 生产环境始终使用 HTTPS
2. ✅ 敏感 Token 使用环境变量，不要硬编码
3. ✅ 定期轮换认证 Token
4. ✅ 记录发送日志但脱敏敏感信息
5. ⚠️ 不要将包含 Token 的完整请求日志提交到版本控制

---

## 快速使用

```bash
# 测试发送
python scripts/send_webhook.py \
  --url https://webhook.site/你的 UUID \
  --data '{"event":"test","data":{"message":"hello"}}'

# 生产发送（带认证）
python scripts/send_webhook.py \
  --url https://api.example.com/webhook \
  --data '{"event":"user.created","data":{"id":"usr_123"}}' \
  --header "Authorization=Bearer $WEBHOOK_AUTH_TOKEN" \
  --timeout 30
```
