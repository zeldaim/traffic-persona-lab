# traffic-persona-lab — 일반화된 트래픽 재현기 - 미완성

사이트별 로그를 그대로 베끼는 트래픽 재현기는 범용성이 없다. [api-defense-lab](https://github.com/zeldaim/api-defense-lab)의 `traffic/lab_traffic.py`가 그 예시 — DVRA 전용이라 다른 앱(petclinic, 관세청 웹 등)에 쓰려면 매번 다시 짜야 한다. 이 레포는 **앱에 맞춰 손으로 짜지 않아도 되는, 일반화된 합성 트래픽 생성기**를 목표로 한다.

> 연구 단계 — 아직 생성기 코드는 없다. 지금은 설계와 공개 데이터 기반 검증만.

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

## 다음

- [ ] 위 두 데이터셋의 요청 간격·세션 길이를 로그정규분포로 피팅(scipy), 문헌 수치와 정량 비교
- [ ] Cadez et al. 방식의 마르코프 혼합모델 프로토타입 (EM, 작은 합성 데이터로)
- [ ] api-defense-lab의 OpenAPI 명세를 입력으로 받아 탐색 경로를 자동 생성하는 뼈대
