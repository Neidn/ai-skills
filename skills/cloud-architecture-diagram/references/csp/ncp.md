# NCP 구성도 레퍼런스

> 검증 상태: **부분 검증**. 공식 문서로 확인한 항목과 실무 경험 기반 항목이 섞여 있다.
> ⚠ 표시는 운영 환경에서 재확인이 필요한 항목.

## 1. 리소스 → kind 매핑

| NCP 리소스 | kind | 비고 |
|---|---|---|
| VPC | `vpc` | 리전 단위. 서브넷은 존 단위 |
| Subnet (일반/GEN) | `public` 또는 `private` | 서브넷 속성 그대로 |
| Subnet (LB 전용) | `public` / `private` | 라벨에 `LB 전용` 명시 |
| Subnet (NATGW 전용) | `public` | 라벨에 `NAT 전용` 명시 |
| Server | `server` | |
| Bare Metal Server | `server` | 전용 서브넷 필요 ⚠ |
| Load Balancer (ALB/NLB/NPLB) | `lb` | 종류를 라벨 2번째 줄에 |
| NAT Gateway | `gateway` | |
| Internet Gateway | — | 노드로 그리지 않고 인터넷 연결선으로 표현 |
| Cloud DB for MySQL/PostgreSQL/Redis | `db` / `cache` | Master·Standby 각각 노드 |
| Object Storage | `storage` | VPC 밖. Region 그룹 직계 자식 |
| NAS | `storage` | |
| Ncloud Kubernetes Service | `k8s` | 클러스터를 그룹으로, 노드풀을 하위 그룹으로 |
| IPsec VPN Gateway | `gateway` | |
| Cloud Connect / 전용회선 | `network` | 온프레미스 그룹과 edge로 연결 |
| WAF / Security Monitoring | `security` | |
| Cloud Insight | `monitoring` | |

## 2. 자산 수집

```bash
# 네트워크
ncloud vpc getVpcList --regionCode KR
ncloud vpc getSubnetList --regionCode KR --vpcNo <VPC_NO>
ncloud vpc getNatGatewayInstanceList --regionCode KR

# 컴퓨트 / LB
ncloud vserver getServerInstanceList --regionCode KR
ncloud vloadbalancer getLoadBalancerInstanceList --regionCode KR

# 연결 관계 추론용
ncloud vserver getAccessControlGroupList --regionCode KR
ncloud vserver getAccessControlGroupRuleList --accessControlGroupNo <ACG_NO>
```

옵션명은 CLI 버전마다 다르므로 `--help`로 확인한다. 결과가 비면 리전 코드와
**사이트(public / gov / fin)** 부터 의심한다.

Terraform으로 관리되는 환경이면 `terraform show -json`이 더 정확하다.
`source-extraction.md` 참고.

### 서브넷 속성에서 읽어낼 것

- `subnetType` (PUBLIC / PRIVATE) → 그대로 `kind`
- `usageType` (GEN / LOADB / NATGW / BM) → 전용 서브넷 여부. 라벨에 명시
- `zoneCode` (KR-1 / KR-2) → 라벨 2번째 줄

## 3. 구성도에서 틀리기 쉬운 것

### LB와 NAT Gateway는 전용 서브넷에 들어간다

**AWS와 가장 크게 다른 지점이고 가장 자주 틀린다.** AWS는 퍼블릭 서브넷에 NAT GW와
ALB를 같이 두지만, NCP는 LB 전용 서브넷과 NAT 전용 서브넷을 따로 만들어야 한다.
웹 서버와 LB를 같은 서브넷 박스 안에 그리면 실제 구성과 다른 그림이 된다.

존 이중화까지 하면 서브넷 수가 금방 늘어난다(존 2개 × 용도별). 서브넷 박스가 많아
그림이 복잡해 보여도 임의로 합치지 않는다.

### 서브넷은 존에 고정된다

