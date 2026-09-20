---
name: career-management
description: >
  개인 경력(회사·프로젝트·성과·기술·사실 교정·지원 이력)을 하나의 경력 저장소(vault)에
  누적 관리하고, 그 저장소만을 근거로 이력서·경력기술서·포트폴리오·자기소개서·지원서 문항을
  생성한다. "이력 정리해줘", "이 프로젝트 포트폴리오로 남겨줘", "이번 작업 이력에 추가해줘",
  "경력기술서 써줘", "이력서 업데이트", "이 JD에 맞춰 이력서 뽑아줘", "자기소개서 써줘",
  "지원한 회사 기록해줘", "면접 대비 STAR 정리", "내 경력 중 X 관련 뭐 있었지?" 같은 요청,
  또는 레포·커밋 로그·작업 메모를 경력 자료로 옮기려는 요청에 반드시 사용한다. "이력"이라는
  단어가 없어도 이직·지원·면접 준비, 끝낸 작업을 성과로 남겨두자는 맥락이면 적용한다.
  문서 뼈대는 document-structure, 서식은 document-design과 함께 쓴다.
metadata:
  author: neidn
  version: "1.0"
---

# Career Management

**매번 처음부터 묻지 않는다.** 핵심 원칙: 모든 산출물은 vault에서 나오고, 대화에서 새로
알게 된 사실은 반드시 vault로 돌아간다. vault에 반영되지 않은 정보는 다음 대화에서 또
물어야 한다 — 그게 이 스킬이 없애려는 비용이다.

두 번째 원칙: **과장보다 정확성.** 기여 범위·소유 경계·신규 개발 vs 인수 개선을 정확히
쓴다. 사용자가 말하지 않은 수치는 만들지 않고 `[직접 입력 필요]`로 남긴다. 그럴듯한 숫자를
채우는 것이 이 스킬에서 가장 나쁜 실패다.

## 0. vault 찾기 (항상 먼저)

아래 순서로 처음 발견되는 위치를 vault로 쓴다.

1. 환경변수 `CAREER_VAULT`가 가리키는 디렉터리
2. 이 스킬 폴더의 `data/` (개인 설치본·claude.ai 업로드본)
3. 현재 작업 디렉터리의 `career/` 또는 `career-vault/`
4. claude.ai 프로젝트 파일 `/mnt/project/*portfolio*.md` — 읽기 전용 원천 자료로만 취급

vault가 없으면 `python scripts/init_vault.py <경로>`로 빈 골격을 만들지 사용자에게 묻는다.
구조·스키마 상세는 `references/data-model.md`.

**쓰기 가능 여부를 먼저 판정한다.** claude.ai에서는 스킬 폴더가 읽기 전용이다
(`/mnt/skills/...`). 이 경우 6절 절차를 따른다.

## 1. 요청 분류 → 워크플로 하나만

| 요청 | 워크플로 | 주로 건드리는 파일 |
|---|---|---|
| 새 프로젝트·성과·작업을 남기고 싶다 | 2. 기록 | `projects/<slug>.md`, `skills.md`, `open-items.md` |
| "그건 사실 이렇다", 범위·역할 정정 | 3. 교정 | `facts.md` → 영향받는 `projects/` |
| 이력서·경력기술서·포트폴리오·자소서·폼 답변 | 4. 생성 | 읽기 위주, 결과는 `outputs/` |
| "뭐가 비었지?", 정기 점검 | 5. 점검 | `open-items.md` |
| "X 관련 경험 뭐 있었지?" | 조회 | `grep -ril <키워드> projects/` 후 요약 |
| 지원했다·서류 합격·면접 결과 | 지원 기록 | `applications/log.md` |

한 요청에 여러 개가 섞이면 **기록·교정 → 생성** 순서로 처리한다. 최신 사실이 반영된
상태에서 문서를 뽑아야 한다.

## 2. 기록 (Ingest)

1. **원천 수집**. 가능한 것은 직접 읽고 사용자에게는 나머지만 묻는다.
   - 코드 레포(Claude Code 등): `README`, `git log --oneline --no-merges | head -100`,
     디렉터리 구조, CI 설정, `docs/`. 커밋 해시는 문제 해결 사례의 근거로 남긴다.
   - 대화 내용, 붙여넣은 메모, 기존 포트폴리오 파일.
2. **기존 파일 확인**. `projects/`에 같은 프로젝트가 있으면 새로 만들지 않고 갱신한다
   (`aliases`, 제목, 레포 이름으로 대조).
3. **이해 요약 → 질문 한 번에**. 파악한 내용을 3~5줄로 요약하고, 비어 있는 것만 모아
   한 번에 묻는다: 회사·기간·역할(단독/주도/재작성/담당/조율)·상태·정량 성과·공개 범위.
   답을 못 받은 항목은 추측하지 않고 `[직접 입력 필요]`로 둔다.
4. **작성**. `assets/project-template.md` 형식(5섹션)으로 `projects/<slug>.md`를 쓴다.
   문체·역할 동사는 `references/writing-rules.md`.
5. **연결 갱신**. `skills.md`에 새 기술과 근거 프로젝트, `companies/<회사>.md` 프로젝트
   목록에 slug, 비어 있는 값은 `open-items.md`에 올린다.
6. **CHANGELOG**. `CHANGELOG.md` 맨 위에 `- YYYY-MM-DD 기록: <slug> — 한 줄 요약`.

## 3. 교정 (Correct)

사용자가 사실을 정정하면 **그 답변만 고치지 말고 잠근다.**

