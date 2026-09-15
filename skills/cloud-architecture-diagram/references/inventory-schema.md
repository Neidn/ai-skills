# 인벤토리 JSON 스키마

`render_drawio.py`의 입력 형식. 재귀 구조이므로 CSP 종류나 계층 깊이에 상관없이 쓸 수 있다.

## 최상위

| 필드 | 필수 | 설명 |
|---|---|---|
| `title` | 권장 | draw.io 다이어그램 탭 이름 |
| `provider` | 선택 | `ncp` / `aws` / `azure` / `gcp` / `onprem` / `hybrid`. 메타 용도 |
| `nodes` | 선택 | 어느 그룹에도 속하지 않는 노드. Internet, 관리자, 외부 SaaS 등 |
| `groups` | 선택 | 최상위 컨테이너. Region, 온프레미스 IDC 등 |
| `edges` | 선택 | 노드 간 연결 |

`nodes`는 그림 위쪽, `groups`는 그 아래에 배치된다. 최상위 항목이 3개 이상이면 2개씩 줄바꿈된다.

## 노드 / 그룹

같은 모양의 객체이고, **`children`이 있으면 그룹, 없으면 노드**로 렌더된다.

```json
{
  "id": "web01",
  "label": "web01\n2vCPU/8GB",
  "kind": "server",
  "children": []
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `id` | ✅ | 전체에서 유일. `edges`가 이 값을 참조한다. 영문/숫자/밑줄 권장 |
| `label` | 권장 | 화면 표시명. `\n`으로 줄바꿈. 없으면 `id`가 표시됨 |
| `kind` | 권장 | 색·모양 결정. 값 목록은 `layout-and-style.md` |
| `children` | 선택 | 하위 노드/그룹 배열 |

### id 규칙

- 중복되면 렌더가 에러로 중단된다.
- 실제 리소스 ID(`ncloud-xxxx-1234`)보다 읽기 쉬운 슬러그(`web01`, `sbn_db`)를 쓴다.
  실제 ID는 `label` 2번째 줄에 넣는다.

### label 작성 요령

2줄 구성이 가장 읽기 좋다.

```
web01
2vCPU/8GB · CentOS 7.9
```

```
db-sbn (10.0.21.0/24)
KR-2
```

## edges

```json
{ "from": "lb01", "to": "web01", "label": "8080", "style": "solid" }
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `from` / `to` | ✅ | 노드 또는 그룹의 `id` |
| `label` | 선택 | 포트, 프로토콜, 용도 |
| `style` | 선택 | `solid`(기본) / `dashed` / `thick` / `none` |

- `solid` — 실제 트래픽 경로
- `dashed` — 복제, 백업, 관리 접근 등 보조 경로
- `thick` — 주 트래픽 경로 강조
- `none` — 방향 없는 단순 인접 관계

존재하지 않는 id를 참조하면 경고만 출력하고 계속 진행하므로, stderr를 확인한다.

## 전체 예시

```json
{
  "title": "○○기관 운영 구성도",
  "provider": "ncp",
  "nodes": [
    { "id": "internet", "label": "Internet", "kind": "external" },
    { "id": "admin", "label": "운영자\nSSL VPN", "kind": "client" }
  ],
  "groups": [
    {
      "id": "kr", "label": "NCP / KR Region", "kind": "region",
      "children": [
        {
          "id": "vpc_prod", "label": "prod-vpc (10.0.0.0/16)", "kind": "vpc",
          "children": [
            {
              "id": "sbn_pub", "label": "public-sbn (10.0.1.0/24)\nKR-1", "kind": "public",
              "children": [
                { "id": "lb01", "label": "Public LB\nweb-lb", "kind": "lb" },
                { "id": "nat01", "label": "NAT Gateway", "kind": "gateway" }
              ]
            },
            {
              "id": "sbn_web", "label": "web-sbn (10.0.11.0/24)\nKR-1", "kind": "private",
              "children": [
                { "id": "web01", "label": "web01\n2vCPU/8GB", "kind": "server" },
                { "id": "web02", "label": "web02\n2vCPU/8GB", "kind": "server" }
              ]
            },
            {
              "id": "sbn_db", "label": "db-sbn (10.0.21.0/24)\nKR-2", "kind": "private",
              "children": [
                { "id": "db01", "label": "Cloud DB for MySQL\nMaster", "kind": "db" },
                { "id": "db02", "label": "Cloud DB for MySQL\nStandby", "kind": "db" }
              ]
            }
          ]
        },
        { "id": "obj", "label": "Object Storage\nbackup-bucket", "kind": "storage" }
      ]
    }
  ],
  "edges": [
    { "from": "internet", "to": "lb01", "label": "443" },
    { "from": "lb01", "to": "web01", "label": "8080" },
    { "from": "lb01", "to": "web02", "label": "8080" },
    { "from": "web01", "to": "db01", "label": "3306" },
    { "from": "web02", "to": "db01", "label": "3306" },
    { "from": "db01", "to": "db02", "label": "복제", "style": "dashed" },
    { "from": "admin", "to": "web01", "style": "dashed" },
    { "from": "db01", "to": "obj", "label": "백업", "style": "dashed" }
  ]
}
```

## 계층 설계 가이드

| 상황 | 권장 구조 |
|---|---|
| 단일 CSP 단일 VPC | Region → VPC → Subnet → 리소스 |
| 멀티 VPC / VPC 피어링 | Region → VPC 여러 개, 피어링은 VPC 간 edge |
| 멀티 리전 / DR | Region 두 개를 최상위 그룹으로 나란히 |
| 하이브리드 | `onprem` kind 그룹을 별도 최상위로, 전용선/VPN은 edge |
| 쿠버네티스 | Subnet → 클러스터 그룹 → 노드풀 그룹 → 워크로드 |

VPC 밖에 있는 매니지드 서비스(Object Storage, DNS 등)는 Region 그룹의 직계 자식으로 둔다.
