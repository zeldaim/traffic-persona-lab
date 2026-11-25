#!/usr/bin/env python3
"""v1 트래픽 재현기 — OpenAPI 명세 하나로 어떤 앱에도 포팅되는 합성 트래픽 생성기.

  python gen.py <openapi.json> --base-url http://127.0.0.1:8089 [--users 5] [--speed-scale 5] [--send]
      [--labels-out labels.jsonl]   api-defense-lab 형식 정답지도 같이 남긴다 (role=normal) — 그 레포의
                                     scorer로 채점해, 정답지·탐지기가 같은 생성기(lab_traffic.py)에서
                                     나온 순환 평가 문제를 다른 생성기로 확인할 수 있다

설계: spec_walk(상태 자동 추출) + priors(페르소나별 기본 전이확률, 아직 미검증) + timing(ClarkNet·NASA
교차검증된 로그정규 몸통, 다이얼업 시대 숫자라 speed_scale 로 보정) + auth(명세에서 회원가입·로그인
경로를 추측해 토큰을 받음, OAuth2 password 류 패턴 가정) 네 조각을 엮는다.

**범위의 정직한 한계 (v1):**
  - 전이확률은 실측이 아니라 손으로 정한 기본값이다 (priors.py 의 docstring 참고)
  - 인증은 OAuth2 password 류(경로에 'regist'·'token'/'login', username+password)만 추측한다 —
    HMAC·API 키 인증 같은 다른 방식은 토큰을 못 받고, 그건 세션마다 이유와 함께 보고한다
  - 실제 HTTP 전송(--send)은 GET 상태만 한다. 쓰기(POST/PUT/PATCH/DELETE)는 명세에 요청 본문 예시가
    없어 실제로 보내면 뭘 보내야 할지 모른다 — 시뮬레이션 로그로만 남기고 전송은 생략한다 (거짓 증명 방지)
  - --send 없이 돌리면 전송 없이 세션 로그만 찍는다 (기본값 — 안전)
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, "model")
sys.path.insert(0, "generator")
from spec_walk import states_from_spec  # noqa: E402
from priors import sample_session  # noqa: E402
from timing import sample_gap  # noqa: E402
import auth  # noqa: E402


def fill_path(path: str, params: list[dict], rng: random.Random) -> str:
    """{order_id} 같은 경로 변수를 타입에 맞는 그럴듯한 값으로 채운다. 실제로 존재하는 값은 모르니
    404 는 여전히 날 수 있지만, 최소한 '경로 형태 자체가 명세 밖'으로는 안 보인다 (실제로 겪은 문제)."""
    for p in params:
        val = rng.randint(1, 50) if p["type"] in ("integer", "number") else "sample"
        path = path.replace("{" + p["name"] + "}", str(val))
    return path


MAX_WAIT_S = 30  # 로그정규 꼬리가 두꺼워 실제 대기가 비정상적으로 길어질 수 있어 상한을 둔다 (알려진 단순화)


def write_label(path, run_id, ip, scenario, start, end):
    """api-defense-lab 의 traffic/lab_traffic.py 와 같은 정답지 형식(run·ip·role·scenario·start·end) —
    채점기(scorer)가 그대로 읽을 수 있게. role 은 항상 'normal' (이 생성기는 공격이 아니라 정상 트래픽 역할)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"run": run_id, "ip": ip, "role": "normal", "scenario": scenario,
                            "start": start.isoformat(), "end": end.isoformat()}) + "\n")


def run_session(states, persona, rng, base_url, send, speed_scale, client_ip, token, auth_note,
                labels_out, run_id, wait):
    seq = sample_session(states, persona, rng)
    by_name = {s["state"]: s for s in states}
    t0 = datetime.now(timezone.utc)
    print(f"[{persona}] 세션 시작 ({len(seq)}단계) · 인증: {auth_note}")
    for name in seq:
        st = by_name[name]
        gap = sample_gap(rng, speed_scale)  # 실제 대기(--send 일 때)는 MAX_WAIT_S 로 자름
        if send and wait:
            time.sleep(min(gap, MAX_WAIT_S))
        if st["method"] == "GET" and send:
            filled_path = fill_path(st["path"], st["path_params"], rng)
            url = base_url.rstrip("/") + filled_path
            headers = {"X-Client-IP": client_ip}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            try:
                req = urllib.request.Request(url, headers=headers)
                code = urllib.request.urlopen(req, timeout=10).status
            except urllib.error.HTTPError as e:
                code = e.code
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                code = f"오류({e})"
            print(f"  +{gap:5.1f}초  GET {filled_path} -> {code}")
        else:
            tag = "전송 안 함(쓰기 상태, v1 한계)" if st["method"] != "GET" else "전송 안 함(--send 없음)"
            print(f"  +{gap:5.1f}초  {st['method']} {st['path']}  [{tag}]")
    t1 = datetime.now(timezone.utc)
    if send and labels_out:
        write_label(labels_out, run_id, client_ip, f"persona-{persona}", t0, t1)
    print(f"[{persona}] 세션 끝\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--base-url", default="http://127.0.0.1:8089")
    ap.add_argument("--users", type=int, default=5)
    ap.add_argument("--speed-scale", type=float, default=5.0,
                    help="1995년 다이얼업 간격을 줄이는 배속 — 기본 5배 (검증 안 됨, 목적에 맞게 조정)")
    ap.add_argument("--send", action="store_true", help="GET 상태는 실제로 base-url 에 요청을 보낸다")
    ap.add_argument("--no-wait", action="store_true",
                    help="--send 여도 실제로 간격만큼 안 기다린다 (빠른 연결 확인용 — 정답지로 채점할 땐 쓰지 말 것)")
    ap.add_argument("--labels-out", help="api-defense-lab 형식 정답지(labels.jsonl)를 이 경로에 추가. role 은 항상 'normal'")
    ap.add_argument("--run-id", default=f"tpl-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                    help="정답지의 run 값 (기본: 실행 시각 기반)")
    ap.add_argument("--no-auth", action="store_true", help="로그인 시도를 끄고 익명으로만 보낸다")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding="utf-8"))
    states = states_from_spec(spec)
    print(f"명세 {a.spec} → 상태 {len(states)}개 · 대상 {a.base_url} · 전송 {'켬' if a.send else '끔'}\n")

    rng = random.Random(a.seed)
    for i in range(a.users):
        persona = "goal" if rng.random() < 0.5 else "browse"
        client_ip = f"10.90.0.{i + 2}"
        token, note = (None, "시도 안 함(--no-auth)")
        if a.send and not a.no_auth:
            token, note = auth.login(a.base_url, spec, rng, client_ip)
        run_session(states, persona, rng, a.base_url, a.send, a.speed_scale, client_ip, token, note,
                   a.labels_out, a.run_id, not a.no_wait)


if __name__ == "__main__":
    main()
