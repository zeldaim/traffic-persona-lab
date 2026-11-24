#!/usr/bin/env python3
"""v1 트래픽 재현기 — OpenAPI 명세 하나로 어떤 앱에도 포팅되는 합성 트래픽 생성기.

  python gen.py <openapi.json> --base-url http://127.0.0.1:8089 [--users 5] [--speed-scale 5] [--send]

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
import random
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "model")
sys.path.insert(0, "generator")
from spec_walk import states_from_spec  # noqa: E402
from priors import sample_session  # noqa: E402
from timing import sample_gap  # noqa: E402
import auth  # noqa: E402


def run_session(states, persona, rng, base_url, send, speed_scale, client_ip, token, auth_note):
    seq = sample_session(states, persona, rng)
    by_name = {s["state"]: s for s in states}
    print(f"[{persona}] 세션 시작 ({len(seq)}단계) · 인증: {auth_note}")
    for name in seq:
        st = by_name[name]
        gap = sample_gap(rng, speed_scale)  # 기록만 — 실제로 간격만큼 멈추려면 time.sleep(gap) 추가
        if st["method"] == "GET" and send:
            url = base_url.rstrip("/") + st["path"].split("{")[0].rstrip("/")
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
            print(f"  +{gap:5.1f}초  GET {st['path']} -> {code}")
        else:
            tag = "전송 안 함(쓰기 상태, v1 한계)" if st["method"] != "GET" else "전송 안 함(--send 없음)"
            print(f"  +{gap:5.1f}초  {st['method']} {st['path']}  [{tag}]")
    print(f"[{persona}] 세션 끝\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--base-url", default="http://127.0.0.1:8089")
    ap.add_argument("--users", type=int, default=5)
    ap.add_argument("--speed-scale", type=float, default=5.0,
                    help="1995년 다이얼업 간격을 줄이는 배속 — 기본 5배 (검증 안 됨, 목적에 맞게 조정)")
    ap.add_argument("--send", action="store_true", help="GET 상태는 실제로 base-url 에 요청을 보낸다")
    ap.add_argument("--no-auth", action="store_true", help="로그인 시도를 끄고 익명으로만 보낸다")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding="utf-8"))
    states = states_from_spec(spec)
    print(f"명세 {a.spec} → 상태 {len(states)}개 · 대상 {a.base_url} · 전송 {'켬' if a.send else '끔'}\n")

    rng = random.Random(a.seed)
    for i in range(a.users):
        persona = "goal" if rng.random() < 0.5 else "browse"
        token, note = (None, "시도 안 함(--no-auth)")
        if a.send and not a.no_auth:
            token, note = auth.login(a.base_url, spec, rng)
        run_session(states, persona, rng, a.base_url, a.send, a.speed_scale, f"10.90.0.{i + 2}", token, note)


if __name__ == "__main__":
    main()
