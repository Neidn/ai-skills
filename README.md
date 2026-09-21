# ai-skills

에이전트 종류를 가리지 않는 개인용 스킬 모음. [Agent Skills 개방 표준](https://agentskills.io/specification)
(`SKILL.md`)을 따르므로 Claude Code, Codex, Cursor, Gemini CLI, OpenCode 등에서 같은
파일을 그대로 쓴다.

## 설치

```bash
# 전체 설치 (설치된 에이전트를 자동 감지)
npx skills add Neidn/ai-skills

# 전역 설치 — 모든 프로젝트에서 사용
npx skills add Neidn/ai-skills -g

# 특정 스킬만
npx skills add Neidn/ai-skills --skill cloud-architecture-diagram -g

# 특정 에이전트만
npx skills add Neidn/ai-skills -a claude-code -a codex -g

# 목록만 확인
npx skills add Neidn/ai-skills --list
```

설치 방식을 물어보면 **Symlink**를 고른다. 에이전트마다 복사본이 생기지 않고 원본
하나만 갱신하면 된다.

claude.ai 웹/앱에서 쓰려면 스킬 폴더를 zip으로 묶어 Settings ▸ Capabilities ▸ Skills에
업로드한다. (Code execution 활성화 필요)

```bash
cd skills && zip -r ../cloud-architecture-diagram.zip cloud-architecture-diagram
```

## 스킬

| 스킬 | 설명 |
|---|---|
| `cloud-architecture-diagram` | CSP 자산 목록을 인벤토리 JSON으로 정규화해 편집 가능한 draw.io 구성도와 Mermaid로 렌더 |
| `ncp-cloud-insight-registration` | NCP Server/LB/DB를 Cloud Insight 모니터링 대상으로 등록하는 절차 안내 |
| `document-design` | 문서의 시각 디자인(타이포·간격·색·표·콜아웃)을 디자인 토큰으로 통일. docx/HTML/MD/PPT 공통, HTML용 CSS·토큰 JSON 포함 |
| `table-of-contents` | 제목에서 목차(TOC)를 자동 생성하고 번호 체계(1/1.1/1.1.1)와 앵커를 매김. docx 필드 TOC·HTML 앵커·MD 링크 지원 |
| `document-structure` | 보고서·매뉴얼·제안서·장애 보고서·인수인계 등 유형별 표준 골격으로 문서 뼈대를 먼저 설계 |
| `career-management` | 경력 vault(프로젝트·사실 교정·기술·지원 이력)를 누적 관리하고, vault만 근거로 이력서·경력기술서·포트폴리오·자소서를 생성 |
| `trading-book-audit` | 자동매매 성과를 거래소 원장 기준으로 측정. 손익 회계 버그 카탈로그, 매매당 정규화 판정 규칙, 표본 기준, 증액 게이트 |
| `llm-loop-economics` | LLM을 반복 루프에 넣기 전 호출량×단가로 운영비를 먼저 계산하고 비용·결정론·평가가능성으로 판정. 폴링→이벤트 전환 사다리 |

## 구조

```
ai-skills/
├── AGENTS.md                 # 항상 적용되는 작업 규칙
├── CLAUDE.md -> AGENTS.md    # Claude Code용 심볼릭 링크
├── GEMINI.md -> AGENTS.md    # Gemini CLI용 심볼릭 링크
└── skills/
    └── <skill-name>/
        ├── SKILL.md          # 필수
        ├── references/       # 필요할 때만 읽히는 상세 문서
        ├── scripts/          # 실행 가능한 도구
        └── assets/           # 템플릿, 아이콘
```

## 새 스킬 추가

1. `skills/<skill-name>/SKILL.md` 생성. `name`은 소문자·숫자·하이픈만, **폴더명과 일치**.
2. `description`에 *무엇을 하는지*와 *언제 쓰는지*를 모두 쓴다. 트리거는 전적으로 이
   문장에 달려 있으므로 사용자가 쓸 법한 표현을 넣는다.
3. 본문은 500줄 이내. 상세 내용은 `references/`로 빼고 SKILL.md에서 언제 읽을지 지시한다.
4. 로컬 테스트: `npx skills add . --skill <skill-name>`
5. 커밋·푸시하면 끝. 사용자는 `npx skills add Neidn/ai-skills`로 갱신한다.

## 로컬 개발

```bash
git clone git@github.com:Neidn/ai-skills.git
cd ai-skills
ln -s AGENTS.md CLAUDE.md
ln -s AGENTS.md GEMINI.md
npx skills add . -y
```

## career-management 개인 데이터

`career-management`는 스킬(절차)과 개인 경력 데이터(vault)를 분리한다. 스킬은 이 레포에,
vault는 **비공개**로 둔다. 스킬은 다음 순서로 vault를 찾는다.

1. 환경변수 `CAREER_VAULT` (예: 비공개 레포 `~/career-vault`)
2. 스킬 폴더의 `data/` — `.gitignore`로 커밋 제외. claude.ai 업로드 zip에만 포함한다
3. 작업 디렉터리의 `career/` 또는 `career-vault/`

```bash
# 빈 vault 만들기
python skills/career-management/scripts/init_vault.py ~/career-vault
# 점검
python skills/career-management/scripts/check_vault.py ~/career-vault
```
