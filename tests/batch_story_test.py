#!/usr/bin/env python3
"""
Batch Story Test - Python 版本
测试 robot-behavior 的 analyze_emotion.py 脚本
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 测试用例
CASES = [
    {"id": "A", "name": "Case A", "group": "Short", "story": "小明在森林里找丢失的小狗，他小心翼翼地往前走，突然听到草丛里有声音，他蹲下来拨开草丛，发现了小狗蜘蛛在里面。", "expected": [9, 8, 1, 0], "emotion": "calm"},
    {"id": "B", "name": "Case B", "group": "Short", "story": "小红走在放学路上，突然一辆自行车冲过来，她赶紧向后退了几步，蹲下身子转开，等车过去后才站起来继续走。", "expected": [10, 8, 0], "emotion": "scared"},
    {"id": "C", "name": "Case C", "group": "Short", "story": "勇者踏上旅途，迈步走向远方的城堡。途中遇到路障，他蹲身钻了过去，到达城堡门口时激动地向里面的人挥手示意。", "expected": [9, 8, 9, 1, 0], "emotion": "happy"},
    {"id": "D", "name": "Case D", "group": "Short", "story": "足球比赛最后一分钟，小华带球向前冲，对方防守队员逼近，他假装后退引开对手，再猛地向前突破射门，球进了他兴奋地挥手庆祝。", "expected": [9, 10, 9, 1, 0], "emotion": "happy"},
    {"id": "E", "name": "Case E", "group": "Short", "story": "小李第一次独自去超市，他推着购物车往前走。到了货架前发现想要的东西放在最低层，他蹲下来仔细挑选。结账时发现钱不够，他就尴尬地向后退了一步重新数钱。最后买到了东西，开心地向收银员挥手告别走出超市。", "expected": [9, 8, 10, 3, 9, 1, 0], "emotion": "happy"},
    {"id": "L1", "name": "Long Case 1", "group": "Long", "story": "小明看着藏宝图，深吸一口气迈步走进了密林。树枝越来越密，他只能弯腿蹲身钻过低矮的灰草丛。走着走着前方出现了一条小河，他小心翼翼地后退几步寻找浅滩。找到渡口后他再次向前趟水过河。对岸的大石头后面就是藏宝地点，他蹲下来用手拨开落叶，终于看到了埋在地下的宝箱。他激动地站起来挥手大喊，声音在山谷里回响。", "expected": [9, 8, 10, 9, 8, 1, 0], "emotion": "happy"},
    {"id": "L2", "name": "Long Case 2", "group": "Long", "story": "消防员小张接到报警立刻出发，快步冲向起火的建筑。门口浓烟弥漫，他弯腿蹲低绕过烟雾最浓的地方。里面能见度很低，他放慢脚步小心向前摸索。突然听到里面有人呼救，他循声加速前进。找到被困的老人后，他俯身蹲下把老人扶起来，两人一起弯腿向出口移动。冲出大门的那一刻，他直起身子回头挥手示意里面已经没有人了。", "expected": [9, 8, 9, 9, 8, 9, 1, 0], "emotion": "scared"},
    {"id": "L3", "name": "Long Case 3", "group": "Long", "story": "运动会开始了，小花站在起跑线上整装待发。发令枪响她快步向前冲出。跑到障碍区她迅速蹲下钻过横杆。站起来继续跑向下一个关卡。前方是一面矮墙，她弯腿蹲身从墙下爬过去。爬过去后站起来向终点全力冲刺。跑过终点线的那一刻她高高举起双手挥舞，转身向同学们挥手庆祝。", "expected": [9, 8, 9, 8, 9, 1, 0], "emotion": "happy"},
]

def format_sequence(seq):
    if not seq:
        return "[]"
    return "[" + ", ".join(str(s) for s in seq) + "]"

def sequence_duration_seconds(seq):
    total = 0
    for a in seq:
        if a == 6:
            total += 60
        elif a == 7:
            total += 20
        else:
            total += 8
    return total

def escape_md(text):
    if not text:
        return ""
    return text.replace('|', '\\|').replace('\r\n', '<br>').replace('\n', '<br>')

def main():
    # 支持命令行参数选择 provider
    provider = sys.argv[1] if len(sys.argv) > 1 else "mock"
    print(f"Using provider: {provider}")
    
    root = Path("/home/admin/.openclaw/workspace")
    analyze_script = root / "skills" / "robot-behavior" / "scripts" / "analyze_emotion.py"
    output_dir = Path("/home/admin/.openclaw/workspace/tests")
    
    # 根据 provider 区分输出文件
    suffix = f"_{provider}" if provider != "mock" else ""
    report_file = output_dir / f"batch_story_report{suffix}.md"
    coverage_file = output_dir / f"action_coverage_report{suffix}.md"
    summary_json_file = output_dir / f"batch_story_report{suffix}.json"
    
    # 加载环境变量中的 API KEY
    env_file = root / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if "DASHSCOPE_API_KEY" in line and not line.strip().startswith("#"):
                    _, _, value = line.partition("=")
                    os.environ["DASHSCOPE_API_KEY"] = value.strip().strip('"')
                    break
    
    if not analyze_script.exists():
        print(f"ERROR: analyze_emotion.py not found: {analyze_script}")
        sys.exit(1)

    results = []
    coverage = {str(i): 0 for i in range(11)}

    for i, case in enumerate(CASES):
        print(f"[{i+1}/{len(CASES)}] Testing Case {case['id']}...")
        input_file = output_dir / f"tmp_{case['id']}.json"
        payload = {"content": case["story"]}
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

        try:
            result = subprocess.run(
                ["python3", str(analyze_script), "--input-file", str(input_file), "--provider", provider],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=90
            )
            if result.returncode != 0:
                print(f"  ERROR: analyze_emotion failed for case {case['id']}")
                print(f"  stderr: {result.stderr[:200]}")
                continue

            json_output = json.loads(result.stdout)
            seq = json_output.get("action_sequence", [])
            
            for a in seq:
                if str(a) in coverage:
                    coverage[str(a)] += 1

            duration = sequence_duration_seconds(seq)
            warning = duration > 40

            results.append({
                "id": case["id"],
                "name": case["name"],
                "group": case["group"],
                "story": case["story"],
                "expected": format_sequence(case["expected"]),
                "actual": format_sequence(seq),
                "segments": len(json_output.get("segments", [])),
                "actions": len(seq),
                "duration": duration,
                "warning": warning,
                "emotion": json_output.get("emotion_detected", ""),
                "emotion_arc": json_output.get("emotion_arc", ""),
                "segments_data": json_output.get("segments", []),
                "expected_emotion": case["emotion"],
            })
            arc_info = json_output.get("emotion_arc", "")
            if arc_info:
                print(f"  -> emotion={json_output.get('emotion_detected')}, arc={arc_info}, actions={len(seq)}, duration={duration}s")
            else:
                print(f"  -> emotion={json_output.get('emotion_detected')}, actions={len(seq)}, duration={duration}s")
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT: Case {case['id']}")
        except Exception as e:
            print(f"  ERROR processing case {case['id']}: {e}")
        finally:
            if input_file.exists():
                input_file.unlink()

    never_triggered = [i for i in range(11) if coverage[str(i)] == 0]

    # 生成报告
    report = []
    report.append("# Batch Story Test Report")
    report.append("")
    report.append(f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- Provider: {provider}")
    report.append(f"- Cases: {len(CASES)}")
    report.append("- Warning threshold: 40s")
    report.append("")
    report.append("| Case | Group | Segments | Actions | Duration(s) | Emotion | Emotion Arc | Warning | Expected | Actual |")
    report.append("| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |")
    for r in results:
        warn = "<span style='color:red'>超时</span>" if r["warning"] else "OK"
        arc = escape_md(r.get("emotion_arc", ""))
        report.append(f"| {r['id']} | {r['group']} | {r['segments']} | {r['actions']} | {r['duration']} | {escape_md(r['emotion'])} | {arc} | {warn} | {escape_md(r['expected'])} | {escape_md(r['actual'])} |")
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    # 生成覆盖率报告
    coverage_report = []
    coverage_report.append("# Action Coverage Report")
    coverage_report.append("")
    coverage_report.append("| Action | Count |")
    coverage_report.append("| --- | ---: |")
    for i in range(11):
        coverage_report.append(f"| {i} | {coverage[str(i)]} |")
    coverage_report.append("")
    never_str = ", ".join(str(x) for x in never_triggered) if never_triggered else "none"
    coverage_report.append(f"Never triggered actions: {never_str}")
    
    with open(coverage_file, "w", encoding="utf-8") as f:
        f.write("\n".join(coverage_report))

    # 生成 JSON 摘要
    summary = {
        "generated_at": datetime.now().isoformat(),
        "provider": provider,
        "cases": results,
        "coverage": coverage,
        "never_triggered": never_triggered,
    }
    with open(summary_json_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to: {report_file}")
    print(f"Coverage saved to: {coverage_file}")
    print(f"JSON saved to: {summary_json_file}")
    print(f"Never triggered actions: {', '.join(str(x) for x in never_triggered)}")

if __name__ == "__main__":
    main()
