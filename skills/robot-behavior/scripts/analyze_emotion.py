#!/usr/bin/env python3
"""
Robot Behavior - 情绪故事编导脚本
两阶段流程：
1) 故事分段（按情节节点）
2) 逐段生成动作（携带 last_action 上下文）
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


def load_dotenv_simple():
    """不依赖 python-dotenv，手动读取 .env 文件"""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:  # 不覆盖已有环境变量
                os.environ[key] = value


# 在文件最顶部调用，其他任何逻辑之前
load_dotenv_simple()

MODEL_NAME = "qwen3.5-omni-plus-realtime"
API_URL = f"wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model={MODEL_NAME}"
ALLOWED_ACTIONS = set(range(0, 11))

ACTION_MAP = {
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
    10: "后退 2 步",
}

SEGMENT_SYSTEM_PROMPT = """你是一个故事情节分析师。
把输入的故事按情节节点分段，每段代表一个独立的动作/情绪事件。

规则：
- 按情节转折点切割，不按句子切割
- 每段 1-3 句话
- 输出纯 JSON 数组，每个元素是字符串
- 不要解释
- 如果无法有效分段，返回只包含原文的单元素数组
"""

ACTION_SYSTEM_PROMPT = """你是一个机器人动作编导。
把情节片段转化为机器人动作序列编号数组。

可用动作：
1=挥手（向外挥动手臂，打招呼/表达开心）
  适用：相遇、问候、轻度喜悦
2=摇头（缓慢左右摇头，也很像左右观察环境）
  适用：拒绝、失望、不认同、环境观察
3=一边致谢（向左侧鞠躬致谢）
  适用：感谢、被表扬、谦逊回应
4=另一边致谢（向右侧鞠躬致谢）
  适用：感谢、被表扬，与3配合使用效果更好
5=交通指挥（标准交警指挥手势）
  适用：引导、指示方向、特殊演绎场景
6=舞蹈歌曲（完整舞蹈，持续约60秒）
  适用：仅限故事结尾，整体情绪为强烈正面时
  不适用：中间段、写实叙事、严肃场景
7=自由飞翔（单脚站立双臂展开扇动，持续约20秒）
  适用：轻松愉快、梦境幻想、无忧无虑的情节
  不适用：写实叙事、严肃场景、悲伤情节
8=下蹲（身体缓慢下蹲，双臂向下左右匀速扫摆）
  适用：害怕、躲藏、低落、受到打击、搜索/寻找、谨慎观察
9=前进2步（向前走两步）
  适用：主动接近、进入场景、积极行动
10=后退2步（向后退两步）
  适用：害怕后退、被动回避、惊吓反应
（0=站立，只能作为整个故事最后一段的结尾）

编排原则：
- 动作顺序符合物理直觉和叙事逻辑
- 强动作（6/7）放在段落高潮位置，不放开头
- 避免语义相反的动作相邻（如 9 紧接 10）
- 每段长度 2-4 个动作
- 中间段不加 0，最后一段结尾必须加 0
- 动作使用约束：
  - 动作6（舞蹈，60秒）：仅允许出现在最后一段，且整体情绪为强烈正面（happy）时才可使用，其余情况禁止
  - 动作7（自由飞翔，20秒）：仅适合梦境、幻想、极度轻松的情节片段，写实叙事情景禁止使用
  - 动作6和动作7不能同时出现在同一段
