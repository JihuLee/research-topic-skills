# research-topic-skills

[English](README.md)

이 저장소는 연구자 한 사람에게 맞춘 연구 주제를 **찾고, 적대적으로 검증하고, 실행 명세로 넘기는** Agent Skills 묶음이다.

- 같은 `SKILL.md` 파일을 Claude Code와 Codex가 그대로 쓴다([Agent Skills 표준](https://agentskills.io/specification)).
- 스킬 자체는 특정 프로젝트와 무관하다. 연구자의 취향, 자원, 과거 기록은 스킬 밖의 **프로필 폴더**에 두고, 스킬은 실행할 때 그 폴더를 읽는다.

## 설계 원칙

1. **생성보다 검증.** 아이디어는 싸게 많이 낼 수 있다. 주제가 죽는 이유는 대개 따로 있다.
   - 몇 주 전에 나온 직접 선행.
   - 다른 이름의 고전 계산.
   - 이미 충분한 값싼 대조군.

   그래서 중심 스킬은 `novelty-gate`다. LLM이 낸 연구 아이디어는 실행 전에는 새로워 보여도 실행 뒤 평가가 크게 떨어진다는 보고가 있다([Si, Hashimoto, Yang 2025](https://arxiv.org/abs/2506.20803)).
2. **"없음"도 정상 결과다.** 후보 개수를 할당하지 않는다.
3. **판정은 증거로만 한다.**
   - 탈락시키려면 이름 있는 논문(URL과 위치)이나 확인 가능한 유도(고전 동치, 이론적으로 강제되는 결과)가 있어야 한다.
   - 검색·접근 실패는 신규성 근거가 아니다. "붐비는 분야"라는 사실만으로 탈락시키지도 않는다.
4. **실험 전에 반증을 설계한다.** 통과 후보와 근접 후보에는 B0(가장 싼 반증 실험)를 붙인다. B0의 임계값은 결과를 보기 전에 해시로 고정한다. 스킬은 B0를 설계만 하고, 실행은 사용자가 승인한다.
5. **취향은 데이터로 둔다.** 선호, 제외, 예산, 과거 주제와 그 탈락 원인, 보유 자산은 프로필 파일에 둔다. 프롬프트를 고치지 않고 파일만 고친다.

## 구성

| 스킬 | 하는 일 | 주 산출물 |
|---|---|---|
| `novelty-gate` | 제안서·후보를 적대적으로 검토한다. 주장을 분해하고, 질의 계열 A–F로 선행을 찾고, 결정적 문장을 원문에서 대조한다. 고전 동치와 이론 강제 여부를 검사하고, 신규성과 실행 가능성을 따로 채점하고, B0를 설계한다 | `gate_report.md`, `evidence.jsonl`, `thresholds.json` |
| `topic-scout` | 정한 level(high: 내 논문·코드·노트 기반, low: 내 분야의 최근 문헌 탐색)과 depth(quick, standard, full)로 번호 붙은 후보를 만든다. 객관적 사실로만 1차 거른 뒤 상위 후보를 `novelty-gate`에 넘긴다 | `candidates.jsonl`, `scout_report.md`, `corpus_manifest.md` 또는 `landscape.md` |
| `research-brief` | 통과한 후보를 실행 명세로 바꾼다. 사용자 양식이 있으면 그 양식을 쓰고, 문헌 사실을 본문에 넣고, 임계값 해시를 고정한다. 사람 팀이나 자동 연구 에이전트가 이 명세로 실행한다 | `brief.md`, `thresholds.json.sha256` |

```
corpus + profile + ledger ─► topic-scout ─► shortlist ─► novelty-gate ─► PASS ─► research-brief
                                  ▲                            │
                                  └──── ledger (탈락·근접) ◄─────┘
```

`novelty-gate`는 단독으로도 쓴다. 이미 가진 제안서를 검토하는 일이 가장 흔하다.

## 설치

[`skills` CLI](https://skills.sh/)로 설치한다.

```bash
# 설치하지 않고 이 저장소의 스킬 목록만 보기
npx skills add JihuLee/research-topic-skills --list

# 세 스킬을 사용자 수준으로 설치(설치할 에이전트는 CLI가 묻는다)
npx skills add JihuLee/research-topic-skills -g

# 스킬 하나만 설치
npx skills add JihuLee/research-topic-skills -g --skill novelty-gate

# 나중에 업데이트·제거
npx skills update -g
npx skills remove -g novelty-gate
```

- `topic-scout`는 후보를 `novelty-gate`에 넘기므로 scout를 쓰려면 둘 다 설치한다.
- 도우미 스크립트는 Python 3.8+ 표준 라이브러리만 쓴다. PDF 텍스트 추출에는 pymupdf나 pdftotext가 있으면 쓰고, 없으면 PDF만 저장한다.

> **주의:** 사용자 수준 설치를 하면 같은 계정으로 도는 **모든** 에이전트 세션에서 스킬 설명이 보인다. 자동 연구 harness 같은 무인 세션도 포함된다. 아래 guardrail 절을 참고한다.

## 사용

프로필 폴더는 이 저장소의 [`templates/`](templates)를 복사해서 시작한다.

```bash
cp -r templates ~/research-profile
mv ~/research-profile/ledger.example.jsonl ~/research-profile/ledger.jsonl   # 예시 줄은 지운다
$EDITOR ~/research-profile/profile.md                                        # json profile 블록 수정
```

사용 예:
- Claude Code: `/novelty-gate proposals/idea.md 검토해줘. profile: ~/research-profile`
- Codex: `$novelty-gate ...`
- 둘 다 스킬 이름을 쓰지 않아도 설명(description)이 맞으면 자동으로 호출된다. 예: "이 아이디어 누가 이미 했는지 확인해줘", "내 논문이랑 코드 보고 후속 주제 찾아줘"

프로필 경로를 찾는 순서는 다음과 같다.
1. 요청에 적은 경로
2. 환경변수 `RESEARCH_PROFILE_DIR`
3. 현재 폴더의 `./research-profile/`
4. 홈의 `~/research-profile/`

모두 없으면 네 가지만 한 번 묻고 프로필을 만든다(아래 참고).

## 자율 연구 framework와의 분리 (guardrail)

이 스킬들은 **연구자가 직접 요청한 세션**에서만 쓴다. 그 세션의 에이전트가 띄운 하위 에이전트까지는 포함된다. 자율 연구 framework의 단계 안에서는 쓰지 않는다. 이유는 셋이다.
- 그런 run은 고정된 자기 워크플로를 따른다.
- 스킬이 묻는 승인 질문에 답할 사람이 없다.
- 스킬이 산출물 폴더를 따로 만든다.

막는 방법은 세 겹이다.
1. **스킬 설명(description):** "For interactive use with a researcher, not for autonomous research pipelines." 에이전트가 스킬을 고를 때 이 문장을 본다.
2. **본문 첫 단계:** "Who may use this skill" 절이 `scripts/guard.py`를 먼저 실행하게 한다. 파이프라인 단계로 실행 중이면 아무것도 하지 않고 멈추게 한다.
3. **`guard.py`:** 다음 중 하나면 종료 코드 3과 함께 차단 메시지를 낸다.
   - 환경변수 `RESEARCH_TOPIC_SKILLS_DISABLE=1`(또는 true, yes, on).
   - 작업 폴더나 그 상위 폴더에 표지 파일 `.no-research-topic-skills`가 있다.
   - 감독 아래 일부러 쓸 때만 `RESEARCH_TOPIC_SKILLS_ALLOW=1`로 위 둘을 무시한다.

framework 쪽에서 할 일은 둘 중 하나다.
- 실행 환경에 `export RESEARCH_TOPIC_SKILLS_DISABLE=1`을 넣는다.
- 작업 공간 루트에 `touch <workspace>/.no-research-topic-skills`를 만든다.

이 guard는 에이전트가 지시를 따른다는 전제의 **협조형** 장치다. 완전히 격리하려면 framework를 별도 OS 사용자로 돌리거나, 스킬을 프로젝트 수준으로만 설치한다.

## 주제 찾기: level과 depth

그냥 요청하면 된다. `topic-scout`가 `scripts/scout_settings.py`로 요청을 설정으로 바꾸고, 시작하기 전에 짧은 카드로 보여 준다.

```
주제 찾아줘
탐색적으로 빠르게 주제 찾아줘, 분야는 의료영상
./my-project 내 코드 기반으로 꼼꼼하게 주제 찾아줘
```

| level | 재료 | 알아듣는 말 |
|---|---|---|
| high | 대부분 내 자료(코퍼스, 보유 자산, ledger의 근접 후보, 80%) | "내 코드", "내 논문", "후속", "based on my code" |
| medium (기본) | 내 자료 절반, 최근 문헌 절반 | (기본값) |
| low | 분야와 취향만 맞춰 최근 문헌을 탐색. 코퍼스는 열지 않는다 | "탐색적", "넓게", "분야만", "exploratory" |

| depth | 어디까지 하나 | 알아듣는 말 |
|---|---|---|
| quick | 번호 붙은 후보와 가벼운 검색 결과까지. 검토할 후보는 사용자가 고른다 | "빠르게", "후보만", "quick" |
| standard (기본) | 1위 후보 하나를 `novelty-gate` light 모드로 검토 | (기본값) |
| full | 상위 3개를 full 모드로 검토 | "꼼꼼", "자세히", "thorough" |

- **level과 무관하게 지키는 것:** 제외 분야, 예산, 정답 정책, ledger 중복 검사, 판정 기준.
- **직접 지정:** `level: low`, `depth: full`, `분야는 …`, `기준일 2026-01-31`, `out: ./scout`, 자료 경로를 요청에 적으면 그대로 쓴다.
- **프로필 기본값:** `scout_level`, `scout_depth`, `corpus_paths`.
- **이어서 쓰기:** 후보는 C1, C2, …로 번호를 붙여 `candidates.jsonl`에 저장한다. "C3 검토해줘", "C1로 명세 써줘"처럼 이어서 요청하면 된다.
- **처음 쓸 때:** 프로필이 없으면 네 가지(분야, 제외 분야, 예산, 언어)만 한 번 묻고, `scripts/profile_init.py`로 `~/research-profile`을 만든 뒤 이어서 진행한다.

## 데이터 파일 명세 (프로필 폴더)

```
<profile_dir>/
├── profile.md      # 필수: 취향 서술 + json profile 블록(상수)
├── ledger.jsonl    # 권장: 과거 주제와 판정, 탈락 원인
├── lessons.md      # 선택: 반복 교훈 체크리스트
├── assets.md       # 선택: 보유 데이터·가중치·캐시·도구
├── corpus/         # 선택: topic-scout 입력(다른 위치면 요청에 경로를 적는다)
└── backtest/       # 선택: 개인 백테스트 사례와 결과
```

### `profile.md`

- **서술 부분:** 좋아하는 결과, 자신의 강점(도메인·장비·데이터 접근), 다시 하고 싶지 않은 연구와 그 이유, 보고받는 방식을 적는다.
- **상수 부분:** `json profile`이라는 info string을 단 코드 블록 하나. 스크립트와 스킬이 이 값을 읽는다.

| 키 | 형식 | 기본값 | 쓰임 |
|---|---|---|---|
| `output_language` | 문자열(`ko`, `en` …) | 요청 언어 | 보고서 언어 |
| `interests` | 문자열 목록(우선순위 순) | — | 생성 관점, 순위 |
| `preferred_contributions` | 목록(`method`, `benchmark`, `analysis`, `theory`, `dataset`) | `method`, `benchmark`, `analysis` | 순위 |
| `target_venues` | 목록 | — | 기여 형태, 심사 기준 |
| `exclusions` | 목록 | `[]` | scout에서는 제외, gate에서는 표시 |
| `ground_truth_policy` | 문자열 | 공개·검증 가능한 정답만, 사람·LLM 판단을 1차 지표로 쓰지 않음 | 실행 가능성 |
| `budgets` | 객체: `tiers`(이름별 `gpu_hours`, `download_gb`), `wall_clock_hours`, `hardware` | — | 실행 가능성, B0 비용 |
| `novelty_entry_threshold` | 정수 1–5 | 4 | PASS와 NEAR-MISS의 경계 |
| `recency_window_months` | 정수 | 6 | 최근 문헌 sweep 범위 |
| `approval_required_for` | 목록(`downloads`, `experiments`, `gpu`) | 셋 다 | 승인 없이는 하지 않는 일 |
| `report_dir_pattern` | 문자열(`{slug}`, `{date}` 치환) | `./gate-{slug}-{date}/` | 산출물 위치 |
| `scout_level` | `high` / `medium` / `low` | `medium` | topic-scout가 내 자료를 얼마나 쓸지 |
| `scout_depth` | `quick` / `standard` / `full` | `standard` | 후보만 / 1위 검토(light) / 상위 3개 검토(full) |
| `corpus_paths` | 경로 목록 | `[]` | 요청에 경로가 없을 때 topic-scout가 쓸 자료 |
| `handoff_template` | 경로 또는 `null` | `null` | research-brief가 채울 사용자 양식 |
| `content_check_command` | 문자열 또는 `null` | `null` | 넘기기 전에 brief에 실행할 검사 명령(예: 비밀 문자열 검사). 출력에 패턴을 찍지 않는 명령이어야 한다 |

### `ledger.jsonl`

한 줄에 JSON 객체 하나를 쓴다. `scripts/ledger.py validate`로 검사한다.

| 키 | 필수 | 형식 |
|---|---|---|
| `id` | ✓ | 문자열, 유일 |
| `date` | ✓ | `YYYY-MM-DD` |
| `title` | ✓ | 문자열 |
| `claim` | ✓ | 한 문장 |
| `verdict` | ✓ | `pass` / `near-miss` / `killed` / `dropped` / `closed` / `none` / `pending` |
| `stage` | | `idea` / `gate` / `b0` / `pilot` / `sealed` / `brief` / `done` |
| `novelty`, `feasibility` | | 정수 1–5 |
| `killers` | | `[{title, url, why}]`. 유도형 탈락이면 `url` 없이 `title`에 "runner derivation"을 적는다 |
| `near_miss_b0` | | 근접 후보를 뒤집을 최소 증거 |
| `tags`, `report`, `notes` | | 목록 / 경로·URL / 문자열 |

```json
{"id": "2026-02-03-T2", "date": "2026-02-03", "title": "...", "claim": "...", "verdict": "near-miss", "stage": "gate", "novelty": 3, "feasibility": 5, "killers": [], "near_miss_b0": "...", "tags": ["uncertainty"], "report": "gate-.../gate_report.md"}
```

ledger는 두 가지에 쓰인다.
- 새 아이디어를 넣을 때 근접 중복을 찾는다(`ledger.py check`). 이름 있는 killer가 있는 과거 주제와 겹치면 강한 신호다. 다만 무엇이 달라졌는지 밝히면 다시 볼 수 있다.
- 게이트가 끝나면 판정을 쌓는다(`ledger.py add --from-summary`). 사용자가 판정을 확인한 뒤에 추가한다.

### `lessons.md`

교훈을 검사 가능한 문장으로 적는다(예: "검사: native 무개입 기준선이 사전등록되었다"). `novelty-gate`는 모든 항목을 체크리스트로 적용하고 결과를 보고서 5절에 적는다. 일반적인 시작 목록은 `templates/lessons.md`에 있다.

### `assets.md`

열: `name | kind | path | size | license | provenance / training split | notes`. 실행 가능성 채점과 "보유 자산 재사용" 생성 관점에 쓰인다. 사전학습 가중치는 학습 split을 꼭 적는다. 평가 자료와 겹치는지 확인하는 데 필요하다.

### `corpus/`

형식에 제한이 없다: 논문(.tex/.pdf/.md), 코드 저장소, 노트, 과거 게이트 보고서. `corpus_scan.py`가 다음 단서의 위치를 찾는다. 판단은 스킬이 한다.
- 이론의 타협: 가정, 근사, 한계
- 코드에만 있는 트릭: clamp, detach, eps, 상수
- 반복문 안의 무거운 연산
- 과거 판정과 교훈

## 산출물 명세 (주제 폴더)

```
<out_dir>/
├── gate_report.md      # 사람이 읽는 보고서. 끝에 gate-summary JSON 블록
├── evidence.jsonl      # 증거 기록: 주장, URL, 원문 인용, 위치, 등급
├── notes/              # 하위 조사 노트
├── lit/                # 받은 PDF와 추출 텍스트(공유할 때 제외 권장)
├── thresholds.json     # B0 사전 고정 임계값과 .sha256
├── corpus_manifest.md  # topic-scout
├── scout_report.md     # topic-scout
└── brief.md            # research-brief
```

**증거 등급**

| 등급 | 뜻 |
|---|---|
| `FT` | 실행자가 전문에서 문장·식·표를 직접 대조했고, `quote_check.py`를 통과했다 |
| `ABS` | 초록·공식 페이지만 확인했다 |
| `SEC` | 하위 에이전트·검색 snippet·2차 인용이고, 확인하지 않았다 |
| `FAIL` | 접근 실패(신규성 근거가 아님) |

결정적 주장(탈락·통과·점수)은 FT가 원칙이다.

**채점** (`references/rubric.md`)

- 신규성 1–5와 실행 가능성 1–5를 따로 매긴다.
- 판정 등급:
  - **PASS:** 신규성이 진입 기준 이상이고, FT로 확인한 최근접 선행이 있고, 실행 가능성이 3 이상이고, B0가 설계되어 있다.
  - **NEAR-MISS:** 신규성이 진입 기준 −1이고, 뒤집을 B0가 있다.
  - **KILLED:** 이름 있는 논문, 고전 동치, 또는 이론 강제로 탈락했다.
  - **DROPPED:** scout가 객관적 사유(제외, 예산, 자료, ledger)로 뺐다.

**`gate-summary` 블록**

보고서 끝에 info string이 `json gate-summary`인 코드 블록으로 넣는다. 스키마는 `novelty-gate/v1`이고 예시는 `skills/novelty-gate/references/report_template.md`에 있다.
- 필수 키: `date`, `literature_cutoff`, `entry_threshold`, `verdict`(`pass`/`none`), `candidates[]`, `coverage[]`(주장 × 질의 계열 A–F).
- 각 후보는 `id`, `title`, `claim`, `novelty`, `feasibility`, `status`, `killer_type`, `closest_prior[]`(`title`, `url`, `tag`, `evidence`)을 갖는다.
- PASS와 NEAR-MISS 후보에는 다음이 더 필요하다.
  - `baselines`: `native`, `common_default`, `simplest_key_info`, `equal_compute`
  - `b0`: `cost`, `primary_endpoint`, `promote_if`, `kill_if`, `inconclusive_if`, `blocked_if`, `known_good`
- 탈락 후보에는 `failing_gate`가 필요하고, 유도형 탈락이면 `derivation`도 필요하다.

## 스크립트

모든 스크립트는 Python 3.8+ 표준 라이브러리만 쓴다. PDF 텍스트 추출에는 pymupdf나 pdftotext가 있으면 쓴다.

| 스크립트 | 위치 | 기능 |
|---|---|---|
| `lit_fetch.py` | gate, scout | `arxiv`(날짜 필터, 엄격한 키워드), `openalex`(관련도 검색과 날짜 필터), `citing`(forward citation), `resolve`(인용 존재 확인; arXiv id도 OpenAlex를 먼저 조회하고, `--no-arxiv` 지원), `pdf`(받기와 텍스트 추출). `--save-abstracts DIR`로 초록을 파일로 남겨 ABS 인용도 대조할 수 있다. HTTP 429가 나면 한 번만 짧게 재시도한 뒤 안내와 함께 바로 실패한다. OpenAlex는 하루 한도가 있다(키 없이 검색 약 100번, 무료 키를 쓰면 약 10배). openalex.org Settings에서 키를 받아 `export OPENALEX_API_KEY=...`로 설정한다 |
| `quote_check.py` | gate, scout | `evidence.jsonl`의 FT 인용이 원문에 실제로 있는지 정규화해서 대조한다(합자, 줄바꿈 하이픈, 공백) |
| `report_lint.py` | gate, brief | `gate`: summary 스키마, 탈락 근거, 대조군 4종, B0, coverage. `brief`: 빈 항목, 자리표시, 문헌 URL 수, 임계값 해시 |
| `ledger.py` | 모두 | `validate`, `list`, `check`(근접 중복), `add`(`--from-summary` 포함), `update` |
| `freeze.py` | gate, brief | `template`, `freeze`(정규화 JSON의 sha256), `verify`(어긋나면 실패), `amend --reason`(수정 이력을 `.amendments.jsonl`에 남김; 결과를 본 뒤에는 강화만 허용) |
| `corpus_scan.py` | scout | 코퍼스에서 단서 위치를 색인한다 |
| `scout_settings.py` | scout | 요청, 프로필, 기본값에서 level, depth, 코퍼스, 분야, 기준일, 출력 폴더를 정하고 설정 카드를 출력한다 |
| `profile_init.py` | 모두 | 몇 가지 답으로 프로필 폴더를 만든다(`--force` 없이는 덮어쓰지 않음) |
| `guard.py` | 모두 | 자율 파이프라인 안이면 차단한다(종료 코드 3) |

## 검증

```bash
python3 -m unittest discover -s tests -v        # 스크립트 단위 테스트(오프라인)
LIT_FETCH_LIVE=1 python3 -m unittest discover -s tests   # 실제 arXiv/OpenAlex 호출 포함
python3 tools/validate_skills.py               # Agent Skills 규격과 이식성, shared 동기화
```

**백테스트 (스킬 품질)**

`skills/novelty-gate/evals/`에 정답이 알려진 공개 사례 3개가 있다.

| 사례 | 확인하는 것 |
|---|---|
| `kills-test-time-dropout-uncertainty` | 아이디어를 이미 담은 논문을 이름으로 찾는가 |
| `flags-theory-forced-rank-metric` | 이론 강제 결과를 알아보는가 |
| `respects-literature-cutoff` | 기준일 이후 논문을 탈락 근거로 쓰지 않는가 |

- 실행: Claude Code에서 skill-creator의 eval 절차를 따르거나, 스킬 폴더에서 `claude plugin eval . --allow-tools Write,Edit,Bash,WebSearch,WebFetch,Agent,Skill`을 쓴다(Claude Code v2.1.269 이상).
- 비용: 한 사례가 조사 세션 한 번이라서 시간과 토큰이 꽤 든다.

**개인 백테스트를 권한다.** 자기 과거 제안서와 실제 탈락 원인으로 사례를 만들면 가장 정확한 평가가 된다. 다만 정답이 새지 않게 해야 한다.
- 에이전트의 자동 메모리(예: 프로젝트별 메모리 색인)는 하위 에이전트에게도 주입된다. 과거 판정이 적힌 메모리가 있는 작업 폴더에서 돌리면 blind가 깨진다. 그런 메모리가 없는 새 폴더나 새 세션에서 돌린다.
- 프로필의 `lessons.md`에서 과거 주제의 탈락 원인 이름을 지울 때는 줄을 지우지 말고 `[redacted]`로 바꾼다. 줄을 지우면 목록이 잘린 것처럼 보인다.
- 해당 주제는 ledger에서 가리고 돌린다.
- 지표:
  - 알려진 killer를 상위 5개 안에 찾은 비율
  - 잘못된 PASS 수
  - 고전 동치 검출
  - 걸린 시간·토큰
- 비교 기준: 스킬 없이 긴 지시문만 준 경우.

## 한계

- 스킬은 지시문이라서 단계를 건너뛰는 것을 완전히 막지는 못한다. 그래서 `report_lint.py`와 `quote_check.py`로 산출물을 검사한다.
- 검색 품질은 호스트의 웹 검색과 공개 색인에 달려 있다.
  - arXiv API는 토큰이 정확히 일치해야 한다.
  - OpenAlex는 인용이 preprint 쪽에 붙기도 하고 출판본 쪽에 붙기도 한다.
  - 유료·봇 차단 문서는 FAIL로 남는다.
- 같은 모델 계열만으로 공격하고 판정하면 사각지대가 겹칠 수 있다(로드맵 참고).

## 로드맵

- **교차 모델 검토:** Codex 같은 다른 모델 계열에 공격 메모나 판정을 맡긴다. `novelty-gate`의 6단계에 연결할 예정이다.
- **주기 점검:** ledger의 근접 후보에 새 선행이나 새 공개 자료가 나왔는지 예약 작업으로 확인한다.

## 개발 규칙

- 공통 파일의 원본은 `shared/`에 둔다. 수정한 뒤 `python3 tools/sync_shared.py`로 각 스킬에 복사하고, `python3 tools/validate_skills.py`로 확인한다. 스킬 안의 복사본을 직접 고치지 않는다.
- 스킬 파일은 자기 폴더 밖(`../`)을 참조하지 않는다. 따로 설치해도 동작해야 하기 때문이다.
- `SKILL.md` 본문은 500줄 미만으로 유지하고, 자세한 내용은 `references/`에 둔다.
- 개발 중에 작업 사본을 바로 쓰려면 `tools/install.sh claude-user` 또는 `tools/install.sh codex-user`로 에이전트 스킬 폴더에 링크한다.

## 변경 이력

- **0.2.0**
  - topic-scout에 level(high/medium/low)과 depth(quick/standard/full), 설정 카드, 후보 번호와 후속 요청, 처음 사용 시 자동 설정을 추가했다.
  - novelty-gate에 light 모드를 추가했다.
- **0.1.0** — 첫 공개: novelty-gate, topic-scout, research-brief, 도우미 스크립트, 프로필 명세, guardrail.

## 출처와 감사

- [Agent Skills specification](https://agentskills.io/specification)
- [Codex skills 문서](https://learn.chatgpt.com/docs/build-skills)
- [ARIS — Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) (MIT). 코드를 가져오지 않고 다음 아이디어만 참고해 다시 썼다.
  - 탈락에는 이름 있는 논문이 필요하다.
  - 방법과 실험 설정의 신규성을 따로 본다.
  - 최근 6개월 sweep.
  - 관점(lens) 기반 생성.
  - 객관적 필터와 품질 판정을 분리한다.
  - 인용 존재를 확인한다.
  - 공격과 판정을 분리한다.
- Si, Hashimoto, Yang (2025), [The Ideation–Execution Gap](https://arxiv.org/abs/2506.20803)
- Beel et al. (2025), [Evaluating Sakana's AI Scientist](https://arxiv.org/abs/2502.14297)

## 라이선스

[MIT](LICENSE) © 2026 Jihu Lee
