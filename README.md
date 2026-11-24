# traffic-persona-lab — 일반화된 트래픽 재현기

사이트별 로그를 그대로 베끼는 트래픽 재현기는 범용성이 없다. [api-defense-lab](https://github.com/zeldaim/api-defense-lab)의 `traffic/lab_traffic.py`가 그 예시 — DVRA 전용이라 다른 앱(petclinic, 관세청 웹 등)에 쓰려면 매번 다시 짜야 한다. 이 레포는 **앱에 맞춰 손으로 짜지 않아도 되는, 일반화된 합성 트래픽 생성기**를 목표로 한다.

> **v1 완성 (2026-11-25)** — `generator/gen.py` 로 OpenAPI 명세 하나만 주면 실제 HTTP 트래픽을 쏜다. "완벽히 검증된 모델"은 아니다 — 알려진 한계는 아래 참고.

## 빠르게 써 보기

```
python generator/gen.py <openapi.json 경로> --base-url http://<대상> --users 5 [--send]
```

`--send` 없이 돌리면 전송 없이 세션 로그만 찍는다(기본, 안전). `model/spec_walk.py`(명세 → 상태) + `generator/priors.py`(페르소나별 전이확률) + `generator/timing.py`(ClarkNet·NASA 교차검증된 로그정규 몸통) 세 조각을 엮은 것이다.

## v1의 알려진 한계 (숨기지 않음)

- **전이확률(`priors.py`)은 실측이 아니라 손으로 정한 기본값이다.** 어떤 앱의 실제 라벨링 트래픽으로도 아직 학습 안 됨 — `model/markov_mixture.py`(EM)로 다시 배우는 게 다음 단계.
- **인증을 전혀 처리하지 않는다.** api-defense-lab에 실제로 돌려 보니, 로그인 없이 보호된 경로를 반복 요청하는 `browse` 세션이 **기존 `agent` 탐지 룰(lab_block)에 실제로 걸렸다** — 정상 생성기인데 공격 에이전트와 구별이 안 된 것. 토큰 발급·로그인 흐름을 붙이는 게 다음 단계 중 가장 급함.
- **쓰기(POST/PUT/PATCH/DELETE) 상태는 실제로 전송 안 한다.** 명세에 요청 본문 예시가 없어 뭘 보내야 할지 모른다 — 시뮬레이션 로그로만 남긴다.
- **타이밍 절대값은 1995년 다이얼업 시대 수치다** (`timing.py` 의 `speed_scale`로 보정하지만, 어떤 배율이 "지금 웹"에 맞는지는 검증 안 됨).

## 문제의식

트래픽을 "탐색"(다음에 뭘 부르나)과 "타이밍"(언제 부르나)으로 나눈다.

- **탐색**은 앱마다 다르다 — OpenAPI 명세에서 자동으로 뽑고, **페르소나(잠재 유형)를 조건으로 거는 마르코프 체인 혼합모델**로 다음 호출을 예측한다. 전체 인구는 다양해 보여도 유형 하나 안에서는 패턴이 예측 가능해진다("필연적"은 과장이고, 정확히는 엔트로피가 줄어든다).
- **타이밍**(요청 간격·세션 길이)은 앱과 무관하게 실제 웹 트래픽 특성화 연구에서 가져와 일반화한다.

## 검증 1 — 보유 실데이터는 부적합했다 (2026-11-25)

처음 계획은 팀 프로젝트의 실 로그(`shadow_api_monitoring` 레포, `teamweb_labeled_2026-11-11`)를 "실제 인간 행동" 비교군으로 쓰는 것이었다. **틀렸다** — 그 로그의 정상 트래픽 자체가 정상 트래픽 생성기(manifest 8개)가 만든 **합성 트래픽**이었다 (고유 출발지 9개, 세션 하나가 요청 414,722건까지 감 — 사람이 아니라 스크립트). 그래서 공개 데이터셋([Internet Traffic Archive](https://ita.ee.lbl.gov/html/traces.html)의 ClarkNet-HTTP, 1995년 실제 이용자 9만 명)으로 바꿔 비교했다.

결과와 수치는 [docs/results/clarknet_vs_teamweb_2026-11-25.md](docs/results/clarknet_vs_teamweb_2026-11-25.md).

## 재현

```
python analysis/http_log_stats.py <access_log_path>
```

ClarkNet-HTTP 받기(자유 재배포 명시됨, [출처](https://ita.ee.lbl.gov/html/contrib/ClarkNet-HTTP.html)):
```
curl -o clarknet_aug28.gz ftp://ita.ee.lbl.gov/traces/clarknet_access_log_Aug28.gz
gunzip clarknet_aug28.gz
```

**주의:** NASA-HTTP는 "일반적인 트래픽 패턴 분석 이상은 하지 말 것"이라는 이용 제한이 있어 세션 단위 분석에는 안 쓴다. teamweb 처럼 민감할 수 있는 로그(평문 비밀번호 등)는 절대 이 레포에 커밋하지 않는다 — `.gitignore` 참고.

## 참고문헌

- Barford & Crovella, *Generating Representative Web Workloads for Network and Server Performance Evaluation* (SIGMETRICS 1998) — SURGE
- Wilson, *What Were They Thinking: Modeling Think Times for Performance Testing* (CMG)
- Harchol-Balter et al., NSDI 2006 — open vs closed 워크로드 모델
- **Cadez, Heckerman, Meek et al., *Model-Based Clustering and Visualization of Navigation Patterns on a Web Site* (Data Mining and Knowledge Discovery, 2003)** — 마르코프 체인 혼합모델 + EM, 이 프로젝트의 핵심 참고
- Gallaugher & McNicholas, arXiv:1802.04849 — 연속시간 마르코프 혼합모델로 확장

## 진행 상황 (2026-11-25)

- [x] **로그정규 피팅 정량화** (`analysis/lognormal_fit.py`, scipy 없이 직접 구현) — ClarkNet 몸통(10~75분위)은 로그정규와 잘 맞지만(KS D=0.128), **꼬리(99분위)는 실측 786초 vs 이론 259초로 크게 벌어짐**. Wilson 논문이 경고한 대로 "긴 간격 = 방치·포기된 세션"일 가능성. 몸통과 꼬리를 다른 모델로 다뤄야 할 수 있음.
- [x] **Cadez et al. 방식 마르코프 혼합모델 프로토타입** (`model/markov_mixture.py` + `model/test_markov_mixture.py`) — 합성 데이터(구매자 vs 둘러보기 두 페르소나)로 EM이 실제 숨겨진 유형을 **군집 정확도 87%**로 복원, 전이확률도 실제값에 근접(0.8→0.721, 0.9→0.892). 작은 규모에서 설계가 작동함을 확인.
- [x] **명세 기반 탐색 뼈대** (`model/spec_walk.py`) — OpenAPI 명세를 상태 집합으로 자동 변환. **api-defense-lab(21개 상태)과 reservoir-rtu-lab(6개 상태) 양쪽에서 코드 수정 없이 포팅 확인** — "앱마다 재현기를 다시 짠다"는 원래 문제를 실제로 풀었다는 첫 증거.

## 다음

- [ ] **인증 처리 — 가장 급함**: 토큰 발급·로그인 흐름을 붙여서 로그인 없이 보호 경로만 때리는 오탐을 없앤다 (lab_traffic.py의 `User` 클래스 참고)
- [ ] 쓰기 상태도 실제 전송 — 명세의 요청 본문 스키마에서 최소한의 유효 payload를 자동 생성
- [ ] `priors.py`의 손으로 정한 전이확률을 `markov_mixture.py`(EM)로 실측 라벨링 트래픽에서 다시 학습
- [ ] 꼬리가 두꺼운 이유(세션 경계 정의 문제인지, 진짜 다른 분포인지) 확인 — 세션 경계(GAP_S) 값을 바꿔 가며 민감도 분석
