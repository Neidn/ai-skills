---
name: cloud-architecture-diagram
description: >
  클라우드(NCP, AWS, Azure, GCP, 온프레미스 혼재 포함) 자산 목록을 표준 인벤토리 JSON으로
  정규화한 뒤, 편집 가능한 draw.io 구성도와 Mermaid 미리보기로 렌더링한다.
  구성도·아키텍처 다이어그램·네트워크 구성도·인프라 현황도 작성 요청, VPC/서브넷/보안그룹
  구조 시각화, 콘솔 화면·CLI 출력·Terraform state·자산 엑셀에서 뽑은 리소스 목록을 그림으로
  만들어 달라는 요청, 신규 아키텍처 설계안을 그려 달라는 요청에 반드시 사용할 것.
  사용자가 "구성도"라는 단어를 쓰지 않고 "서버 뭐뭐 있는지 그림으로 정리해줘",
  "이 리소스들 관계 좀 보여줘", "인수인계 문서에 넣을 아키텍처" 같이 말해도 적용된다.
metadata:
  author: neidn
  version: "1.0"
---

# Cloud Architecture Diagram

클라우드 자산을 **구조화 → 렌더 → 검수** 순서로 구성도로 만든다.
핵심 원칙: 그림을 손으로 그리지 말고, 먼저 인벤토리 JSON을 만들고 스크립트로 렌더한다.
그래야 자산이 바뀌었을 때 JSON만 고쳐 다시 뽑을 수 있다.

## 산출물

| 형식 | 용도 | 만드는 법 |
|---|---|---|
| `.drawio` | **기본 산출물.** 고객 전달·인수인계·제안서. draw.io / VS Code 확장으로 편집 | `render_drawio.py` |
| Mermaid | 대화·README·위키에 바로 붙이는 미리보기 | `render_drawio.py -f mermaid` |
| `inventory.json` | 다음 갱신 때 재사용할 원본 | 직접 작성 |

세 개를 다 주는 것이 기본이다. 사용자가 "그림만 보여줘"라고 하면 Mermaid를 먼저
보여주고 확정된 뒤 `.drawio`를 뽑는다.

## 워크플로

### 1. 대상 CSP 확정 → 해당 레퍼런스 1개만 읽기

CSP마다 네트워크 계층 구조와 제약이 다르다. 대상을 확정한 뒤
`references/csp/<provider>.md` **하나만** 읽는다. 다른 CSP 파일은 읽지 않는다.

| provider | 파일 | 검증 상태 |
|---|---|---|
| `ncp` | `references/csp/ncp.md` | 부분 검증 |
| `aws` | `references/csp/aws.md` | 부분 검증 |
| `azure` | `references/csp/azure.md` | 미검증 |
| `gcp` | `references/csp/gcp.md` | 미검증 |

- 파일이 **미검증**이면, 그 CSP 특유의 제약은 확인되지 않았음을 사용자에게 먼저 알린다.
- 해당 파일이 아예 없는 CSP면 공통 규칙으로 진행하되 같은 안내를 한다.
- 하이브리드·멀티 CSP 구성이면 관련 파일을 모두 읽되, 그림에서 CSP 경계를
  최상위 그룹으로 분리한다.

### 2. 자산 수집

입력이 무엇인지부터 확인한다. CSP별 CLI 명령은 방금 읽은 `csp/<provider>.md`의 "자산 수집" 절에 있다.
Terraform state, 자산 엑셀, 콘솔 스크린샷, 말로 된 설명처럼 CSP와 무관한 경로는
`references/source-extraction.md`를 본다.

**정보가 부족하면 그리지 말고 먼저 물어본다.** 최소한 이 네 가지는 있어야 한다.

- 리소스 이름과 종류 (서버/DB/LB/스토리지 …)
- 네트워크 위치 (VPC, 서브넷, 존) — 없으면 계층 없는 평면 그림이 되어 쓸모가 떨어진다
- 리소스 간 연결과 포트
- 외부 진입점 (인터넷, VPN, 전용선, 관리자 접근 경로)

### 3. 인벤토리 JSON 작성

스키마 전문과 예시는 `references/inventory-schema.md`를 읽는다. 요약하면:

