# Vault 데이터 모델

vault는 **평범한 Markdown 파일 묶음**이다. DB나 특정 도구에 의존하지 않아야 어느 에이전트·
에디터에서도 읽고, git으로 변경 이력을 남길 수 있다.

## 디렉터리 구조

```
<vault>/
├── README.md             # vault 사용법 (사람용)
├── profile.md            # 인적사항·학력·자격·경력 요약·타깃 직무
├── facts.md              # 잠긴 사실·금지 표현·공백(gap) 전략 ← 생성 전 항상 먼저 읽음
├── skills.md             # 기술 스택 마스터 (분류·수준·근거 프로젝트)
├── open-items.md         # 사용자가 채워야 할 값 목록
├── CHANGELOG.md          # vault 변경 이력 (최신이 위)
├── companies/<slug>.md   # 회사별 재직 정보·역할·프로젝트 목록
├── projects/<slug>.md    # 프로젝트 1개 = 파일 1개 (5섹션)
├── applications/log.md   # 지원 이력 표
├── outputs/              # 생성한 이력서·경력기술서 등 (제출본 보관)
└── sources/              # 원천 자료 원본 (가공 전, 참고용 · 권위 없음)
```

권위 순서: `facts.md` > `projects/`·`companies/`·`profile.md` > `sources/`.
`sources/`와 정규화 파일이 충돌하면 정규화 파일이 맞다.

## projects/<slug>.md frontmatter

```yaml
---
id: ncp-mcp-server            # = 파일명 stem. 소문자-하이픈
title: NCP MCP Server
aliases: [MCP 서버, ncp-mcp]  # 사용자가 부르는 다른 이름, 레포 이름
company: ahnlab-cloudmate     # companies/<slug> 와 일치
period: 2026-06 ~ 현재         # YYYY-MM ~ YYYY-MM | 현재 | [직접 입력 필요]
role: 단독 설계·구현            # writing-rules.md 역할 동사 사다리
team_size: 1                  # 모르면 [직접 입력 필요]
status: poc                   # production | poc | ongoing | done | lab | paused
domains: [운영 자동화·사내 도구, 모니터링·AI]
tags: [Python, FastMCP, OAuth2, Kubernetes, Redis]
highlight: high               # high | medium | low — 이력서 선별 우선순위
disclosure: public            # public | anonymize | internal
public_alias: ""              # anonymize일 때 외부 표기 (예: 공공 연구기관)
repo: ""                      # 공개 가능한 링크만
updated: 2026-09-20
---
```

필수: `id, title, company, period, role, status, domains, disclosure, updated`.
`check_vault.py`가 누락을 보고한다. frontmatter는 한 줄 `key: value`와 `[a, b]` 인라인
리스트만 쓴다 (스크립트가 PyYAML 없이 파싱한다).

### domains 표준 값

이력서 도메인 그룹 헤더와 1:1로 맞춘다. 새 값이 필요하면 여기에 먼저 추가한다.

| 값 | 포함 범위 |
|---|---|
| 클라우드 인프라·IaC | NCP/AWS 설계·운영, Terraform, Ansible, 네트워크(VPC·VPN·ACG) |
| Kubernetes·GitOps | 클러스터 운영, ArgoCD, Helm, Ingress, 오토스케일링 |
| 운영 자동화·사내 도구 | n8n, Python 도구, 보고서·메일 자동화, CI/CD |
| DB·미들웨어 | MySQL, PostgreSQL, MSSQL, Tibero 지원, Tomcat/Apache |
| 보안·컴플라이언스 | 취약점 조치, DevSecOps, 라이선스, 접근제어 |
| 모니터링·AI | 관측성, 이상 탐지, AIOps, LLM/MCP |
| 리더십 | 인턴 지도, 벤더·고객 조율, 표준화 |

### 본문 5섹션 (고정)

`## 1. 직무 요약` → `## 2. 기술 스택`(표) → `## 3. 주요 프로젝트 (STAR)` →
`## 4. 문제 해결 사례` → `## 5. 업무 방식`. 템플릿은 `assets/project-template.md`.
작은 프로젝트는 3·4절을 짧게 줄여도 되지만 섹션 제목은 유지한다.

## companies/<slug>.md

```yaml
---
id: ahnlab-cloudmate
name: 안랩클라우드메이트
name_en: AhnLab CloudMate
period: 2025-05 ~ 현재
title: [직접 입력 필요]
team: MS2팀 (MSP 운영)
updated: 2026-09-20
---
```

본문: `## 역할`(3~5줄), `## 조직 변동`, `## 프로젝트`(`- [[slug]]` 목록).

## facts.md 형식

```markdown
## 잠긴 사실
- 사실 한 줄 (확정 시점)

## 금지 표현
- [금지] 틀린 표현 → 바른 표현

## 공백(gap)과 대응 전략
- 없는 경험 — 대응 전략
```

`[금지]` 줄은 `check_vault.py`가 파싱한다. 화살표 왼쪽은 **그대로 일치하는 문자열**
(정규식 아님)이다. 짧은 단어(예: "DBA")는 오탐이 많으니 구절로 쓴다.

## skills.md 형식

분류별 표 `| 기술 | 수준 | 근거 프로젝트 |`. 수준: `운영`(실서비스 운영) / `구축`(설계·구현)
/ `검증`(PoC·Lab) / `지원`(고객 기술지원) / `학습`. 근거 프로젝트가 없으면 `학습`으로만
둔다 — 이력서 기술 스택에서 근거 없는 항목을 거르는 기준이다.

## applications/log.md 형식

| 일자 | 회사 | 포지션 | 제출본(outputs/ 경로) | 상태 | 메모 |

상태: 작성중 / 제출 / 서류합격 / 면접(n차) / 합격 / 불합격 / 보류 / 철회.

## slug 규칙

- 소문자 영문·숫자·하이픈. 고객사 실명 대신 성격으로 짓는다.
  이미 만든 slug는 바꾸지 말고 `aliases`로 보완한다.
- 한 프로젝트 = 한 파일. 후속 작업은 새 파일이 아니라 같은 파일의 3·4절에 추가하고
  `period`·`status`·`updated`를 갱신한다.
