---
name: json-webhook-skill
description: 生成指定格式的 JSON 数据并发送到 Webhook 地址。使用场景：(1) 需要推送结构化数据到外部系统 (2) 调用第三方 API (3) 发送事件通知 (4) 数据同步到外部服务
---

# JSON Webhook 技能

## 核心功能

1. 根据用户需求生成符合 schema 的 JSON 数据
2. 验证 JSON 格式和必填字段
3. 发送 HTTP POST 请求到指定地址
4. 返回响应结果和发送日志

## 工作流程

```
用户请求 → 生成 JSON → 验证 Schema → 发送 Webhook → 返回结果
```

## 使用方法

### 基本用法

用户提供：
- 目标 URL（或从配置中选择）
- 事件类型/数据内容

示例：
> "发送一个用户注册事件到 https://api.example.com/webhook"

### 发送方式

**方式 A：使用内置脚本（推荐）**

```bash
scripts/send_webhook.py --url <WEBHOOK_URL> --data '<JSON>'
```

**方式 B：使用 curl**

```bash
curl -X POST <URL> -H "Content-Type: application/json" -d '<JSON>'
```

## JSON Schema

参考 [references/json-schema.md](references/json-schema.md) 获取完整的格式定义和示例。

## 端点配置

参考 [references/endpoints.md](references/endpoints.md) 配置目标地址和认证信息。

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| JSON 格式错误 | 重新生成并验证 |
| 网络超时 | 重试 1 次，返回错误信息 |
| HTTP 非 2xx | 返回状态码和响应体 |
| Schema 验证失败 | 指出缺失/错误字段 |

## 安全注意

- ⚠️ 敏感 URL 和 API Key 使用环境变量或配置文件
- ⚠️ 发送前向用户确认目标地址和内容
- ⚠️ 不要记录敏感数据到日志
- ⚠️ 生产环境使用 HTTPS

## 相关文件

- `scripts/send_webhook.py` - HTTP 发送脚本
- `references/json-schema.md` - JSON 格式定义
- `references/endpoints.md` - 端点配置