```json
{
  "title": "○○기관 운영 구성도",
  "provider": "ncp",
  "nodes":  [ { "id": "internet", "label": "Internet", "kind": "external" } ],
  "groups": [ { "id": "vpc1", "label": "prod-vpc (10.0.0.0/16)", "kind": "vpc",
                "children": [ /* 중첩 그룹 또는 노드 */ ] } ],
  "edges":  [ { "from": "lb01", "to": "web01", "label": "8080" } ]
}
```

- `children`이 있으면 컨테이너(그룹), 없으면 리소스(노드)로 렌더된다. 깊이 제한 없음.
- 권장 계층은 **Region → VPC → Subnet → 리소스**. 온프레미스는 별도 최상위 그룹.
- `id`는 전체에서 유일해야 한다. 중복이면 스크립트가 에러로 멈춘다.
- `label`의 `\n`은 줄바꿈으로 렌더된다. 2줄째에 스펙·역할을 넣으면 읽기 좋다.
- `kind` 값에 따라 색과 모양이 정해진다. 목록은 `references/layout-and-style.md` 참고.

### 4. 렌더

```bash
python3 scripts/render_drawio.py inventory.json -o 구성도.drawio
python3 scripts/render_drawio.py inventory.json -f mermaid
```

의존성 없음(Python 3.8+ 표준 라이브러리만). 실패하면 대개 JSON 구조 문제이므로
에러 메시지를 그대로 읽고 인벤토리를 고친다.

### 5. 검수 — 넘기기 전에 반드시 확인

- [ ] 인벤토리에 있는 모든 리소스가 그림에 있는가 (누락 = 사고)
- [ ] 연결이 없는 고아 노드가 있는가. 있다면 정말 고립된 자산인지, 아니면 연결을 빠뜨린 건지
- [ ] 외부에서 들어오는 경로가 전부 표시됐는가 (인터넷, VPN, 전용선, 관리자 SSH)
- [ ] 서브넷 CIDR과 존이 라벨에 들어갔는가
- [ ] 이중화 구성이 이중화로 보이는가 (Active/Standby 표기)
- [ ] `csp/<provider>.md`의 "구성도에서 틀리기 쉬운 것"을 그림과 대조했는가
- [ ] **추측으로 채운 항목을 사용자에게 명시했는가**
- [ ] 이번 작업에서 새로 알게 된 CSP 제약이 있다면, `csp/<provider>.md`에 추가할
      내용을 사용자에게 제안했는가 (이 스킬은 이렇게 보강된다)

### 6. 전달

`.drawio` 파일 경로, Mermaid 블록, 그리고 **추측했거나 확인이 필요한 항목 목록**을
같이 준다. 마지막 항목을 생략하지 않는다.

## 하지 말 것

- **자산을 지어내지 않는다.** 정보가 없는 구간은 노드를 만들지 말고 "확인 필요"로 남긴다.
  구성도는 운영 판단의 근거가 되므로 그럴듯한 빈칸 메우기가 가장 위험하다.
- **SVG/이미지를 직접 손으로 그리지 않는다.** 편집이 안 되면 고객이 쓰지 못한다.
- **한 장에 다 담으려 하지 않는다.** 노드가 40개를 넘으면 전체 개요도 1장 + 영역별
  상세도 N장으로 나눈다. 인벤토리 JSON도 파일을 나눈다.
- IP·계정·키 같은 민감 정보를 라벨에 넣지 않는다. 사설 대역 CIDR은 괜찮다.

## 레퍼런스

- `references/csp/<provider>.md` — **CSP별 계층 매핑, 수집 명령, 제약.** 작업 시작 시
  대상 CSP 파일 하나만 읽는다
- `references/inventory-schema.md` — 스키마 전문, 필드별 규칙, 전체 예시
- `references/source-extraction.md` — CSP 무관 수집 경로(Terraform, 엑셀, 구두 설명)와
  수집 후 공통 정리 절차
- `references/layout-and-style.md` — kind 팔레트, 레이아웃 규칙, CSP 공식 아이콘으로
  바꾸는 법, PNG/PDF/PPT 변환
- `references/csp/_template.md` — 새 CSP 레퍼런스를 추가할 때 쓰는 빈 양식
