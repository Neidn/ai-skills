# 레이아웃 · 스타일 · 내보내기

## kind 팔레트

`kind` 값이 색과 모양을 정한다. 목록에 없는 값을 쓰면 회색 기본 스타일로 렌더된다.

### 그룹(컨테이너)용

| kind | 색 | 용도 |
|---|---|---|
| `region` | 회색 | 리전, 최상위 경계 |
| `vpc` | 파랑 | VPC / VNet |
| `zone` | 흰색 | 가용영역, 논리 묶음 |
| `subnet`, `public` | 초록 | 퍼블릭 서브넷 |
| `private` | 주황 | 프라이빗 서브넷 |
| `onprem` | 보라 | 온프레미스 IDC, 기관 내부망 |
| `external` | 밝은 회색 | 외부 영역 |

퍼블릭/프라이빗을 색으로 구분하는 것이 이 팔레트의 핵심이다. 서브넷 kind를 전부
`subnet`으로 두면 그 구분이 사라지므로, **반드시 `public` / `private`로 나눠 쓴다.**

### 노드용

| kind | 모양 · 색 | 용도 |
|---|---|---|
| `server`, `container`, `k8s` | 둥근 사각 · 파랑 | VM, 컨테이너, 노드 |
| `db`, `cache` | 원통 · 주황 | DB, Redis |
| `storage` | 원통 · 노랑 | Object Storage, NAS |
| `lb`, `gateway` | 둥근 사각 · 초록 | LB, NAT, IGW, VPN GW |
| `security` | 둥근 사각 · 빨강 | 방화벽, WAF, IPS |
| `monitoring` | 둥근 사각 · 보라 | 모니터링, 로그 수집 |
| `network` | 둥근 사각 · 회색 | 라우터, 스위치, 회선 |
| `client`, `external` | 타원 · 흰색 | 사용자, 인터넷, 외부 시스템 |

## 자동 레이아웃 규칙

`render_drawio.py`가 적용하는 규칙. 결과가 마음에 안 들면 draw.io에서 직접 옮기면 된다.

- 리프 노드만 있는 컨테이너 → 한 줄에 최대 3개
- 그룹을 품은 컨테이너 → 한 줄에 최대 2개
- 컨테이너 크기는 자식에 맞춰 자동 계산(패딩 20, 헤더 34)
- 최상위 항목은 좌→우로 2개씩 배치 후 줄바꿈
- 노드 기본 크기 170×60, 라벨 줄 수만큼 세로로 늘어남

레이아웃을 바꾸려면 스크립트 상단 상수(`NODE_W`, `GAP`, `MAX_COLS_LEAF` 등)를 수정한다.

## CSP 공식 아이콘으로 바꾸기

기본 스타일은 어디서 열어도 깨지지 않는 도형·색 조합이다. AWS/Azure/GCP 공식 아이콘이
필요하면 `render_drawio.py`의 `NODE_STYLE` / `SHAPE` 대신 draw.io 셰이프 라이브러리
스타일 문자열을 쓴다.

```python
# AWS4 예시
"sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=#F78E04;"
"gradientDirection=north;fillColor=#D05C17;strokeColor=#ffffff;"
"dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;"
"html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ec2;"
```

draw.io에서 해당 도형을 하나 그린 뒤 `Edit Style`(Ctrl+E)로 문자열을 복사하는 것이
가장 확실하다. NCP는 공식 draw.io 라이브러리가 없으므로 기본 팔레트를 쓰거나,
NCP 아이콘 PNG를 `assets/`에 넣고 `shape=image;image=...` 스타일로 참조한다.

## 내보내기

```bash
# draw.io 데스크톱 CLI가 설치된 환경
drawio -x -f png -s 2 -o 구성도.png 구성도.drawio
drawio -x -f pdf -o 구성도.pdf 구성도.drawio
```

PPT에 넣을 때는 PNG(scale 2 이상)보다 **draw.io에서 Edit ▸ Select All ▸ Copy as Image**로
붙여넣는 편이 벡터로 들어가 확대해도 깨지지 않는다.

GitHub·위키에는 Mermaid 출력을 그대로 붙인다. Mermaid는 컨테이너 중첩이 깊어지면
레이아웃이 무너지므로 3단계까지만 쓴다.
