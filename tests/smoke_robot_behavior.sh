#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_SCRIPT="$ROOT_DIR/services/webhook-receiver/server.py"
ANALYZE_SCRIPT="$ROOT_DIR/skills/robot-behavior/scripts/analyze_emotion.py"

passed=0
total=6

run_case() {
  local id="$1"
  local name="$2"
  shift 2
  echo
  echo "[$id] $name"
  set +e
  "$@"
  local rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    echo "PASS"
    passed=$((passed + 1))
  else
    echo "FAIL"
  fi
}

post_json() {
  local url="$1"
  local body="$2"
  curl -sS -X POST "$url" -H "Content-Type: application/json" -d "$body"
}

json_eval() {
  local code="$1"
  python3 -c "$code"
}

export EMOTION_PROVIDER="mock"
python3 "$SERVER_SCRIPT" >/tmp/smoke_robot_behavior.log 2>&1 &
server_pid=$!
trap 'kill $server_pid >/dev/null 2>&1 || true' EXIT
sleep 1

curl -sS "http://127.0.0.1:8765/health" >/dev/null

case1() {
  local raw
  raw="$(post_json "http://127.0.0.1:8765/emotion" '{"content":"我很开心"}')"
  RAW="$raw" json_eval '
import json, os, sys
r=json.loads(os.environ["RAW"])
need=["status","emotion","action_sequence","command_id","client_id"]
for k in need:
    assert k in r, f"missing {k}: {r}"
assert isinstance(r["action_sequence"], list) and len(r["action_sequence"])>0, r
assert r["action_sequence"][-1]==0, r
' || { echo "actual: $raw"; return 1; }
}

case2() {
  local raw
  raw="$(post_json "http://127.0.0.1:8765/emotion" '{"content":""}')"
  RAW="$raw" json_eval '
import json, os
r=json.loads(os.environ["RAW"])
assert r.get("status") != "error", r
assert r.get("action_sequence") == [0], r
' || { echo "actual: $raw"; return 1; }
}

case3() {
  local raw
  raw="$(post_json "http://127.0.0.1:8765/emotion" '{"content":"小明走进教室，老师表扬了他，他激动地跑去告诉朋友"}')"
  RAW="$raw" json_eval '
import json, os
r=json.loads(os.environ["RAW"])
seq=r["action_sequence"]
assert len(seq) > 2, r
for i in range(len(seq)-1):
    assert not (seq[i]==0 and seq[i+1]==0), r
' || { echo "actual: $raw"; return 1; }

  local raw_an
  raw_an="$(python3 "$ANALYZE_SCRIPT" --provider mock --input "小明走进教室，老师表扬了他，他激动地跑去告诉朋友")"
  RAW="$raw_an" json_eval '
import json, os
r=json.loads(os.environ["RAW"])
assert "segments" in r, r
assert len(r["segments"]) >= 2, r
' || { echo "actual analyze_emotion: $raw_an"; return 1; }
}

case4() {
  local raw
  raw="$(post_json "http://127.0.0.1:8765/emotion" '{"content":"她满怀期待地打开信封，却发现自己落榜了，默默离开了考场"}')"
  RAW="$raw" json_eval '
import json, os
r=json.loads(os.environ["RAW"])
seq=r["action_sequence"]
assert len(seq) > 0, r
assert seq[-1] == 0, r
for i in range(len(seq)-1):
    assert seq[i] != 0, r
' || { echo "actual: $raw"; return 1; }
}

case5() {
  local raw
  raw="$(post_json "http://127.0.0.1:8765/emotion" '{"content":"我很开心"}')"
  RAW="$raw" json_eval '
import json, os
r=json.loads(os.environ["RAW"])
expected={"status","emotion","action_sequence","command_id","client_id"}
actual=set(r.keys())
assert actual == expected, {"actual":sorted(actual), "raw":r}
assert "segments" not in r, r
' || { echo "actual: $raw"; return 1; }
}

case6() {
  local create poll1 cmd ack poll2
  create="$(post_json "http://127.0.0.1:8765/emotion" '{"content":"我很开心"}')"
  poll1="$(curl -sS "http://127.0.0.1:8765/poll/milk_duos_001")"
  cmd="$(RAW="$poll1" json_eval 'import json, os; print(json.loads(os.environ["RAW"]).get("command_id",""))')"
  [[ -n "$cmd" ]] || { echo "actual poll1: $poll1"; return 1; }
  ack="$(post_json "http://127.0.0.1:8765/ack/milk_duos_001" "{\"command_id\":\"$cmd\"}")"
  poll2="$(curl -sS "http://127.0.0.1:8765/poll/milk_duos_001")"
  RAW="$ack" RAW2="$poll2" json_eval '
import json, os
ack=json.loads(os.environ["RAW"])
poll2=json.loads(os.environ["RAW2"])
assert ack.get("status")=="success", ack
assert poll2.get("status")=="no_action", poll2
' || { echo "actual ack: $ack"; echo "actual poll2: $poll2"; return 1; }
}

run_case "1" "单段输入-简单情绪" case1
run_case "2" "单段输入-边界空内容" case2
run_case "3" "多段输入-情节有转折" case3
run_case "4" "多段输入-情绪反转" case4
run_case "5" "/emotion 响应字段校验" case5
run_case "6" "/poll + /ack 全链路" case6

echo
echo "Summary: $passed/$total passed"
