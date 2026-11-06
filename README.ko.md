# research-topic-skills

[영어](README.md)

**연구 주제를 찾고, 정말 새로운지 검증하고, 좋은 주제는 바로 실행할 수 있는 연구 계획으로 바꿔 주는** Agent Skills 묶음입니다. Claude Code, Codex 등 [Agent Skills](https://agentskills.io/specification)를 지원하는 에이전트에서 동작합니다.

| 스킬 | 이렇게 말하면 | 이걸 받습니다 |
|---|---|---|
| `topic-scout` | "연구 주제 찾아줘" | 내 분야(원하면 내 논문·코드까지)에서 뽑은 번호 붙은 후보 주제와, 1위 후보의 검증 결과 |
| `novelty-gate` | "이거 누가 이미 했어?" | 판정(Recommended, Near miss, Rejected), 가장 가까운 선행 논문과 링크, 아이디어를 반증할 가장 싼 첫 실험 |
| `research-brief` | "C1로 연구 계획 써줘" | 대조군, 데이터 분할, 결과 전에 고정한 판정 기준을 담은 실행용 연구 명세 |

**topic-scout → novelty-gate → research-brief** 순서로 이어지며, 각 스킬을 따로 써도 됩니다.

## 설치

```bash
npx skills add JihuLee/research-topic-skills -g
```

- 스킬 하나만 설치하려면 `--skill novelty-gate`를 붙입니다.
- 업데이트는 `npx skills update -g`로 합니다.
- 도우미 스크립트는 Python 3.8 이상만 있으면 되고, 추가 패키지는 필요 없습니다.

## 사용 예시

에이전트에게 그냥 말하면 됩니다. 스킬 이름을 쓰지 않아도 됩니다.

### 1. 주제 찾기

```
연구 주제 찾아줘, 분야는 의료영상
```

스카우트는 먼저 요청을 어떻게 이해했는지 보여 주고 시작합니다.

```
level: medium (profile) · depth: standard (default) · gate: top 1, light mode
corpus: - [none]
direction: 의료영상 · cutoff: 2026-11-04 · out: ./scout-2026-11-04-medium
```

결과로 번호 붙은 후보(C1, C2, …)와 1위 후보의 판정이 담긴 짧은 보고서를 받습니다. 원하는 방향은 평소 말로 정하면 됩니다.

| 원하는 것 | 이렇게 말하기 |
|---|---|
| 내 분야만 맞춰 최근 논문에서 넓게 탐색 | "탐색적으로", "분야만 맞춰서" |
| 내 연구를 바탕으로 | "./my-project 내 코드 기반으로", "내 논문 후속으로" |
| 검증 없이 후보 목록만 빠르게 | "빠르게", "후보만" |
| 상위 3개까지 꼼꼼하게 검증 | "꼼꼼하게", "자세히" |

### 2. 아이디어 검증

```
이거 누가 이미 했는지 봐줘. 학습된 분류기에서 테스트 때도 dropout을 켜고
여러 번 예측해 평균 내면 불확실도를 얻을 수 있다.
```

보고서 예시(요약, `report.ko.md`):

```
## C1 · Test-time dropout for uncertainty — Rejected
novelty score 2/5 · feasibility score 5/5

**Why.** Gal & Ghahramani (2016)가 이미 정확히 이 방법을 제시한다.
논문 본문에서 확인했다.
```

### 3. 결과에서 이어가기

```
C3도 검증해줘
C1로 연구 계획 써줘
```

## 결과물

실행할 때마다 폴더 하나가 생깁니다.
- `report.md`: 사람이 읽는 짧은 보고서입니다. 판정, 이유, 다음 할 일만 쉬운 영어로 담습니다.
- `details.md`: 전체 감사 기록입니다. 인용, 검색 범위, 설정이 들어 있습니다. 판정을 확인하고 싶을 때 봅니다.

보고서를 한국어로도 받으려면 "한국어로도"(또는 `lang: ko`)라고 말하세요. 그러면 `report.ko.md`도 생깁니다. 산문만 번역하고 전문용어는 영어로 둡니다. 매번 받으려면 프로필에 `"extra_report_language": "ko"`를 넣으세요.

## 내 프로필

처음 쓸 때 네 가지만 묻습니다.
1. 분야
2. 피하고 싶은 주제
3. 대략의 계산 예산
4. 보고서를 다른 언어로도 받을지(기본은 영어)

답은 `~/research-profile/`에 저장됩니다. 그 폴더의 `profile.md`를 고쳐 취향을 적거나 기본값을 바꿀 수 있습니다. 이 폴더는 비공개로 두세요.

## 알아둘 점

- 실험은 설계만 합니다. 데이터 다운로드나 실험 실행은 사용자에게 묻기 전에는 하지 않습니다.
- 사람과 함께 쓰는 용도이고, 자율 연구 파이프라인용이 아닙니다. 파이프라인에서 쓰지 못하게 하려면 그 실행 환경에 `RESEARCH_TOPIC_SKILLS_DISABLE=1`을 설정합니다.
- 하루 문헌 검색 횟수를 늘리려면 무료 OpenAlex 키를 설정합니다: `export OPENALEX_API_KEY=...`

나머지 내용은 **[상세 문서](docs/REFERENCE.ko.md)**에 있습니다. 판정 방식, 프로필 형식, 산출물, 스크립트, 개발 방법을 다룹니다.

## 라이선스

[MIT](LICENSE) © 2026 Jihu Lee
