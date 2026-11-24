#!/usr/bin/env python3
"""명세에서 회원가입·로그인 경로를 추측해 토큰을 받아 온다 (OAuth2 password 류 패턴을 가정한 휴리스틱).

가정: 회원가입 경로는 경로 이름에 'regist'가 들어가고, 로그인 경로는 'token' 또는 'login'이 들어간다.
둘 다 username·password 류 필드를 요구한다(스키마에서 읽음). 이 가정과 안 맞는 앱(예: HMAC·API 키 인증인
reservoir-rtu-lab)은 토큰을 못 받고, 그건 실패로 보고한다 — 조용히 넘어가지 않는다.

표준 라이브러리만 쓴다.
"""
import json
import random
import string
import urllib.error
import urllib.parse
import urllib.request


def _resolve(schema: dict, spec: dict) -> dict:
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return spec["components"]["schemas"][name]
    return schema


def _fake_value(name: str, rng: random.Random) -> str:
    n = name.lower()
    suffix = "".join(rng.choices(string.digits, k=4))
    if "phone" in n:
        return f"010-{suffix}-{suffix}"
    if "email" in n:
        return f"gen{suffix}@example.invalid"
    if "password" in n:
        return "Passw0rd!x"
    if "username" in n or n in ("name", "user"):
        return f"genuser{suffix}"
    return f"gen{suffix}"


def _build_body(schema_ref: dict, spec: dict, rng: random.Random, overrides: dict) -> dict:
    schema = _resolve(schema_ref, spec)
    body = {}
    for field in schema.get("required", []):
        body[field] = overrides.get(field, _fake_value(field, rng))
    return body


def _find_op(spec: dict, keyword: str):
    for path, item in spec.get("paths", {}).items():
        if keyword in path.lower():
            for method, op in item.items():
                if method.lower() == "post" and "requestBody" in op:
                    return path, op
    return None, None


def _post(base_url: str, path: str, op: dict, spec: dict, rng: random.Random, overrides: dict):
    rb = op["requestBody"]["content"]
    if "application/x-www-form-urlencoded" in rb:
        ctype, ref = "application/x-www-form-urlencoded", rb["application/x-www-form-urlencoded"]["schema"]
        body = _build_body(ref, spec, rng, overrides)
        data = urllib.parse.urlencode(body).encode()
    elif "application/json" in rb:
        ctype, ref = "application/json", rb["application/json"]["schema"]
        body = _build_body(ref, spec, rng, overrides)
        data = json.dumps(body).encode()
    else:
        return None, f"지원 안 하는 content-type: {list(rb)}"
    req = urllib.request.Request(base_url.rstrip("/") + path, data=data, method="POST",
                                 headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"{path} -> {e.code} {e.read()[:200]}"
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return None, f"{path} -> 연결 실패 {e}"


def login(base_url: str, spec: dict, rng: random.Random) -> tuple[str | None, str]:
    """(토큰 또는 None, 상태 메시지) — 회원가입(있으면) → 로그인 순. 실패하면 이유를 메시지로 남긴다."""
    reg_path, reg_op = _find_op(spec, "regist")
    login_path, login_op = _find_op(spec, "token")
    if login_op is None:
        login_path, login_op = _find_op(spec, "login")
    if login_op is None:
        return None, "로그인 경로를 명세에서 못 찾음 (경로에 'token'·'login'이 없음) — HMAC·API 키 인증일 수 있음"

    creds = {}
    if reg_op is not None:
        creds = {k: v for k, v in _build_body(reg_op["requestBody"]["content"]
                 .get("application/json", {}).get("schema", {}), spec, rng, {}).items()
                 if k in ("username", "password")}
        _, err = _post(base_url, reg_path, reg_op, spec, rng, creds)
        if err:
            return None, f"회원가입 실패 — {err}"

    resp, err = _post(base_url, login_path, login_op, spec, rng, creds)
    if err:
        return None, f"로그인 실패 — {err}"
    for key in ("access_token", "token", "jwt", "id_token"):
        if key in resp:
            return resp[key], f"로그인 성공 ({login_path})"
    return None, f"로그인 응답에 토큰 필드 없음: {list(resp)}"


if __name__ == "__main__":
    print(__doc__)
