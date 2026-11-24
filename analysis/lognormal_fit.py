#!/usr/bin/env python3
"""요청 간격(think-time)이 로그정규분포에 얼마나 맞는지 정량 확인 (scipy 없이, 표준 라이브러리만).

  python lognormal_fit.py <access_log_path>

방법: 로그 변환한 간격의 평균·표준편차로 로그정규 MLE 적합(mu, sigma) → 그 분포의 이론 분위수와
실측 분위수를 비교(Q-Q 식) → 최대 괴리(Kolmogorov–Smirnov 통계량 D)를 직접 계산.
D 가 작을수록(대략 0.05 미만이면 꽤 잘 맞음, 데이터가 수만 건 넘으면 기준은 더 엄격해짐 — 표본이 크면
아주 작은 괴리도 "통계적으로 유의"해지니 D 값 자체 크기로 실무적 적합도를 본다) 로그정규 가정이 그럴듯하다.
"""
import math
import statistics
import sys

from http_log_stats import parse, sessions  # 같은 폴더


def norm_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def ks_statistic(sorted_logs: list[float], mu: float, sigma: float) -> float:
    """정렬된 log(간격) 표본과 적합된 정규분포(mu, sigma) 사이의 KS 통계량 D = 최대 |경험분포 - 이론분포|."""
    n = len(sorted_logs)
    d = 0.0
    for i, x in enumerate(sorted_logs):
        f_theory = norm_cdf((x - mu) / sigma)
        f_emp_before = i / n
        f_emp_after = (i + 1) / n
        d = max(d, abs(f_emp_before - f_theory), abs(f_emp_after - f_theory))
    return d


def quantile(sorted_xs: list[float], q: float) -> float:
    i = (len(sorted_xs) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(sorted_xs) - 1)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (i - lo)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    by_host, n = parse(sys.argv[1])
    gaps, _ = sessions(by_host)
    gaps = sorted(g for g in gaps if g > 0)
    if len(gaps) < 30:
        print("표본이 너무 적음")
        return 1
    logs = sorted(math.log(g) for g in gaps)
    mu, sigma = statistics.mean(logs), statistics.pstdev(logs)
    print(f"표본 {len(gaps):,}건 — 적합된 로그정규: mu={mu:.3f} sigma={sigma:.3f}")

    d = ks_statistic(logs, mu, sigma)
    print(f"KS 통계량 D = {d:.4f}  (작을수록 로그정규 가정에 가까움 — 참고용 간이 계산, scipy 의 정밀한 p-value 아님)")

    print("\nQ-Q 비교 (분위수, 초 단위로 환산):")
    print(f"{'분위':>6} {'실측':>12} {'로그정규 이론':>14}")
    for q in (0.10, 0.25, 0.50, 0.75, 0.90, 0.99):
        emp = math.exp(quantile(logs, q))
        theory = math.exp(mu + sigma * math.sqrt(2) * _inv_erf(2 * q - 1))
        print(f"{q:>6.2f} {emp:>12.1f} {theory:>14.1f}")


def _inv_erf(x: float) -> float:
    """erf 역함수 — 뉴턴법 몇 번으로 충분한 정밀도 (scipy 없이 분위수 계산용)."""
    if x <= -1 or x >= 1:
        raise ValueError("범위 밖")
    # 초기값(Winitzki 근사) 뒤 뉴턴법으로 다듬음
    a = 0.147
    ln1mx2 = math.log(1 - x * x)
    t = 2 / (math.pi * a) + ln1mx2 / 2
    y = math.copysign(math.sqrt(math.sqrt(t * t - ln1mx2 / a) - t), x)
    for _ in range(3):
        y -= (math.erf(y) - x) / (2 / math.sqrt(math.pi) * math.exp(-y * y))
    return y


if __name__ == "__main__":
    sys.exit(main())
