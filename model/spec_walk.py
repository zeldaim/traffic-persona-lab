#!/usr/bin/env python3
"""OpenAPI 명세 → 마르코프 혼합모델의 "상태"(= 탐색 가능한 작업) 자동 추출 (뼈대, 전이확률은 아직 추정 안 함).

목표: 앱마다 AGENT_WALK 같은 목록을 손으로 안 짜도, 명세 파일 하나만 바꾸면 그 앱의 상태 집합이 나오게.
지금은 상태 목록만 뽑는다 — 실제 전이확률은 1) 공개 트래픽 특성화 연구의 일반 규칙(GET이 POST보다 자주,
읽기가 쓰기보다 인기) 또는 2) 그 앱에서 실측한 소량의 라벨링 트래픽으로 추정해야 한다 (다음 단계, 아직 없음).

  python spec_walk.py <openapi.json 경로>
"""
import json
import sys
from collections import Counter


def states_from_spec(spec: dict) -> list[dict]:
    """명세의 각 (메서드, 경로)를 상태 하나로. method 로 대략적인 성격(읽기/쓰기)을 구분해 둔다 — 나중에
    전이확률 사전(prior)으로 쓸 수 있게 (GET=read, POST/PUT/PATCH/DELETE=write)."""
    out = []
    for path, item in spec.get("paths", {}).items():
        for method, op in item.items():
            if method == "parameters":
                continue
            out.append({
                "state": f"{method.upper()} {path}",
                "method": method.upper(),
                "path": path,
                "kind": "read" if method.lower() == "get" else "write",
                "summary": op.get("summary") or op.get("operationId") or "",
            })
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    states = states_from_spec(spec)
    kinds = Counter(s["kind"] for s in states)
    print(f"{sys.argv[1]} → 상태 {len(states)}개 (읽기 {kinds['read']} · 쓰기 {kinds['write']})")
    for s in states:
        print(f"  [{s['kind']:5}] {s['state']}  {('— ' + s['summary']) if s['summary'] else ''}")
    print("\n(아직 전이확률 없음 — 다음 단계: 공개 연구의 읽기/쓰기 비율 사전 또는 소량 실측 트래픽으로 추정)")


if __name__ == "__main__":
    sys.exit(main())
