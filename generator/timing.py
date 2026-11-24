#!/usr/bin/env python3
"""요청 간격 샘플러 — ClarkNet·NASA 로 적합한 로그정규 "몸통" 파라미터를 쓴다.

주의(README·docs/results 참고): 이 숫자는 1995년 다이얼업 시대 값이다. **모양(로그정규)은 두 개의 독립된
실제 데이터셋에서 교차검증됐지만, 절대 수치(중앙값 5~9초)는 지금 웹에 그대로 쓰면 안 된다.** 그래서
speed_scale 로 나눠서 쓴다 — 기본 scale=1.0 은 "1995년 그대로"이고, scale 을 늘리면 간격이 짧아진다
(예: scale=5 → 중앙값이 1/5). 어떤 scale 이 "지금 웹"에 맞는지는 검증 안 됨 — 사용자가 목적에 맞게 조정.

꼬리(99분위)는 로그정규보다 두꺼웠다(docs/results) — 긴 간격 일부는 방치된 세션일 수 있어, 여기선 몸통만
흉내 내고 꼬리의 긴 방치는 모델링하지 않는다 (알려진 단순화).
"""
import math
import random

# ClarkNet(1995-08) · NASA(1995-07) 적합값의 평균 — analysis/lognormal_fit.py 로 계산한 것
MU_1995 = (1.821 + 2.380) / 2
SIGMA_1995 = (1.605 + 1.747) / 2


def sample_gap(rng: random.Random, speed_scale: float = 1.0) -> float:
    """초 단위 요청 간격 하나. speed_scale 이 클수록 더 빠르게(간격이 짧게)."""
    g = math.exp(rng.gauss(MU_1995, SIGMA_1995))
    return g / speed_scale


if __name__ == "__main__":
    print(__doc__)
