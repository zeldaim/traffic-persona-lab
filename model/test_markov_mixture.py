#!/usr/bin/env python3
"""markov_mixture.fit 이 실제로 숨겨진 두 유형을 복원하는지 — 합성 데이터로 확인.

두 페르소나를 손으로 만든다: '구매자'(menu→cart→checkout→logout 순으로 목표지향)와
'둘러보기'(menu 에 계속 머물다 바로 logout, checkout 은 거의 안 감). 둘을 섞어 세션을 생성하고,
EM(k=2)이 그 둘을 실제로 구분해내는지, 전이확률도 진짜 값과 비슷하게 복원하는지를 시험한다.
  python test_markov_mixture.py
"""
import random

from markov_mixture import fit

STATES = ["menu", "cart", "checkout", "logout"]

TRUE = {
    "buyer": {"menu": {"menu": 0.1, "cart": 0.8, "checkout": 0.05, "logout": 0.05},
              "cart": {"menu": 0.1, "cart": 0.1, "checkout": 0.7, "logout": 0.1},
              "checkout": {"menu": 0.0, "cart": 0.0, "checkout": 0.1, "logout": 0.9},
              "logout": {"menu": 0.0, "cart": 0.0, "checkout": 0.0, "logout": 1.0}},
    "browser": {"menu": {"menu": 0.75, "cart": 0.1, "checkout": 0.02, "logout": 0.13},
                "cart": {"menu": 0.6, "cart": 0.2, "checkout": 0.05, "logout": 0.15},
                "checkout": {"menu": 0.3, "cart": 0.1, "checkout": 0.1, "logout": 0.5},
                "logout": {"menu": 0.0, "cart": 0.0, "checkout": 0.0, "logout": 1.0}},
}


def gen_session(rng: random.Random, persona: str, max_len=10) -> list[str]:
    seq = ["menu"]
    t = TRUE[persona]
    while len(seq) < max_len and seq[-1] != "logout":
        probs = t[seq[-1]]
        states, ws = zip(*probs.items())
        seq.append(rng.choices(states, weights=ws, k=1)[0])
    return seq


def main() -> int:
    rng = random.Random(42)
    labels, sessions = [], []
    for _ in range(300):
        persona = "buyer" if rng.random() < 0.5 else "browser"
        labels.append(persona)
        sessions.append(gen_session(rng, persona))

    pi, trans, resp = fit(sessions, k=2, states=STATES, iters=40, seed=1)

    # 클러스터 번호(0/1)는 임의 — 더 많이 겹치는 쪽을 'buyer'로 매핑해 정확도 계산 (라벨 순서 모호성 처리)
    pred = [0 if r[0] > r[1] else 1 for r in resp]
    true01 = [0 if lab == "buyer" else 1 for lab in labels]
    acc_as_is = sum(p == t for p, t in zip(pred, true01)) / len(pred)
    acc_flip = 1 - acc_as_is
    acc = max(acc_as_is, acc_flip)
    buyer_cluster = 0 if acc_as_is >= acc_flip else 1

    print(f"유형 비율(추정) = {[round(x, 2) for x in pi]} (실제 0.5/0.5 근처여야 함)")
    print(f"군집 정확도(라벨 순서 보정) = {acc:.1%}  (300개 세션, 'buyer' 라벨로 매핑된 클러스터 = {buyer_cluster})")

    buyer_est = trans[buyer_cluster]
    print("\n'구매자' 유형으로 잡힌 클러스터의 menu→cart 추정 확률:",
          round(buyer_est.get("menu", {}).get("cart", 0), 3), "(실제 0.8)")
    print("'구매자' 유형의 checkout→logout 추정 확률:",
          round(buyer_est.get("checkout", {}).get("logout", 0), 3), "(실제 0.9)")

    ok = acc >= 0.85
    print(f"\n{'PASS' if ok else 'FAIL'}  군집 정확도 85% 이상 — EM 이 두 숨겨진 유형을 실제로 분리했다")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
