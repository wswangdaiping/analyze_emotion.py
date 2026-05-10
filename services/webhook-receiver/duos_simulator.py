#!/usr/bin/env python3
"""
Milk DuoS 模拟器 - Python 测试版本
用于在 Windows/电脑上测试与 OpenClaw 服务器的连接

功能：
- 轮询 OpenClaw 服务器获取动作指令
- 模拟执行动作（串口输出）
- 确认动作完成

使用方法：
python duos_simulator.py
"""

import json
import time
import requests
from datetime import datetime

# ========== 配置 ==========
OPENCLAW_SERVER = "http://47.93.27.196:8765"  # OpenClaw 服务器地址
CLIENT_ID = "milk_duos_001"                    # 客户端 ID
POLL_INTERVAL = 2                              # 轮询间隔（秒）

# 动作映射表（用于显示）
ACTION_NAMES = {
    0: "站立",
    1: "挥手",
    2: "摇头",
    3: "一边致谢",
    4: "另一边致谢",
    5: "交通指挥",
    6: "舞蹈歌曲",
    7: "自由飞翔",
    8: "下蹲",
    9: "前进 2 步",
    10: "后退 2 步"
}


def poll_action():
    """轮询动作指令"""
    url = f"{OPENCLAW_SERVER}/poll/{CLIENT_ID}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"轮询失败：{e}")
        return None


def execute_action(action_sequence: list, command_id: str):
    """执行动作序列"""
    print(f"\n{'='*60}")
    print(f"收到动作指令：{command_id}")
    print(f"动作序列：{action_sequence}")
    print(f"{'='*60}")
    
    for i, action in enumerate(action_sequence):
        action_name = ACTION_NAMES.get(action, "未知")
        print(f"[{i+1}] 执行动作 #{action}: {action_name}")
        time.sleep(0.5)  # 模拟动作执行时间
    
    print(f"{'='*60}")
    print("动作序列执行完成！")
    print(f"{'='*60}\n")
    
    # 确认动作完成
    acknowledge_action(command_id)


def acknowledge_action(command_id: str):
    """确认动作完成"""
    url = f"{OPENCLAW_SERVER}/ack/{CLIENT_ID}"
    data = {"command_id": command_id}
    
    try:
        response = requests.post(url, json=data, timeout=5)
        if response.status_code == 200:
            print(f"✓ 已确认动作：{command_id}")
    except Exception as e:
        print(f"确认失败：{e}")


def test_emotion(emotion_text: str):
    """测试发送情绪数据"""
    url = f"{OPENCLAW_SERVER}/emotion"
    data = {"content": emotion_text}
    
    print(f"\n发送情绪：{emotion_text}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("status") == "success":
            print(f"✓ 情绪分析成功")
            print(f"  情绪：{result.get('emotion')}")
            print(f"  动作：{result.get('action_sequence')}")
            print(f"  指令 ID: {result.get('command_id')}")
        else:
            print(f"✗ 情绪分析失败：{result}")
    except Exception as e:
        print(f"✗ 请求失败：{e}")


def main():
    print(f"{'='*60}")
    print(f"Milk DuoS 模拟器 - Python 测试版")
    print(f"{'='*60}")
    print(f"服务器：{OPENCLAW_SERVER}")
    print(f"客户端 ID: {CLIENT_ID}")
    print(f"轮询间隔：{POLL_INTERVAL}秒")
    print(f"{'='*60}")
    
    # 测试连接
    print("\n测试服务器连接...")
    try:
        response = requests.get(f"{OPENCLAW_SERVER}/health", timeout=5)
        if response.status_code == 200:
            print("✓ 服务器连接成功")
        else:
            print(f"✗ 服务器响应异常：{response.status_code}")
    except Exception as e:
        print(f"✗ 无法连接服务器：{e}")
        return
    
    # 主循环 - 轮询动作
    print(f"\n开始轮询动作指令（按 Ctrl+C 停止）...")
    print(f"提示：可以在另一个窗口运行测试情绪发送\n")
    
    last_action_id = None
    
    try:
        while True:
            result = poll_action()
            
            if result and result.get("status") == "pending":
                command_id = result.get("command_id")
                action_sequence = result.get("action_sequence")
                
                # 避免重复执行
                if command_id != last_action_id:
                    execute_action(action_sequence, command_id)
                    last_action_id = command_id
            elif result and result.get("status") == "no_action":
                # 没有新动作，静默
                pass
            else:
                print(f"轮询响应：{result}")
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n程序已停止")


if __name__ == "__main__":
    # 如果直接运行，启动轮询模式
    # 如果带参数，发送测试情绪
    import sys
    
    if len(sys.argv) > 1:
        # 测试模式：发送情绪
        emotion_text = " ".join(sys.argv[1:])
        test_emotion(emotion_text)
    else:
        # 轮询模式：模拟 DuoS
        main()
