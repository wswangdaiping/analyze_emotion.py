# JSON Schema 定义

本文档定义常用的 JSON 数据格式。根据实际需求选择或扩展。

---

## 通用事件格式

适用于大多数事件通知场景。

```json
{
  "event": "string",
  "timestamp": "ISO8601 字符串",
  "data": {
    "id": "string",
    "type": "string",
    "attributes": {}
  },
  "metadata": {
    "source": "openclaw",
    "version": "1.0",
    "request_id": "string（可选）"
  }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| event | string | 是 | 事件名称，如 `user.created` |
| timestamp | string | 是 | ISO8601 格式时间戳 |
| data | object | 是 | 业务数据主体 |
| data.id | string | 推荐 | 资源唯一标识 |
| data.type | string | 推荐 | 资源类型 |
| metadata | object | 否 | 元数据 |
| metadata.source | string | 否 | 数据来源，默认 `openclaw` |
| metadata.version | string | 否 | 格式版本 |

---

## 用户事件 Schema

### user.created（用户创建）

```json
{
  "event": "user.created",
  "timestamp": "2026-04-23T15:00:00+08:00",
  "data": {
    "id": "usr_xxx",
    "email": "user@example.com",
    "name": "张三",
    "created_at": "2026-04-23T15:00:00+08:00"
  }
}
```

### user.updated（用户更新）

```json
{
  "event": "user.updated",
  "timestamp": "2026-04-23T15:00:00+08:00",
  "data": {
    "id": "usr_xxx",
    "changes": {
      "field": "name",
      "old_value": "张三",
      "new_value": "李四"
    }
  }
}
```

### user.deleted（用户删除）

```json
{
  "event": "user.deleted",
  "timestamp": "2026-04-23T15:00:00+08:00",
  "data": {
    "id": "usr_xxx",
    "reason": "user_request"
  }
}
```

---

## 订单事件 Schema

### order.created（订单创建）

```json
{
  "event": "order.created",
  "timestamp": "2026-04-23T15:00:00+08:00",
  "data": {
    "order_id": "ord_xxx",
    "user_id": "usr_xxx",
    "total_amount": 99.00,
    "currency": "CNY",
    "items": [
      {
        "product_id": "prod_xxx",
        "quantity": 2,
        "price": 49.50
      }
    ],
    "status": "pending"
  }
}
```

### order.paid（订单支付）

```json
{
  "event": "order.paid",
  "timestamp": "2026-04-23T15:00:00+08:00",
  "data": {
    "order_id": "ord_xxx",
    "payment_id": "pay_xxx",
    "amount": 99.00,
    "payment_method": "alipay"
  }
}
```

---

## 自定义 Schema

如需自定义格式，请提供：

1. **字段列表** - 每个字段的名称、类型、是否必填
2. **嵌套结构** - 如有嵌套对象，说明层级
3. **枚举值** - 如字段有固定选项，列出所有可能值
4. **示例** - 至少一个完整的 JSON 示例

### 模板

```json
{
  "字段 1": "类型/说明",
  "字段 2": {
    "嵌套字段": "类型/说明"
  },
  "数组字段": ["类型/说明"]
}
```

---

## 验证规则

生成 JSON 时遵循：

1. ✅ 所有必填字段必须存在
2. ✅ 时间戳使用 ISO8601 格式（带时区）
3. ✅ 数字类型不使用字符串
4. ✅ 布尔值使用 `true`/`false` 而非字符串
5. ✅ 空值使用 `null` 而非空字符串

---

## 快速参考

### ISO8601 时间戳格式

```
2026-04-23T15:00:00+08:00
2026-04-23T07:00:00Z        # UTC
```

### 常见事件命名

```
user.created / user.updated / user.deleted
order.created / order.paid / order.shipped
payment.success / payment.failed
notification.sent
```
