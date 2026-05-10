#!/usr/bin/env python3
"""
导演模式 - 拍视频专用版

用途：输入长故事，输出优化后的动作序列并发送到队列
特点：禁用 clear_old，保证所有段落都能入队

使用方法：
python3 director_video.py --story "故事内容" --send http://localhost:8765
"""

import json
import sys
import argparse
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# 已去除所有站立动作 (0)，让演绎更紧凑
ACTION_MAP = {
    "happy": {"formal": [1], "warm": [1, 6], "climax": [1, 6, 7], "default": [1, 6]},
    "grateful": {"formal": [3, 4], "warm": [3, 1], "climax": [3, 4, 1, 6], "default": [3, 4]},
    "scared": {"formal": [8, 10], "warm": [8], "climax": [10, 8, 10], "default": [8, 10]},
    "sad": {"formal": [2, 8], "warm": [2], "climax": [2, 8, 10], "default": [2, 8]},
    "angry": {"formal": [2, 5], "warm": [2], "climax": [2, 5, 2], "default": [2, 5]},
    "surprised": {"formal": [10, 1], "warm": [10], "climax": [10, 1, 10], "default": [10, 1]},
    "calm": {"formal": [], "warm": [1], "climax": [], "default": []},  # calm 无动作或挥手
}

ACTION_NAMES = {0:"站立",1:"挥手",2:"摇头",3:"一边致谢",4:"另一边致谢",5:"交通指挥",6:"舞蹈歌曲",7:"自由飞翔",8:"下蹲",9:"前进 2 步",10:"后退 2 步"}

def extract_emotion(text):
    """提取单个段落的情绪"""
    import subprocess
    result = subprocess.Popen(
        ["python3", "/home/admin/.openclaw/workspace/skills/robot-behavior/scripts/analyze_emotion.py", "--input", text],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, _ = result.communicate()
    try:
        data = json.loads(stdout.decode('utf-8'))
        if data.get("status") == "success":
            return data.get("emotion_detected", "calm")
    except:
        pass
    return "calm"

def assign_style(emotions):
    """分配风格：避免重复，添加高潮"""
    styles = []
    seen = {}
    climax_idx = len(emotions) - 1  # 最后一段是高潮
    
    # 找 scared 段落作为高潮
    for i, e in enumerate(emotions):
        if e in ["scared", "angry", "surprised"]:
            climax_idx = i
    
    for i, emotion in enumerate(emotions):
        if i == climax_idx:
            style = "climax"
        elif emotion in seen:
            style = "warm"  # 重复情绪用 warm 变体
        else:
            style = "formal"  # 首次出现用 formal
        
        seen[emotion] = seen.get(emotion, 0) + 1
        styles.append(style)
    
    return styles

def send_action(webhook_url, client_id, action_seq, emotion, segment):
    """发送动作到队列"""
    url = f"{webhook_url}/action/{client_id}"
    data = {"action_sequence": action_seq, "emotion": emotion, "segment_index": segment}
    try:
        r = requests.post(url, json=data, timeout=10)
        return r.status_code == 200, r.json()
    except Exception as e:
        return False, {"error": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", "-s", required=True)
    parser.add_argument("--send", default="http://localhost:8765")
    parser.add_argument("--client", default="milk_duos_001")
    args = parser.parse_args()
    
    if not DASHSCOPE_API_KEY:
        print("❌ 请设置 DASHSCOPE_API_KEY 环境变量")
        sys.exit(1)
    
    # 拆分故事
    segments = [s.strip() for s in args.story.replace('。','\n').replace('!','\n').replace('?','\n').split('\n') if len(s.strip()) > 5]
    if len(segments) <= 1:
        segments = [s.strip() for s in args.story.replace(',','\n').replace(',','\n').split('\n') if len(s.strip()) > 5]
    
    print(f"📖 故事拆分为 {len(segments)} 段")
    
    # 并发提取情绪
    print("⚡ 提取情绪标签...")
    start = time.time()
    with ThreadPoolExecutor(max_workers=5) as ex:
        emotions = list(ex.map(extract_emotion, segments))
    print(f"✅ {int((time.time()-start)*1000)} ms")
    
    # 分配风格
    styles = assign_style(emotions)
    
    # 生成动作并发送
    print("🎯 生成动作序列并发送到队列...")
    results = []
    for i, (seg, emotion, style) in enumerate(zip(segments, emotions, styles), 1):
        action_seq = ACTION_MAP.get(emotion, {}).get(style, ACTION_MAP.get(emotion, {}).get("default", []))
        # calm 无动作时，跳过该段落
        if not action_seq:
            print(f"  ⏭️ 段落{i}: {emotion}+{style} → (跳过，无动作)")
            continue
        action_names = "→".join([ACTION_NAMES.get(a,"?") for a in action_seq])
        
        success, resp = send_action(args.send, args.client, action_seq, emotion, i)
        status = "✅" if success else "❌"
        print(f"  {status} 段落{i}: {emotion}+{style} → {action_names}")
        results.append({"segment":i, "emotion":emotion, "style":style, "actions":action_seq})
    
    # 汇总
    total = sum(len(r["actions"]) for r in results)
    print(f"\n📊 总计：{len(results)}段，{total}个动作，平均{total/len(results):.1f}动作/段")
    print("✅ 拍视频准备完成！")

if __name__ == "__main__":
    main()
