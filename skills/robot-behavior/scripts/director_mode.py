#!/usr/bin/env python3
"""
导演模式 - 一键运行脚本

用途：输入长故事，输出优化后的动作序列（带情绪曲线和动作变体）
延迟：~3 秒（5 段并发）

使用方法：
python3 director_mode.py --story "故事内容" --pretty
python3 director_mode.py --story "早上小明..." --send http://localhost:8765 --client milk_duos_001
"""

import json
import sys
import argparse
import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ========== 配置 ==========
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
ANALYZE_SCRIPT_PATH = Path(__file__).resolve().parent / "analyze_emotion.py"
ACTION_NAMES = {
    0: "站立", 1: "挥手", 2: "摇头", 3: "一边致谢", 4: "另一边致谢",
    5: "交通指挥", 6: "舞蹈歌曲", 7: "自由飞翔", 8: "下蹲",
    9: "前进 2 步", 10: "后退 2 步"
}

# ========== 动作变体映射表 ==========
ACTION_MAP = {
    "happy": {
        "default": [1, 6, 0],
        "formal": [1, 0],
        "warm": [1, 6, 0],
        "climax": [1, 6, 7, 0],
        "gentle": [1, 0],
        "transition": [1, 9, 0],
    },
    "grateful": {
        "default": [3, 4, 0],
        "formal": [3, 4, 0],
        "warm": [3, 1, 0],
        "climax": [3, 4, 1, 6, 0],
        "gentle": [3, 0],
        "transition": [4, 1, 0],
    },
    "scared": {
        "default": [8, 10, 0],
        "formal": [8, 10, 0],
        "warm": [8, 0],
        "climax": [10, 8, 10, 0],
        "gentle": [10, 0],
        "transition": [8, 1, 0],
    },
    "sad": {
        "default": [2, 8, 0],
        "formal": [2, 8, 0],
        "warm": [2, 0],
        "climax": [2, 8, 10, 0],
        "gentle": [2, 0],
        "transition": [8, 2, 0],
    },
    "angry": {
        "default": [2, 5, 0],
        "formal": [2, 5, 0],
        "warm": [2, 0],
        "climax": [2, 5, 2, 0],
        "gentle": [2, 0],
        "transition": [5, 2, 0],
    },
    "surprised": {
        "default": [10, 1, 0],
        "formal": [10, 1, 0],
        "warm": [10, 0],
        "climax": [10, 1, 10, 0],
        "gentle": [1, 0],
        "transition": [10, 1, 9, 0],
    },
    "calm": {
        "default": [0],
        "formal": [0],
        "warm": [0, 1, 0],
        "climax": [0],
        "gentle": [0],
        "transition": [0, 1, 0],
    },
}


def split_story(story: str) -> list:
    """拆分故事为段落"""
    sentences = re.split(r'[。！？.!?]', story)
    segments = [s.strip() for s in sentences if len(s.strip()) > 5]
    
    if len(segments) <= 1:
        segments = [s.strip() for s in re.split(r'[，,]', story) if len(s.strip()) > 5]
    
    return segments


def extract_emotion(text: str) -> dict:
    """并发提取单个段落的情绪标签"""
    import subprocess
    
    start = time.time()
    result = subprocess.Popen(
        [sys.executable, str(ANALYZE_SCRIPT_PATH), "--input", text],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = result.communicate()
    elapsed = (time.time() - start) * 1000
    
    try:
        data = json.loads(stdout.decode('utf-8'))
        if data.get("status") == "success":
            return {
                "emotion": data.get("emotion_detected"),
                "intensity": 0.7,  # 默认中等强度
                "elapsed_ms": int(elapsed)
            }
    except:
        pass
    
    return {"emotion": "calm", "intensity": 0.5, "elapsed_ms": int(elapsed)}


def director_analyze(emotion_sequence: list) -> dict:
    """导演模型：分析情绪曲线，推荐风格"""
    
    # 构建输入
    emotion_str = " → ".join([f"{s['emotion']}({s['intensity']})" for s in emotion_sequence])
    
    # 简化版导演提示词（快速响应）- 明确高潮规则
    prompt = f"""分析情绪序列，为每段推荐动作风格。

规则：
1. scared/angry/surprised 段落 → climax（情绪高潮）
2. 最后一段 → climax（结尾高潮）
3. 重复的情绪 → warm（避免重复）
4. 首次出现的情绪 → formal
5. 其他 → default

输入：{emotion_str}

输出 JSON（只输出 JSON，无其他文字）：
{{"segments": [{{"segment": 1, "emotion": "happy", "style": "formal"}}, ...]}}"""

    # 调用轻量模型
    try:
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen-turbo",
                "input": {"messages": [{"role": "user", "content": prompt}]},
                "parameters": {"result_format": "message"}
            },
            timeout=5
        )
        
        content = response.json()["output"]["choices"][0]["message"]["content"]
        # 提取 JSON
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"导演模型调用失败：{e}，使用默认风格")
    
    # 降级：手动分配风格（智能高潮检测）
    segments = []
    seen_emotions = {}
    
    # 找到情绪最高点（高潮位置）- 通常最后一段或 scared 段落是高潮
    # 简单规则：scared 段落或最后一段作为 climax
    climax_candidates = []
    for i, seg in enumerate(emotion_sequence):
        if seg["emotion"] in ["scared", "angry", "surprised"]:
            climax_candidates.append(i)
        if i == len(emotion_sequence) - 1:  # 最后一段
            climax_candidates.append(i)
    
    for i, seg in enumerate(emotion_sequence, 1):
        emotion = seg["emotion"]
        intensity = seg["intensity"]
        
        # 高潮位置 → climax
        if (i - 1) in climax_candidates:
            style = "climax"
        # 重复情绪 → warm（避免重复）
        elif emotion in seen_emotions:
            style = "warm"
        # 首次出现 → formal
        else:
            style = "formal"
        
        seen_emotions[emotion] = seen_emotions.get(emotion, 0) + 1
        
        segments.append({
            "segment": i,
            "emotion": emotion,
            "style": style
        })
    
    return {"segments": segments}