1. `facts.md`의 "잠긴 사실"에 한 줄로 추가한다. 틀린 표현이 반복될 수 있으면 "금지 표현"에
   `- [금지] 틀린 표현 → 바른 표현` 형식으로도 넣는다 (`check_vault.py`가 검사한다).
2. `grep`으로 영향받는 `projects/`, `companies/`, `profile.md`를 찾아 같이 고친다.
3. CHANGELOG에 `교정:`으로 남긴다.

## 4. 생성 (Generate)

1. **`facts.md`를 가장 먼저 읽는다.** 생성물의 모든 주장은 여기와 충돌하면 안 된다.
   원천 문서(`sources/`)에 다르게 적혀 있어도 facts.md를 따른다.
2. **산출물 확정**: 유형(이력서 전체/축약/영문, 경력기술서, 포트폴리오, 자기소개서,
   온라인 폼 요약), 지원처·직무, 분량·글자 수 제한. 모호하면 한 번에 묻는다.
   `references/outputs.md`에서 **해당 유형 섹션만** 읽는다.
3. **JD가 있으면** `references/jd-tailoring.md` 절차로 요구사항 ↔ 프로젝트 매핑표를 먼저
   만들어 보여준다. 공백(gap)은 숨기지 않고 보완 근거와 함께 드러낸다.
4. **선별**: `projects/*.md` frontmatter의 `domains`, `tags`, `status`, `highlight`로 고른다.
   `profile.md`의 "타깃 직무" 우선순위를 기본 가중치로 쓴다.
5. **공개 범위 적용**: `disclosure: anonymize`는 고객사명을 `public_alias`로 바꾼다.
   `internal`은 외부 제출물에 넣지 않는다.
6. **초안 → 검수 → 전달**. 아래 체크리스트를 통과시킨 뒤 Markdown으로 전달한다
   (PDF 변환은 사용자가 직접 한다). 파일은 vault의 `outputs/<YYYYMMDD>-<지원처>-<유형>.md`,
   쓰기 불가면 `/mnt/user-data/outputs/`.
7. 지원처가 있으면 `applications/log.md`에 행을 추가한다(상태: 작성중).

## 5. 점검 (Review)

```bash
python scripts/check_vault.py <vault경로>          # 사람이 읽는 리포트
python scripts/check_vault.py <vault경로> --json   # 후속 처리용
```

필수 frontmatter 누락, `[직접 입력 필요]`/`[확인 필요]` 개수, 오래된 파일(기본 180일),
`facts.md` 금지 표현 위반, 회사 파일에 연결되지 않은 프로젝트를 보고한다. 결과로
`open-items.md`를 갱신하고, 사용자에게는 **우선 채울 3~5개**만 묻는다.

## 6. 쓰기 불가 환경 (claude.ai 등)

vault 파일을 직접 고칠 수 없으면:

1. 변경된 파일만 **vault 상대 경로 그대로** `/mnt/user-data/outputs/vault-update/` 아래에
   만든다 (예: `vault-update/projects/ncp-mcp-server.md`). 부분이 아니라 파일 전체를 담는다.
2. 응답 끝에 "덮어쓸 경로" 목록과 CHANGELOG 줄을 알려준다.
3. 사용자는 이를 개인 vault(비공개 레포 권장)에 반영하고, claude.ai 스킬은 필요할 때
   `data/`를 갱신해 다시 zip으로 올린다.

## 검수 체크리스트 (생성물)

- [ ] `facts.md`의 잠긴 사실·금지 표현과 충돌하는 문장이 없는가
- [ ] 모든 수치가 vault에 근거가 있는가. 없으면 `[직접 입력 필요]`로 남겼는가
- [ ] 역할 동사가 실제 기여 범위와 맞는가 (조율·검증을 "수행·구축"으로 부풀리지 않았는가)
- [ ] 인수·개선한 것을 신규 개발로 쓰지 않았는가
- [ ] `anonymize`/`internal` 공개 범위를 지켰는가
- [ ] 문체가 산출물 규칙과 맞는가 (포트폴리오 "~한다", 이력서 명사형 bullet)
- [ ] 글자 수·페이지 제한을 지켰는가 (공백 포함 여부 명시)
- [ ] 공백(gap) 항목을 숨기지 않고 보완 근거와 함께 처리했는가
- [ ] **이번 대화에서 새로 알게 된 사실을 vault에 반영(또는 반영 파일 제공)했는가**

## 하지 말 것

- vault를 읽지 않고 기억·추측으로 이력서를 쓰지 않는다.
- 없는 수치·성과·기간을 만들지 않는다.
- 생성 결과물만 고치고 vault를 그대로 두지 않는다 — 다음 번에 같은 오류가 다시 나온다.
- 개인 vault(`data/`)를 공개 레포에 커밋하지 않는다. `.gitignore`에 있는지 확인한다.
- 고객사 실명을 `anonymize` 프로젝트의 외부 제출물에 넣지 않는다.

## 레퍼런스

- `references/data-model.md` — vault 구조, 파일별 스키마, frontmatter 필드, domains 표준값, slug 규칙
- `references/writing-rules.md` — 문체, 역할 동사 사다리, 수치·출처 표기, 금지 패턴
- `references/outputs.md` — 산출물 유형별 구조·분량·선별 규칙 (필요한 섹션만 읽는다)
- `references/jd-tailoring.md` — JD 분석 → 매핑표 → 강조점 재배열 → gap 처리
- `assets/project-template.md` — 프로젝트 파일 5섹션 템플릿
- `assets/vault-template/` — 빈 vault 골격 (`scripts/init_vault.py`가 복사)
