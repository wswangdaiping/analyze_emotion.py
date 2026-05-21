#!/usr/bin/env python3
"""
发送 JSON 数据到 Webhook 地址

用法:
    python send_webhook.py --url <WEBHOOK_URL> --data '<JSON>'
    python send_webhook.py --url <WEBHOOK_URL> --data '<JSON>' --header "Authorization=Bearer xxx"
    python send_webhook.py --url <WEBHOOK_URL> --data '<JSON>' --timeout 60
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "缺少 requests 库，请运行：pip install requests",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }))
    sys.exit(1)


def send_webhook(url: str, data: dict, headers: dict = None, timeout: int = 60) -> dict:
    """
    发送 POST 请求到 Webhook 地址
    
    Args:
        url: 目标 URL
        data: JSON 数据（字典）
        headers: 额外 Headers（可选）
        timeout: 超时秒数（默认 60）
    
    Returns:
        包含发送结果的字典
    """
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    start_time = datetime.now(timezone.utc)
    
    try:
        response = requests.post(
            url,
            json=data,
            headers=default_headers,
            timeout=timeout
        )
        
        elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        result = {
            "success": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "response_body": response.text[:5000],  # 限制响应长度
            "elapsed_ms": round(elapsed_ms, 2),
            "timestamp": start_time.isoformat(),
            "url": url
        }
        
        return result
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": f"请求超时（>{timeout}秒）",
            "timestamp": start_time.isoformat(),
            "url": url
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": f"连接失败：{str(e)}",
            "timestamp": start_time.isoformat(),
            "url": url
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"发送失败：{str(e)}",
            "timestamp": start_time.isoformat(),
            "url": url
        }


def parse_headers(header_list: list) -> dict:
    """解析 header 列表为字典"""
    headers = {}
    if header_list:
        for h in header_list:
            if "=" in h:
                key, value = h.split("=", 1)
                headers[key.strip()] = value.strip()
    return headers


def main():
    parser = argparse.ArgumentParser(
        description="发送 JSON 数据到 Webhook 地址",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s --url https://api.example.com/webhook --data '{"event":"test"}'
    %(prog)s --url https://api.example.com/webhook --data '{"event":"test"}' --header "Authorization=Bearer xxx"
        """
    )
    
    parser.add_argument(
        "--url",
        required=True,
        help="Webhook URL（必填）"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="JSON 数据字符串（必填）"
    )
    parser.add_argument(
        "--header",
        action="append",
        dest="headers",
        metavar="KEY=VALUE",
        help="额外 Header，可多次使用 (例如：--header 'Authorization=Bearer xxx')"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="超时秒数（默认 30）"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="美化输出 JSON"
    )
    
    args = parser.parse_args()
    
    # 解析 JSON 数据
    try:
        data = json.loads(args.data)
        if not isinstance(data, dict):
            raise ValueError("JSON 根元素必须是对象")
    except json.JSONDecodeError as e:
        result = {
            "success": False,
            "error": f"JSON 格式错误：{str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        print(json.dumps(result, indent=2 if args.pretty else None))
        sys.exit(1)
    except ValueError as e:
        result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        print(json.dumps(result, indent=2 if args.pretty else None))
        sys.exit(1)
    
    # 解析 Headers
    headers = parse_headers(args.headers)
    
    # 发送请求
    result = send_webhook(args.url, data, headers, args.timeout)
    
    # 输出结果
    print(json.dumps(result, indent=2 if args.pretty else None))
    
    # 根据结果设置退出码
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