def select_action(emotion: str, style: str) -> list:
    """根据情绪和风格选择动作序列"""
    style_map = ACTION_MAP.get(emotion, {})
    return style_map.get(style, style_map.get("default", [0]))


def send_to_webhook(webhook_url: str, client_id: str, action_sequence: list, emotion: str, segment_index: int) -> dict:
    """发送动作序列到 Webhook 队列"""
    import uuid
    
    data = {
        "action_sequence": action_sequence,
        "emotion": emotion,
        "segment_index": segment_index
    }
    
    url = f"{webhook_url}/action/{client_id}"
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return {
            "success": response.status_code == 200,
            "response": response.json(),
            "status_code": response.status_code
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="导演模式 - 长故事演绎优化")
    parser.add_argument("--story", "-s", required=True, help="故事内容")
    parser.add_argument("--send", default=None, help="Webhook URL（如 http://localhost:8765）")
    parser.add_argument("--client", default="milk_duos_001", help="客户端 ID")
    parser.add_argument("--pretty", action="store_true", help="美化输出")
    
    args = parser.parse_args()
    
    if not DASHSCOPE_API_KEY:
        print(json.dumps({
            "status": "error",
            "error_message": "缺少 API Key，请设置 DASHSCOPE_API_KEY 环境变量"
        }, ensure_ascii=False))
        sys.exit(1)
    
    print("=" * 80)
    print("🎬 导演模式 - 长故事演绎优化")
    print("=" * 80)
    
    # Step 1: 拆分故事
    segments = split_story(args.story)
    print(f"\n📖 故事拆分为 {len(segments)} 个段落")
    
    if len(segments) == 0:
        print("❌ 无法拆分故事")
        sys.exit(1)
    
    # Step 2: 并发提取情绪
    print(f"\n⚡ 并发提取情绪标签...")
    start_extract = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(extract_emotion, seg): i for i, seg in enumerate(segments)}
        emotion_results = [None] * len(segments)
        
        for future in as_completed(futures):
            index = futures[future]
            emotion_results[index] = future.result()
    
    extract_time = (time.time() - start_extract) * 1000
    print(f"✅ 情绪提取完成 ({int(extract_time)} ms)")
    
    # 添加段落索引
    for i, (seg, emotion) in enumerate(zip(segments, emotion_results), 1):
        emotion["segment"] = i
        emotion["text"] = seg[:30] + "..." if len(seg) > 30 else seg
    
    # Step 3: 导演模型分析
    print(f"\n🎭 导演模型分析情绪曲线...")
    start_director = time.time()
    
    director_result = director_analyze(emotion_results)
    
    director_time = (time.time() - start_director) * 1000
    print(f"✅ 导演分析完成 ({int(director_time)} ms)")
    
    # Step 4: 生成动作序列
    print(f"\n🎯 生成动作序列...")
    
    final_results = []
    for seg in director_result.get("segments", []):
        emotion = seg["emotion"]
        style = seg.get("style", "default")
        action_seq = select_action(emotion, style)
        action_names = [ACTION_NAMES.get(a, "未知") for a in action_seq]
        
        result = {
            "segment": seg["segment"],
            "emotion": emotion,
            "style": style,
            "action_sequence": action_seq,
            "action_names": action_names
        }
        final_results.append(result)
    
    # Step 5: 发送到队列（可选）
    if args.send:
        print(f"\n📡 发送到 Webhook 队列...")
        for result in final_results:
            send_result = send_to_webhook(
                args.send,
                args.client,
                result["action_sequence"],
                result["emotion"],
                result["segment"]
            )
            
            if send_result.get("success"):
                print(f"  ✅ 段落{result['segment']} 已入队 (ID: {send_result.get('response', {}).get('command_id', 'N/A')})")
            else:
                print(f"  ❌ 段落{result['segment']} 发送失败：{send_result.get('error', '未知')}")
    
    # Step 6: 输出结果
    print(f"\n" + "=" * 80)
    print("📊 演绎结果")
    print("=" * 80)
    
    print(f"\n{'段落':<6} {'情绪':<10} {'风格':<10} {'动作序列':<25} {'动作名称':<35}")
    print("-" * 80)
    
    for result in final_results:
        seq_str = str(result["action_sequence"])
        names_str = "→".join(result["action_names"])
        print(f"{result['segment']:<6} {result['emotion']:<10} {result['style']:<10} {seq_str:<25} {names_str:<35}")
    
    # 统计
    total_actions = sum(len(r["action_sequence"]) for r in final_results)
    print(f"\n总计：{len(final_results)} 段落，{total_actions} 个动作，平均 {total_actions/len(final_results):.1f} 动作/段")
    
    # 输出 JSON
    output = {
        "status": "success",
        "total_segments": len(final_results),
        "total_actions": total_actions,
        "extract_time_ms": int(extract_time),
        "director_time_ms": int(director_time),
        "results": final_results,
        "timestamp": datetime.now().isoformat()
    }
    
    if args.pretty:
        print("\n" + json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print("\n" + json.dumps(output, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("✅ 导演模式完成")
    print("=" * 80)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
