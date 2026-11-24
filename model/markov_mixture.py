#!/usr/bin/env python3
"""페르소나 조건부 마르코프 체인 혼합모델 — Cadez, Heckerman, Meek et al. (2003) 의 EM 알고리즘을 작게 구현.

생각: 방문자는 보이지 않는 유형(페르소나) k 중 하나이고, 유형마다 다른 1차 마르코프 전이확률로 페이지를 옮겨 다닌다.
전체 인구를 보면 다양해 보이지만, 유형 하나로 조건을 걸면 다음 페이지가 더 잘 예측된다 — "엔트로피가 줄어든다."

EM:
  E단계: 각 세션이 유형 k 에서 나왔을 사후확률(책임값) 계산 — 세션의 전이들을 유형 k 의 전이확률로 쳤을 때의 우도 비교
  M단계: 책임값으로 가중 평균해 유형별 전이확률 · 유형 비율을 다시 추정

표준 라이브러리만 쓴다. 작은 합성 데이터로 "EM이 진짜 숨겨진 유형을 복원하는가"를 시험한다 (model/test_markov_mixture.py).
"""
from __future__ import annotations

import math
import random
from collections import defaultdict


def fit(sessions: list[list[str]], k: int, states: list[str], iters: int = 50, seed: int = 0):
    """sessions: 세션마다 방문한 페이지 순서 리스트. k: 유형 수. 반환: (유형 비율 리스트, 유형별 전이확률 dict 리스트)."""
    rng = random.Random(seed)
    # 초기화: 유형 비율은 균등, 전이확률은 임의로 흩어서 시작 (대칭을 깨야 EM이 유형을 분리함)
    pi = [1.0 / k] * k
    trans = [defaultdict(lambda: defaultdict(float)) for _ in range(k)]
    for t in trans:
        for s in states:
            w = [rng.random() + 0.1 for _ in states]
            z = sum(w)
            for s2, wi in zip(states, w):
                t[s][s2] = wi / z

    def seq_loglik(seq: list[str], t: dict) -> float:
        ll = 0.0
        for a, b in zip(seq, seq[1:]):
            p = t[a].get(b, 1e-9)
            ll += math.log(max(p, 1e-12))
        return ll

    for _ in range(iters):
        # E단계: 책임값 r[i][k] = P(유형 k | 세션 i) ∝ pi[k] * 우도
        resp = []
        for seq in sessions:
            logs = [math.log(pi[j]) + seq_loglik(seq, trans[j]) for j in range(k)]
            m = max(logs)
            ws = [math.exp(l - m) for l in logs]
            z = sum(ws)
            resp.append([w / z for w in ws])

        # M단계: 책임값으로 가중한 전이 횟수 → 전이확률, 평균 책임값 → 유형 비율
        counts = [defaultdict(lambda: defaultdict(float)) for _ in range(k)]
        for seq, r in zip(sessions, resp):
            for a, b in zip(seq, seq[1:]):
                for j in range(k):
                    counts[j][a][b] += r[j]
        for j in range(k):
            for s in states:
                total = sum(counts[j][s].values())
                if total > 0:
                    for s2 in states:
                        trans[j][s][s2] = counts[j][s].get(s2, 0.0) / total
        pi = [sum(r[j] for r in resp) / len(sessions) for j in range(k)]

    return pi, [{s: dict(d) for s, d in t.items()} for t in trans], resp


if __name__ == "__main__":
    print(__doc__)
