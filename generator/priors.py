#!/usr/bin/env python3
"""페르소나별 "기본값" 전이확률 — 아직 어떤 앱의 실제 트래픽으로도 학습하지 않았다 (학습용 라벨링 데이터가 없음, README 참고).
그래서 markov_mixture.fit() 이 배우는 것과 같은 모양({state: {state2: prob}})을, 손으로 정한 상식 규칙으로 채운다:
  - goal(목표지향): 쓰기 상태로 수렴하려 한다 — 전자상거래 "구매자" 같은 행동
  - browse(둘러보기): 읽기 상태에 머무는 비중이 높다 — "그냥 보는 사람"

둘 다 **검증된 모델이 아니라 합리적 기본값**이다. 실제 앱의 라벨링 트래픽이 쌓이면 markov_mixture.fit() 으로
다시 학습해 이 자리를 대체해야 한다.
"""
import random


def build(states: list[dict], persona: str, rng: random.Random) -> dict:
    """states: spec_walk.states_from_spec() 의 출력. 반환: {state_name: {state_name2: prob}}."""
    names = [s["state"] for s in states]
    reads = [s["state"] for s in states if s["kind"] == "read"]
    writes = [s["state"] for s in states if s["kind"] == "write"]
    reads = reads or names
    writes = writes or names

    trans = {}
    for s in states:
        if persona == "goal":
            # 지금까지 쓰기를 한 번도 안 했으면 쓰기 쪽으로 강하게, 이미 썼으면 다른 쓰기나 읽기로 고르게
            w = {n: (3.0 if n in writes else 1.0) for n in names}
        elif persona == "browse":
            w = {n: (3.0 if n in reads else 0.3) for n in names}
        else:
            raise ValueError(f"알 수 없는 페르소나: {persona}")
        z = sum(w.values())
        trans[s["state"]] = {n: v / z for n, v in w.items()}
    return trans


def sample_session(states: list[dict], persona: str, rng: random.Random,
                    mean_len: int = 6, max_len: int = 30) -> list[str]:
    """전이확률로 상태 시퀀스 하나를 뽑는다. 길이는 기하분포 근사(평균 mean_len, max_len 에서 자름)."""
    trans = build(states, persona, rng)
    names = list(trans)
    seq = [rng.choice(names)]
    p_stop = 1.0 / max(mean_len, 1)
    while len(seq) < max_len:
        if rng.random() < p_stop:
            break
        nxt, probs = zip(*trans[seq[-1]].items())
        seq.append(rng.choices(nxt, weights=probs, k=1)[0])
    return seq


if __name__ == "__main__":
    print(__doc__)
