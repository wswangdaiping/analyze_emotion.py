#!/usr/bin/env python3
"""
OpenClaw Webhook Receiver
接收 WebApp 情绪数据和 DuoS 轮询请求

端点：
- POST /emotion - 接收 WebApp 情绪数据
- GET  /poll/{client_id} - DuoS 轮询动作指令
- POST /action/{client_id} - 直接发送动作指令
- GET  /health - 健康检查
"""

import json
import logging
import os
import sys
import subprocess
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import threading
import uuid

# ========== 配置 ==========
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = Path(__file__).resolve().parent / "logs"
PORT = int(os.environ.get("WEBHOOK_PORT", 8765))
LOG_DIR = Path(os.environ.get("LOG_DIR", str(DEFAULT_LOG_DIR)))
ACTION_QUEUE_DIR = Path(
    os.environ.get("ACTION_QUEUE_DIR", str(REPO_ROOT / ".runtime" / "action-queue"))
)
EMOTION_SCRIPT_PATH = Path(
    os.environ.get(
        "EMOTION_SCRIPT_PATH",
        str(REPO_ROOT / "skills" / "robot-behavior" / "scripts" / "analyze_emotion.py"),
    )
)
API_AUTH_ENABLED = os.environ.get("ENABLE_API_KEY_AUTH", "false").lower() in ("1", "true", "yes")
API_AUTH_KEY = os.environ.get("API_AUTH_KEY", "")

# 确保目录存在
LOG_DIR.mkdir(parents=True, exist_ok=True)
ACTION_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "webhook.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def normalize_action_sequence(sequence) -> list:
    """标准化动作序列：整数数组，且必须以 0 结尾。"""
    if not isinstance(sequence, list):
        return [0]

    normalized = []
    for item in sequence:
        if isinstance(item, bool):
            continue
        try:
            normalized.append(int(item))
        except (TypeError, ValueError):
            continue

    if not normalized:
        return [0]

    if normalized[-1] != 0:
        normalized.append(0)

    return normalized


