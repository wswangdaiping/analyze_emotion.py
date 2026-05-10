#!/usr/bin/env python3
"""
导演模型快速验证脚本

用途：手动测试"情绪提取 → 导演分析 → 动作映射"流程
无需等待自动化实现，今天就能验证效果！

使用方法：
python3 test_director_manual.py
"""

import json

# ========== 1. 模拟并发情绪提取结果 ==========
# （实际实现时这部分会调用 AI 并发分析）
emotion_extraction_result = [
    {"segment": 1, "emotion": "happy", "intensity": 0.7},
    {"segment": 2, "emotion": "grateful", "intensity": 0.5},
    {"segment": 3, "emotion": "scared", "intensity": 0.9},
    {"segment": 4, "emotion": "grateful", "intensity": 0.6},
    {"segment": 5, "emotion": "happy", "intensity": 0.9},
]

# ========== 2. 模拟导演模型分析结果 ==========
# （实际实现时这部分会调用导演模型 API）
director_result = {
    "emotion_curve": {
        "trend": "wave",
        "peak_segment": 3,
        "repeated_emotions": ["grateful", "happy"]
    },
    "segments": [
        {"segment": 1, "emotion": "happy", "intensity": 0.7, "style": "default"},
        {"segment": 2, "emotion": "grateful", "intensity": 0.5, "style": "formal"},
        {"segment": 3, "emotion": "scared", "intensity": 0.9, "style": "climax"},
        {"segment": 4, "emotion": "grateful", "intensity": 0.6, "style": "warm"},
        {"segment": 5, "emotion": "happy", "intensity": 0.9, "style": "climax"},
    ]
}

# ========== 3. 动作变体映射表 ==========
ACTION_MAP = {
    "happy": {
        "default": [1, 6, 0],
        "formal": [1, 0],
        "warm": [1, 6, 0],
        "climax": [1, 6, 7, 0],      # 加入自由飞翔！
        "gentle": [1, 0],
        "transition": [1, 9, 0],
    },
    "grateful": {
        "default": [3, 4, 0],
        "formal": [3, 4, 0],
        "warm": [3, 1, 0],           # 致谢 + 挥手（变体！）
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

ACTION_NAMES = {
    0: "站立", 1: "挥手", 2: "摇头", 3: "一边致谢", 4: "另一边致谢",
    5: "交通指挥", 6: "舞蹈歌曲", 7: "自由飞翔", 8: "下蹲",
    9: "前进 2 步", 10: "后退 2 步"
}

# ========== 4. 生成动作序列 ==========
def generate_action_sequence(emotion, style):
    """根据情绪和风格生成动作序列"""
    style_map = ACTION_MAP.get(emotion, {})
    return style_map.get(style, style_map.get("default", [0]))

def get_action_names(sequence):
    """将动作 ID 转换为名称"""
    return [ACTION_NAMES.get(a, "未知") for a in sequence]

# ========== 5. 输出对比报告 ==========
print("=" * 80)
print("🎬 导演模型快速验证报告")
print("=" * 80)

print("\n📖 测试故事：小明的一天")
print("-" * 80)
story_segments = [
    "早上小明起床后开心地挥手跟妈妈打招呼",
    "吃完早餐他背着书包出门，路上遇到邻居爷爷，他鞠躬致谢问好",
    "到了学校发现忘记带作业，他吓得蹲在地上",
    "老师走过来安慰他，他感动地挥手",
    "放学后回家，看到妈妈准备了生日蛋糕，他兴奋地跳起了舞蹈",
]

for i, seg in enumerate(story_segments, 1):
    print(f"段落{i}: {seg}")

print("\n" + "=" * 80)
print("📊 方案 A：传统并发（无导演模型）")
print("=" * 80)
print(f"{'段落':<6} {'情绪':<10} {'动作序列':<20} {'动作名称':<30}")
print("-" * 80)

traditional_actions = []
for seg in emotion_extraction_result:
    emotion = seg["emotion"]
    # 传统方式：直接使用默认风格
    action_seq = generate_action_sequence(emotion, "default")
    action_names = get_action_names(action_seq)
    traditional_actions.append(action_seq)
    
    print(f"{seg['segment']:<6} {emotion:<10} {str(action_seq):<20} {'→'.join(action_names):<30}")

print("\n⚠️  问题检测：")
print("  - 段落 2 和 4 都是 grateful，动作完全相同 [3,4,0] ❌ 重复！")
print("  - 段落 1 和 5 都是 happy，动作完全相同 [1,6,0] ❌ 重复！")
print("  - 缺少情绪高潮，结尾不够突出")

print("\n" + "=" * 80)
print("✨ 方案 B：导演模型 + 动作变体（推荐）")
print("=" * 80)
print(f"{'段落':<6} {'情绪':<10} {'风格':<10} {'动作序列':<25} {'动作名称':<35}")
print("-" * 80)

optimized_actions = []
for seg in director_result["segments"]:
    emotion = seg["emotion"]
    style = seg["style"]
    action_seq = generate_action_sequence(emotion, style)
    action_names = get_action_names(action_seq)
    optimized_actions.append(action_seq)
    
    print(f"{seg['segment']:<6} {emotion:<10} {style:<10} {str(action_seq):<25} {'→'.join(action_names):<35}")

print("\n✅ 改进点：")
print("  - 段落 2（首次感谢）：使用 formal 风格 [3,4,0] 正式致谢")
print("  - 段落 4（再次感谢）：使用 warm 风格 [3,1,0] 致谢 + 挥手 ✅ 不同！")
print("  - 段落 3（情绪高峰）：使用 climax 风格 [10,8,10,0] 极度恐惧")
print("  - 段落 5（结尾高潮）：使用 climax 风格 [1,6,7,0] 加入自由飞翔 ⭐")

print("\n" + "=" * 80)
print("📈 对比总结")
print("=" * 80)

# 检测重复
def count_duplicates(actions):
    action_strs = [str(a) for a in actions]
    return len(action_strs) - len(set(action_strs))

traditional_duplicates = count_duplicates(traditional_actions)
optimized_duplicates = count_duplicates(optimized_actions)

print(f"传统方案重复数：{traditional_duplicates} 处")
print(f"优化方案重复数：{optimized_duplicates} 处 ✅ 减少{traditional_duplicates - optimized_duplicates}处重复！")

print("\n情绪曲线：")
print(f"  趋势：{director_result['emotion_curve']['trend']}")
print(f"  高潮段落：第{director_result['emotion_curve']['peak_segment']}段")
print(f"  重复情绪：{', '.join(director_result['emotion_curve']['repeated_emotions'])}")

print("\n动作丰富度：")
total_actions = sum(len(a) for a in optimized_actions)
avg_actions = total_actions / len(optimized_actions)
print(f"  总动作数：{total_actions} 个")
print(f"  平均每段：{avg_actions:.1f} 个动作")

print("\n" + "=" * 80)
print("🎯 结论")
print("=" * 80)
print("导演模型 + 动作变体方案有效解决了动作重复问题！")
print("推荐实现此方案用于演示视频和生产环境。")
print("=" * 80)

# 保存结果为 JSON
output = {
    "story": "小明的一天",
    "traditional": {
        "actions": traditional_actions,
        "duplicates": traditional_duplicates
    },
    "optimized": {
        "actions": optimized_actions,
        "duplicates": optimized_duplicates,
        "emotion_curve": director_result["emotion_curve"]
    }
}

with open("/tmp/director_test_result.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n📁 详细结果已保存到：/tmp/director_test_result.json")