- 输出纯 JSON 整数数组，不要解释
"""

EMOTION_SYSTEM_PROMPT = """你是情绪分类器。
从文本中识别主情绪，只输出 JSON：
{"emotion":"happy|sad|nervous|scared|angry|grateful|calm|surprised"}
"""

EMOTION_FALLBACK_ORDER = [
    ("grateful", ["谢谢", "感谢", "感恩"]),
    ("scared", ["害怕", "恐惧"]),
    ("nervous", ["紧张", "焦虑", "不安"]),
    ("sad", ["难过", "伤心", "失落", "沮丧"]),
    ("angry", ["生气", "愤怒", "烦"]),
    ("surprised", ["惊讶", "震惊", "哇"]),
    ("happy", ["开心", "高兴", "快乐", "兴奋"]),
]


def debug_safe_repr(value):
    if isinstance(value, str):
        return value.encode("unicode_escape").decode("ascii")
    return repr(value)


def deduplicate_consecutive(seq):
    if not seq:
        return seq
    result = []
    for action in seq:
        if not result or action != result[-1]:
            result.append(action)
    return result


def normalize_action_sequence(sequence):
    if not isinstance(sequence, list):
        return [0]

    out = []
    for item in sequence:
        if isinstance(item, bool):
            continue
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value in ALLOWED_ACTIONS:
            out.append(value)

    if not out:
        return [0]
    if out[-1] != 0:
        out.append(0)
    out = deduplicate_consecutive(out)
    return out


def parse_json_maybe(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None


def emotion_by_rule(text):
    source = (text or "").strip()
    for label, words in EMOTION_FALLBACK_ORDER:
        if any(word in source for word in words):
            return label
    return "calm"


def call_dashscope_json(system_prompt, user_prompt, api_key, timeout=15):
    ws = None
    try:
        try:
            import websocket
        except ImportError:
            return {
                "ok": False,
                "error": {
                    "status": "error",
                    "error_code": "MISSING_DEPENDENCY",
                    "error_message": "缺少 websocket-client 库，请运行：pip install websocket-client --user",
                },
            }

        headers = [f"Authorization: Bearer {api_key}"]
        ws = websocket.create_connection(API_URL, header=headers, timeout=10)
        print("[DEBUG] dashscope invoke mode: websocket realtime API (session.update + conversation.item.create + response.create), not messages/prompt REST SDK", file=sys.stderr)
        print("[DEBUG] content type before send:", type(user_prompt), file=sys.stderr)
        print("[DEBUG] content repr before send:", debug_safe_repr(user_prompt), file=sys.stderr)

        ws.send(
            json.dumps(
                {
                    "event_id": f"event_{uuid.uuid4().hex[:16]}",
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "instructions": system_prompt,
                        "turn_detection": None,
                    },
                }
            )
        )
        time.sleep(0.3)

        ws.send(
            json.dumps(
                {
                    "event_id": f"event_{uuid.uuid4().hex[:16]}",
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_prompt}],
                    },
                }
            )
        )
        time.sleep(0.2)

        ws.send(
            json.dumps(
                {
                    "event_id": f"event_{uuid.uuid4().hex[:16]}",
                    "type": "response.create",
                    "response": {"modalities": ["text"]},
                }
            )
        )

        ws.settimeout(timeout)
        full_text = ""
        for _ in range(60):
            data = json.loads(ws.recv())
            msg_type = data.get("type", "")
            if msg_type == "response.text.delta":
                full_text += data.get("delta", "")
            elif msg_type == "response.text.done":
                full_text = data.get("text", full_text)
                break
            elif msg_type == "error":
                return {
                    "ok": False,
                    "error": {
                        "status": "error",
                        "error_code": "API_ERROR",
                        "error_message": data.get("error", {}).get("message", "未知错误"),
                    },
                }
            elif "done" in msg_type:
                break

        print("[DEBUG] raw response:", debug_safe_repr(full_text), file=sys.stderr)

        parsed = parse_json_maybe(full_text)
        if parsed is None:
            return {
                "ok": False,
                "error": {
                    "status": "error",
                    "error_code": "PARSE_ERROR",
                    "error_message": f"无法解析模型响应: {full_text[:200]}",
                },
            }
        return {"ok": True, "data": parsed}
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "status": "error",
                "error_code": "NETWORK_ERROR",
                "error_message": str(exc),
            },
        }
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass


def segment_story(text, provider, api_key, timeout):
    if provider == "mock":
        chunks = [s.strip() for s in re.split(r"[。！？!?]", text) if s.strip()]
        if not chunks:
            return [text]
        return chunks

    prompt = f"故事文本：{text}\n请返回 JSON 数组。"
    print("[DEBUG] segment_story prompt:", debug_safe_repr(prompt), file=sys.stderr)
    result = call_dashscope_json(
        SEGMENT_SYSTEM_PROMPT,
        prompt,
        api_key,
        timeout,
    )
    if not result.get("ok"):
        print("[DEBUG] segment_story error:", debug_safe_repr(json.dumps(result.get("error", {}), ensure_ascii=False)), file=sys.stderr)
        return [text]
    data = result.get("data")
    if not isinstance(data, list):
        return [text]
    segments = [str(item).strip() for item in data if str(item).strip()]
    return segments if segments else [text]


def generate_actions(segment, last_action, is_last, is_multi_segment, provider, api_key, timeout):
    if provider == "mock":
        emotion = emotion_by_rule(segment)
        mapping = {
            "happy": [9, 1, 6],
            "sad": [2, 8],
            "nervous": [8, 10],
            "scared": [8, 10],
            "angry": [2, 5],
            "grateful": [3, 4],
            "calm": [1, 9],
            "surprised": [10, 1],
        }
        seq = mapping.get(emotion, [1, 9])[:]
        if last_action is not None and seq and abs(seq[0] - last_action) > 8:
            seq = [1] + seq
        if is_last:
            seq.append(0)
        return seq

    context_line = ""
    if last_action is not None:
        context_line = f"\n上一段最后一个动作是 {last_action}，避免与当前段第一个动作跳跃过大。"

    last_rule = "最后一段，结尾必须加 0。" if is_last else "中间段，不要输出 0。"
    user_prompt = (
        f"情节片段：{segment}\n"
        f"{last_rule}"
        f"{context_line}\n"
        "仅输出 JSON 整数数组。"
    )
    if is_multi_segment:
        user_prompt += "\n若序列包含动作6，6之前必须至少有1个非0动作（优先1或9），禁止直接 [6, 0]。"
    print("[DEBUG] generate_actions prompt:", debug_safe_repr(user_prompt), file=sys.stderr)
    result = call_dashscope_json(ACTION_SYSTEM_PROMPT, user_prompt, api_key, timeout)
    if not result.get("ok"):
        print("[DEBUG] generate_actions error:", debug_safe_repr(json.dumps(result.get("error", {}), ensure_ascii=False)), file=sys.stderr)
        return [0]
    data = result.get("data")
    if not isinstance(data, list):
        return [0]
    seq = []
    for item in data:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value in ALLOWED_ACTIONS:
            seq.append(value)
    if not seq:
        return [0]
    if not is_last:
        seq = [x for x in seq if x != 0]
        if not seq:
            return [0]
    else:
        if seq[-1] != 0:
            seq.append(0)
    return seq


def detect_emotion(segment, provider, api_key, timeout):
    if provider == "mock":
        return emotion_by_rule(segment)

    prompt = f"文本：{segment}\n仅输出 JSON。"
    print("[DEBUG] detect_emotion prompt:", debug_safe_repr(prompt), file=sys.stderr)
    result = call_dashscope_json(
        EMOTION_SYSTEM_PROMPT,
        prompt,
        api_key,
        timeout,
    )
    if not result.get("ok"):
        print("[DEBUG] detect_emotion error:", debug_safe_repr(json.dumps(result.get("error", {}), ensure_ascii=False)), file=sys.stderr)
        return emotion_by_rule(segment)
    data = result.get("data")
    if isinstance(data, dict):
        emotion = str(data.get("emotion", "")).strip().lower()
        if emotion in {
            "happy",
            "sad",
            "nervous",
            "scared",
            "angry",
            "grateful",
            "calm",
            "surprised",
        }:
            return emotion
    return emotion_by_rule(segment)


def merge_sequences(sequences):
    merged = []
    for idx, seq in enumerate(sequences):
        if not isinstance(seq, list):
            seq = [0]
        if idx < len(sequences) - 1:
            merged.extend([x for x in seq if x != 0])
        else:
            merged.extend(seq)
    if not merged or merged[-1] != 0:
        merged.append(0)
    return merged


def build_story_actions(text, provider, api_key, timeout):
    segments = segment_story(text, provider, api_key, timeout)
    if not segments:
        segments = [text]
    is_multi_segment = len(segments) > 1

    raw_sequences = []
    segment_debug = []
    segment_emotions = []
    last_action = None

    for idx, segment in enumerate(segments):
        is_last = idx == len(segments) - 1
        seq = generate_actions(
            segment,
            last_action,
            is_last,
            is_multi_segment,
            provider,
            api_key,
            timeout,
        )
        raw_sequences.append(seq)

        non_zero = [x for x in seq if x != 0]
        if non_zero:
            last_action = non_zero[-1]

        segment_debug.append({"text": segment, "actions": [int(x) for x in seq if isinstance(x, int)]})
        segment_emotions.append(detect_emotion(segment, provider, api_key, timeout))

    merged = normalize_action_sequence(merge_sequences(raw_sequences))

    if len(segments) == 1:
        emotion_detected = segment_emotions[0] if segment_emotions else "calm"
    else:
        uniq = {e for e in segment_emotions if e}
        emotion_detected = segment_emotions[0] if len(uniq) == 1 and segment_emotions else "mixed"

    rationale = f"分{len(segments)}段处理：" + "→".join([s.get("text", "")[:12] for s in segment_debug])

    return {
        "status": "success",
        "action_sequence": merged,
        "action_names": [ACTION_MAP.get(a, "未知") for a in merged],
        "emotion_detected": emotion_detected,
        "rationale": rationale,
        "segments": segment_debug,
    }


def main():
    parser = argparse.ArgumentParser(description="故事分段 + 动作编导")
    parser.add_argument("--input", "-i", required=False, help="输入文本")
    parser.add_argument("--input-file", required=False, help="输入 JSON 文件路径，格式: {\"content\":\"...\"}")
    parser.add_argument("--api-key", "-k", default=None, help="DashScope API Key")
    parser.add_argument("--provider", default=None, choices=["dashscope", "mock"], help="分析提供方")
    parser.add_argument("--timeout", "-t", type=int, default=15, help="超时秒数")
    parser.add_argument("--pretty", action="store_true", help="美化输出")
    args = parser.parse_args()

    provider = (
        args.provider
        or os.environ.get("EMOTION_PROVIDER")
        or os.environ.get("ROBOT_BEHAVIOR_PROVIDER")
        or "dashscope"
    )
    api_key = args.api_key or os.environ.get("DASHSCOPE_API_KEY", "")

    input_text = args.input
    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        input_text = payload.get("content", "")

    if input_text is None:
        input_text = ""

    if provider == "dashscope" and not api_key:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error_code": "MISSING_API_KEY",
                    "error_message": "缺少 API Key",
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    # 代理配置（例如本地 VPN）
    if provider == "dashscope":
        https_proxy = os.getenv("HTTPS_PROXY")
        http_proxy = os.getenv("HTTP_PROXY")
        if https_proxy:
            os.environ["HTTPS_PROXY"] = https_proxy
        if http_proxy:
            os.environ["HTTP_PROXY"] = http_proxy

    try:
        result = build_story_actions(input_text, provider, api_key, args.timeout)
        result["timestamp"] = datetime.now().isoformat()
        result["model"] = MODEL_NAME if provider == "dashscope" else "mock-rule-based-v2"
        result["provider"] = provider
        print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
        sys.exit(0)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error_code": "UNEXPECTED_ERROR",
                    "error_message": str(exc),
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
