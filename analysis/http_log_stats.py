#!/usr/bin/env python3
"""HTTP 접속 로그 → 요청 간격(think-time)·세션 길이 기초 통계 (Common/Combined Log Format).

  python http_log_stats.py <access_log_path> [--hash-host]

--hash-host: 출발지를 해시로만 묶는다 (민감할 수 있는 로그 — 원본 IP·호스트명을 출력하지 않음).
세션 경계: 같은 출발지에서 30분(1800초) 넘게 비면 새 세션 (SURGE 류 관례).
표준 라이브러리만 쓴다.
"""
import argparse
import hashlib
import math
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime

LINE = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "')
GAP_S = 1800


def parse(path):
    by_host = defaultdict(list)
    n = 0
    with open(path, encoding="latin-1") as f:
        for line in f:
            m = LINE.match(line)
            if not m:
                continue
            host, ts = m.groups()
            try:
                t = datetime.strptime(ts, "%d/%b/%Y:%H:%M:%S %z").timestamp()
            except ValueError:
                continue
            by_host[host].append(t)
            n += 1
    return by_host, n


def sessions(by_host):
    gaps, lens = [], []
    for host, times in by_host.items():
        times.sort()
        sess = [times[0]]
        for t in times[1:]:
            d = t - sess[-1]
            if d <= GAP_S:
                if d > 0:
                    gaps.append(d)
            else:
                lens.append(len(sess))
                sess = []
            sess.append(t)
        lens.append(len(sess))
    return gaps, lens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--hash-host", action="store_true")
    a = ap.parse_args()

    by_host, n = parse(a.log)
    if a.hash_host:
        hashed = defaultdict(list)
        for host, times in by_host.items():
            hashed[hashlib.sha1(host.encode()).hexdigest()[:8]].extend(times)
        by_host = hashed

    print(f"총 요청 {n:,} · 고유 출발지 {len(by_host):,}")
    gaps, lens = sessions(by_host)
    gaps_pos = [g for g in gaps if g > 0]
    if gaps_pos:
        log_gaps = [math.log(g) for g in gaps_pos]
        print(f"\n== 요청 간격(think-time), 세션 내 {len(gaps_pos):,}건 ==")
        print(f"중앙값 {statistics.median(gaps_pos):.1f}초 · 평균 {statistics.mean(gaps_pos):.1f}초")
        print(f"log(간격) meanlog={statistics.mean(log_gaps):.3f} sdlog={statistics.pstdev(log_gaps):.3f}")
    if lens:
        print(f"\n== 세션 길이(요청 수), {len(lens):,}개 세션 ==")
        print(f"중앙값 {statistics.median(lens)} · 평균 {statistics.mean(lens):.2f} · 최대 {max(lens)}")
        print(f"요청 1건짜리 세션 비율: {sum(1 for s in lens if s == 1) / len(lens):.1%}")


if __name__ == "__main__":
    sys.exit(main())
