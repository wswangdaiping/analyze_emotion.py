#!/usr/bin/env python3
"""
DuoS 测试工具 - 直接发送动作指令到队列

用途：在不通过 WebApp 的情况下，测试 DuoS 是否能接收动作

使用方法：
python test_duos.py                          # 交互式
python test_duos.py --action 1,6,0           # 直接发送
python test_duos.py --emotion happy          # 按情绪发送
"""

import json
import requests
import sys

# 配置
OPENCLAW_SERVER = "http://47.93.27.196:8765"
CLIENT_ID = "milk_duos_001"

# 情绪→动作映射
EMOTION_ACTIONS = {
    "happy": [1, 6, 0],
    "sad": [2, 8, 0],
    "scared": [8, 10, 0],
    "grateful": [3, 4, 0],
    "angry": [2, 5, 0],
    "calm": [0],
    "surprised": [10, 1, 0]
}

# 动作名称
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


def send_action(action_sequence: list, emotion: str = None):
    """发送动作指令到队列"""
    url = f"{OPENCLAW_SERVER}/action/{CLIENT_ID}"
    data = {
        "action_sequence": action_sequence,
        "emotion": emotion
    }
    
    print(f"发送动作到 {CLIENT_ID}...")
    print(f"动作序列：{action_sequence}")
    print(f"动作名称：{[ACTION_NAMES.get(a, '未知') for a in action_sequence]}")
    if emotion:
        print(f"情绪：{emotion}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("status") == "success":
            print(f"\n✅ 发送成功！")
            print(f"指令 ID: {result.get('command_id')}")
            print(f"\nDuoS 将在下次轮询时收到此动作（最多 2 秒）")
        else:
            print(f"\n❌ 发送失败：{result}")
        
        return result
    except Exception as e:
        print(f"\n❌ 请求失败：{e}")
        return None


def send_emotion(emotion: str):
    """按情绪发送预设动作"""
    if emotion not in EMOTION_ACTIONS:
        print(f"未知情绪：{emotion}")
        print(f"支持的情绪：{list(EMOTION_ACTIONS.keys())}")
        return
    
    action_sequence = EMOTION_ACTIONS[emotion]
    return send_action(action_sequence, emotion)


def interactive_mode():
    """交互式模式"""
    print("=" * 60)
    print("DuoS 测试工具 - 交互式模式")
    print("=" * 60)
    print(f"服务器：{OPENCLAW_SERVER}")
    print(f"客户端：{CLIENT_ID}")
    print("=" * 60)
    print("\n支持的情绪：")
    for emotion, actions in EMOTION_ACTIONS.items():
        action_names = [ACTION_NAMES.get(a) for a in actions]
        print(f"  {emotion:10} → {actions} ({'→'.join(action_names)})")
    print("=" * 60)
    print("\n输入情绪名称发送动作，或输入 'q' 退出\n")
    
    while True:
        try:
            user_input = input("请输入情绪 > ").strip().lower()
            
            if user_input == 'q':
                print("退出")
                break
            
            if user_input in EMOTION_ACTIONS:
                send_emotion(user_input)
            else:
                # 尝试解析为动作序列
                try:
                    actions = [int(x.strip()) for x in user_input.split(',')]
                    send_action(actions)
                except:
                    print(f"未知情绪或无效格式。支持的情绪：{list(EMOTION_ACTIONS.keys())}")
            
            print()
        except KeyboardInterrupt:
            print("\n退出")
            break
        except Exception as e:
            print(f"错误：{e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="DuoS 测试工具")
    parser.add_argument("--emotion", "-e", help="按情绪发送（happy/sad/scared 等）")
    parser.add_argument("--action", "-a", help="直接发送动作序列（如：1,6,0）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式模式")
    
    args = parser.parse_args()
    
    if args.emotion:
        send_emotion(args.emotion)
    elif args.action:
        try:
            actions = [int(x.strip()) for x in args.action.split(',')]
            send_action(actions)
        except:
            print(f"无效的动作序列格式。示例：--action 1,6,0")
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