서브넷 하나가 여러 존에 걸치는 그림은 틀렸다. 존 이중화는 **같은 용도의 서브넷을
존마다 하나씩** 두는 방식으로 표현한다. 존을 그룹으로 묶어 `zone` kind를 쓰거나,
서브넷 라벨 2번째 줄에 존 코드를 적는다. 서브넷이 6개 이하면 후자가 덜 복잡하다.

### ACG와 NACL을 한 경계선으로 뭉뚱그리지 않는다

- **ACG** — 서버의 NIC 단위. 허용 규칙만 있다. VPC 환경에서 서버당 NIC는 3개까지
- **NACL** — 서브넷 단위. 허용과 차단 규칙을 모두 쓴다

구성도에 보안 정책을 넣어야 한다면 ACG는 서버 노드 쪽, NACL은 서브넷 박스 쪽에
주석으로 붙인다. 둘을 하나의 "방화벽" 박스로 그리면 검토자가 적용 범위를 오해한다.
규칙 내용 자체는 구성도가 아니라 별도 표로 빼는 편이 낫다.

### Classic 환경은 계층이 다르다

Classic에는 VPC·서브넷 개념이 없다. Classic 자산을 VPC 계층에 억지로 끼워 넣지 말고
별도 최상위 그룹(`kind: "external"`)으로 분리한다. 한 고객사에 두 환경이 섞여 있으면
반드시 구분해서 그린다.

### 사이트(public / gov / fin) 구분

공공(gov)·금융(fin)은 별도 콘솔이고 사용 가능한 서비스와 리전이 다르다. 공공기관
구성도라면 **다이어그램 제목이나 Region 그룹 라벨에 사이트를 명시**한다.
`NCP(공공) / KR Region` 형태. 이게 없으면 나중에 보는 사람이 일반 리전 구성으로 오해한다.

### VPC 밖 서비스

Object Storage, DNS, CDN, Certificate Manager 등은 VPC 내부가 아니다. VPC 박스 안에
그리면 틀린다. Region 그룹의 직계 자식으로 두고 VPC 내부 리소스와 점선으로 연결한다.

### CIDR 제약

서브넷은 /16 ~ /28 범위. VPC CIDR 안에 포함되어야 하고 사설 대역만 쓴다.
라벨에 적은 CIDR이 이 범위를 벗어나면 수집 과정에서 잘못 읽은 것이다.

### 멀티 VPC

고객사당 VPC 여러 개를 쓰는 구성이 흔하다. VPC가 3개를 넘으면 한 장에 다 넣지 말고
**전체 개요도 1장(VPC 박스만, 내부 생략) + VPC별 상세도 N장**으로 나눈다.
VPC 간 연결은 개요도에서만 표현한다.

## 4. 라벨 표기 관례

운영 중인 네이밍 컨벤션을 그대로 라벨에 쓴다.

```
서버          cm-prod-web-01
              2vCPU/8GB · CentOS 7.9

서브넷        cm-pub-subnet-a (10.0.1.0/24)
              KR-1 · LB 전용

VPC           cm-vpc-01 (10.0.0.0/16)

ACG (주석)    cm-web-acg
```

- 존: `KR-1`, `KR-2` (AWS식 `ap-northeast-2a` 아님)
- 리전 그룹: `NCP(공공) / KR Region` 처럼 사이트 포함
- 공인 IP는 라벨에 적지 않는다. 필요하면 `공인 IP 할당` 정도로만 표기
- 중지 상태 서버는 라벨에 `(중지)` 추가. 조용히 섞지 않는다

## 확인이 필요한 항목 ⚠

아래는 실제 운영 환경에서 확인한 뒤 이 문서를 고쳐야 한다.

- Bare Metal 전용 서브넷 요건
- 이 문서의 kind 매핑이 사내 구성도 표준 표기와 일치하는지
- 고객사별로 다른 네이밍 규칙이 있다면 그 목록