def decode_subprocess_output(data: bytes) -> str:
    """跨平台解码子进程输出，优先 UTF-8，失败回退 GBK。"""
    if not data:
        return ""
    for encoding in ("utf-8", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")

# ========== 动作队列管理 ==========
class ActionQueue:
    """动作指令队列（每个客户端独立）"""
    
    # 配置
    CLEANUP_INTERVAL_HOURS = 3  # 清理间隔（小时）
    MAX_AGE_HOURS = 3           # 命令最大保留时间（小时）
    KEEP_LATEST_ONLY = True     # 只保留最新输入的动作（新输入时清除未 ACK 的旧命令）
    
    def __init__(self):
        self.queues = {}
        self.lock = threading.Lock()
        self._start_cleanup_timer()
    
    def clear_pending(self, client_id: str) -> int:
        """清除指定客户端所有未 ACK 的命令
        
        Returns:
            int: 清理的命令数量
        """
        with self.lock:
            if client_id not in self.queues:
                return 0
            
            old_count = len(self.queues[client_id])
            # 只保留已完成的命令
            self.queues[client_id] = [
                item for item in self.queues[client_id]
                if item.get("status") == "completed"
            ]
            
            removed = old_count - len(self.queues[client_id])
            if removed > 0:
                logger.info(f"清除客户端 {client_id} 的 {removed} 条未 ACK 命令")
            
            return removed
    
    def add_action(self, client_id: str, action_sequence: list, emotion: str = None, 
                   clear_old: bool = False) -> str:
        """添加动作指令到队列
        
        Args:
            client_id: 客户端 ID
            action_sequence: 动作序列
            emotion: 情绪类型
            clear_old: 是否在添加前清除未 ACK 的旧命令（默认 False）
        """
        command_id = f"cmd_{uuid.uuid4().hex[:16]}"
        
        with self.lock:
            # 如果需要清除旧命令，先清理
            if clear_old and client_id in self.queues:
                old_count = len(self.queues[client_id])
                self.queues[client_id] = [
                    item for item in self.queues[client_id]
                    if item.get("status") == "completed"
                ]
                removed = old_count - len(self.queues[client_id])
                if removed > 0:
                    logger.info(f"【最新优先】清除客户端 {client_id} 的 {removed} 条未 ACK 旧命令")
            
            if client_id not in self.queues:
                self.queues[client_id] = []
            
            self.queues[client_id].append({
                "command_id": command_id,
                "action_sequence": action_sequence,
                "emotion": emotion,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending"
            })
        
        logger.info(f"添加动作指令到 {client_id}: {action_sequence}")
        return command_id
    
    def poll_action(self, client_id: str) -> dict:
        """轮询待发送的动作指令"""
        with self.lock:
            if client_id not in self.queues:
                return None
            
            queue = self.queues[client_id]
            if not queue:
                return None
            
            # 返回最早的待处理指令，并标记为 processing
            for item in queue:
                if item["status"] == "pending":
                    item["status"] = "processing"  # 标记为处理中
                    return item
        
        return None
    
    def acknowledge_action(self, client_id: str, command_id: str) -> bool:
        """确认动作已执行"""
        with self.lock:
            if client_id not in self.queues:
                return False
            
            for item in self.queues[client_id]:
                if item["command_id"] == command_id:
                    item["status"] = "completed"
                    item["completed_at"] = datetime.now(timezone.utc).isoformat()
                    logger.info(f"动作已确认：{command_id}")
                    return True
        
        return False
    
    def cleanup_old(self, client_id: str = None, max_age_hours: int = None):
        """清理旧的动作指令
        
        Args:
            client_id: 指定客户端，None 表示清理所有客户端
            max_age_hours: 最大保留时间（小时），默认使用配置值
        """
        if max_age_hours is None:
            max_age_hours = self.MAX_AGE_HOURS
        
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        cutoff_str = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        
        with self.lock:
            if client_id:
                # 清理指定客户端
                if client_id in self.queues:
                    old_count = len(self.queues[client_id])
                    self.queues[client_id] = [
                        item for item in self.queues[client_id]
                        if item["created_at"] > cutoff_str
                    ]
                    removed = old_count - len(self.queues[client_id])
                    if removed > 0:
                        logger.info(f"清理客户端 {client_id} 的 {removed} 条旧命令")
            else:
                # 清理所有客户端
                total_removed = 0
                for cid in list(self.queues.keys()):
                    old_count = len(self.queues[cid])
                    self.queues[cid] = [
                        item for item in self.queues[cid]
                        if item["created_at"] > cutoff_str
                    ]
                    removed = old_count - len(self.queues[cid])
                    total_removed += removed
                
                if total_removed > 0:
                    logger.info(f"定期清理完成：共清理 {total_removed} 条旧命令（保留{max_age_hours}小时内）")
    
    def _cleanup_all(self):
        """清理所有过期命令（供定时器调用）"""
        try:
            self.cleanup_old()
        except Exception as e:
            logger.error(f"清理命令失败：{e}")
        finally:
            self._start_cleanup_timer()
    
    def _start_cleanup_timer(self):
        """启动定时清理任务"""
        timer = threading.Timer(
            self.CLEANUP_INTERVAL_HOURS * 3600,
            self._cleanup_all
        )
        timer.daemon = True
        timer.start()
        logger.info(f"已启动定期清理任务：每{self.CLEANUP_INTERVAL_HOURS}小时清理一次（保留{self.MAX_AGE_HOURS}小时内命令）")

# 全局动作队列
action_queue = ActionQueue()

# ========== HTTP 请求处理 ==========
class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.client_address} - {format % args}")
    
    def send_json_response(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def require_api_key(self) -> bool:
        """可选 API Key 校验。只在开启认证时生效。"""
        if not API_AUTH_ENABLED:
            return True
        if not API_AUTH_KEY:
            logger.error("API 认证已开启，但 API_AUTH_KEY 为空")
            self.send_json_response(500, {"error": "Server auth misconfigured"})
            return False
        if self.headers.get("X-API-Key", "") != API_AUTH_KEY:
            self.send_json_response(401, {"error": "Unauthorized"})
            return False
        return True
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 健康检查
        if path == "/health":
            self.send_json_response(200, {
                "status": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "openclaw-webhook-receiver"
            })
            return
        
        # 手动清理队列：GET /cleanup
        if path == "/cleanup":
            self.handle_cleanup()
            return
        
        # 轮询动作指令：GET /poll/{client_id}
        if path.startswith("/poll/"):
            client_id = path.split("/poll/")[1].split("?")[0]
            self.handle_poll(client_id)
            return
        
        self.send_json_response(404, {"error": "Not found"})
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 接收情绪数据：POST /emotion
        # 支持 ?mode=agent 切换为 OpenClaw Agent 异步处理
        if path == "/emotion":
            self.handle_emotion(parsed.query)
            return
        
        # 直接发送动作：POST /action/{client_id}
        if path.startswith("/action/"):
            client_id = path.split("/action/")[1].split("?")[0]
            self.handle_action(client_id)
            return
        
        # 确认动作：POST /ack/{client_id}
        if path.startswith("/ack/"):
            client_id = path.split("/ack/")[1].split("?")[0]
            self.handle_ack(client_id)
            return
        
        self.send_json_response(404, {"error": "Not found"})
    
    def handle_emotion(self, query=""):
        """处理情绪数据

        Args:
            query: URL query string，支持 ?mode=agent 切换为 OpenClaw Agent 处理
        """
        try:
            if not self.require_api_key():
                return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            content = data.get("content", "")
            session_id = data.get("session_id", "default")

            # 解析 mode 参数：?mode=agent 触发 OpenClaw Agent，默认 direct
            params = parse_qs(query) if query else {}
            modes = params.get("mode", ["direct"])
            mode = modes[0] if modes else "direct"

            if not content:
                # 空内容降级（两种模式相同）
                action_sequence = [0]
                emotion = "calm"
                client_id = "milk_duos_001"
                clear_old = ActionQueue.KEEP_LATEST_ONLY
                command_id = action_queue.add_action(client_id, action_sequence, emotion, clear_old=clear_old)
                self.send_json_response(200, {
                    "status": "success",
                    "emotion": emotion,
                    "action_sequence": action_sequence,
                    "command_id": command_id,
                    "client_id": client_id
                })
                return

            logger.info(f"收到情绪数据：{content[:100]} [mode={mode}]")

            # Agent 模式：触发 OpenClaw Agent 异步处理
            if mode == "agent":
                return self._handle_emotion_agent(content, session_id)

            # 默认 direct 模式：直接调用 analyze_emotion.py
            # 调用 robot-behavior 分析情绪
            result = analyze_emotion(content)
            
            if result.get("status") != "success":
                self.send_json_response(500, {
                    "error": "Emotion analysis failed",
                    "details": result
                })
                return
            
            # 添加到动作队列
            action_sequence = normalize_action_sequence(result.get("action_sequence", []))
            emotion = result.get("emotion_detected", "unknown")
            
            # 默认发送到 milk_duos_001
            client_id = "milk_duos_001"
            
            # 新输入时清除未 ACK 的旧命令（最新优先策略）
            clear_old = ActionQueue.KEEP_LATEST_ONLY
            command_id = action_queue.add_action(client_id, action_sequence, emotion, clear_old=clear_old)
            
            logger.info(f"情绪分析完成：{emotion} → {action_sequence}")
            
            self.send_json_response(200, {
                "status": "success",
                "emotion": emotion,
                "action_sequence": action_sequence,
                "command_id": command_id,
                "client_id": client_id
            })
            
        except json.JSONDecodeError as e:
            self.send_json_response(400, {"error": f"Invalid JSON: {str(e)}"})
        except Exception as e:
            logger.error(f"处理情绪数据失败：{e}")
            self.send_json_response(500, {"error": str(e)})

    def _handle_emotion_agent(self, content, session_id):
        """Agent 模式：触发 OpenClaw Agent 异步处理情绪

        流程：
        1. 调用 openclaw sessions_spawn 触发 Agent
        2. Agent 读取 robot-behavior SKILL.md → 调用 analyze_emotion.py
        3. Agent 链式调用 json-webhook-skill → POST /action/{client_id}
        4. server.py 立即返回 processing 状态，客户端通过轮询获取结果
        """
        client_id = "milk_duos_001"
        label = f"emotion-{session_id}"
        task = (
            f"分析以下情绪文本并生成机器人动作序列：{content}"
        )

        try:
            subprocess.Popen(
                [
                    "openclaw", "sessions_spawn",
                    "--task", task,
                    "--label", label,
                    "--runtime", "subagent",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            logger.info(f"Agent 模式：已触发 OpenClaw Agent [label={label}]")

            self.send_json_response(200, {
                "status": "processing",
                "mode": "agent",
                "session_label": label,
                "client_id": client_id,
                "message": (
                    "Agent 正在分析情绪，动作将自动入队。"
                    f"请通过 GET /poll/{client_id} 获取结果。"
                ),
            })
        except FileNotFoundError:
            logger.error("Agent 模式失败：找不到 openclaw 命令")
            self.send_json_response(500, {
                "status": "error",
                "mode": "agent",
                "error_code": "AGENT_NOT_FOUND",
                "error_message": (
                    "openclaw CLI 不可用，请确认 OpenClaw 已安装并在 PATH 中。"
                    "在 ECS 上通常位于 /home/admin/.openclaw/ 目录下。"
                ),
            })
        except Exception as exc:
            logger.error(f"Agent 模式失败：{exc}")
            self.send_json_response(500, {
                "status": "error",
                "mode": "agent",
                "error_code": "AGENT_SPAWN_FAILED",
                "error_message": str(exc),
            })

    def handle_poll(self, client_id: str):
        """处理轮询请求"""
        try:
            action = action_queue.poll_action(client_id)
            
            if action:
                logger.info(f"{client_id} 轮询到动作：{action}")
                self.send_json_response(200, action)
            else:
                # 没有新动作，返回空
                self.send_json_response(200, {
                    "status": "no_action",
                    "message": "No pending actions"
                })
            
        except Exception as e:
            logger.error(f"轮询失败：{e}")
            self.send_json_response(500, {"error": str(e)})
    
    def handle_action(self, client_id: str):
        """处理直接发送动作"""
        try:
            if not self.require_api_key():
                return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            action_sequence = normalize_action_sequence(data.get("action_sequence", []))
            emotion = data.get("emotion", None)
            
            if not data.get("action_sequence"):
                self.send_json_response(400, {"error": "Missing 'action_sequence' field"})
                return
            
            command_id = action_queue.add_action(client_id, action_sequence, emotion)
            
            self.send_json_response(200, {
                "status": "success",
                "command_id": command_id
            })
            
        except json.JSONDecodeError as e:
            self.send_json_response(400, {"error": f"Invalid JSON: {str(e)}"})
        except Exception as e:
            logger.error(f"处理动作失败：{e}")
            self.send_json_response(500, {"error": str(e)})
    
    def handle_cleanup(self):
        """处理手动清理请求"""
        try:
            action_queue.cleanup_old()
            self.send_json_response(200, {
                "status": "success",
                "message": "队列清理完成",
                "cleanup_policy": {
                    "interval_hours": action_queue.CLEANUP_INTERVAL_HOURS,
                    "max_age_hours": action_queue.MAX_AGE_HOURS
                }
            })
        except Exception as e:
            logger.error(f"清理失败：{e}")
            self.send_json_response(500, {"error": str(e)})
    
    def handle_ack(self, client_id: str):
        """处理动作确认"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            command_id = data.get("command_id")
            
            if not command_id:
                self.send_json_response(400, {"error": "Missing 'command_id' field"})
                return
            
            success = action_queue.acknowledge_action(client_id, command_id)
            
            self.send_json_response(200, {
                "status": "success" if success else "not_found"
            })
            
        except json.JSONDecodeError as e:
            self.send_json_response(400, {"error": f"Invalid JSON: {str(e)}"})
        except Exception as e:
            logger.error(f"处理确认失败：{e}")
            self.send_json_response(500, {"error": str(e)})

# ========== 情绪分析 ==========
def analyze_emotion(text: str) -> dict:
    """调用 robot-behavior skill 分析情绪"""
    try:
        script_path = EMOTION_SCRIPT_PATH
        if not script_path.exists():
            return {
                "status": "error",
                "error_code": "SCRIPT_NOT_FOUND",
                "error_message": f"Emotion script not found: {script_path}"
            }
        
        # Python 3.6 兼容：使用 stdout/stderr 代替 capture_output
        result = subprocess.Popen(
            [sys.executable, str(script_path), "--input", text],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ)
        )
        
        # 等待完成（带超时）
        try:
            stdout, stderr = result.communicate(timeout=30)
        except AttributeError:
            # Python 3.6 不支持 timeout 参数
            stdout, stderr = result.communicate()
        
        stdout = decode_subprocess_output(stdout)
        stderr = decode_subprocess_output(stderr)
        
        if result.returncode == 0:
            return json.loads(stdout)
        else:
            logger.error(f"情绪分析失败：{stderr}")
            return {
                "status": "error",
                "error_code": "ANALYSIS_FAILED",
                "error_message": stderr
            }
    
    except Exception as e:
        logger.error(f"情绪分析异常：{e}")
        return {
            "status": "error",
            "error_code": "ERROR",
            "error_message": str(e)
        }

# ========== 主程序 ==========
def main():
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    logger.info(f"=" * 60)
    logger.info(f"OpenClaw Webhook Receiver 启动")
    logger.info(f"监听端口：{PORT}")
    logger.info(f"日志目录：{LOG_DIR}")
    logger.info(f"端点:")
    logger.info(f"  POST /emotion          - 接收情绪数据")
    logger.info(f"  GET  /poll/{{client_id}} - 轮询动作指令")
    logger.info(f"  POST /action/{{client_id}} - 直接发送动作")
    logger.info(f"  POST /ack/{{client_id}}  - 确认动作")
    logger.info(f"  GET  /health           - 健康检查")
    logger.info(f"=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("正在关闭服务...")
        server.shutdown()
        logger.info("服务已关闭")

if __name__ == "__main__":
    main()
