# GCP 구성도 레퍼런스

> 검증 상태: **미검증**. 뼈대만 있는 상태다. 이 파일로 구성도를 그릴 때는
> 아래 내용이 확인되지 않았음을 사용자에게 먼저 알린다.

## 1. 리소스 → kind 매핑

| GCP 리소스 | kind | 비고 |
|---|---|---|
| VPC Network | `vpc` | ⚠ 글로벌 리소스. 리전 단위가 아니다 |
| Subnet | `public` / `private` | ⚠ 리전 단위. 존 단위가 아니다 |
| Compute Engine | `server` | 존 단위 |
| Cloud Load Balancing | `lb` | 글로벌/리전 종류 구분 |
| Cloud NAT | `gateway` | |
| Cloud SQL | `db` | |
| Cloud Storage | `storage` | VPC 밖 |
| GKE | `k8s` | |
| Cloud Interconnect / VPN | `network` / `gateway` | |

## 2. 자산 수집

```bash
gcloud compute networks list --format=json
gcloud compute networks subnets list --format=json
gcloud compute instances list --format=json
gcloud compute forwarding-rules list --format=json
```

## 3. 구성도에서 틀리기 쉬운 것 ⚠ 전부 미검증

- **VPC가 글로벌, 서브넷이 리전 단위**다. NCP/AWS와 계층 관계가 뒤집힌다.
  Region → VPC 순서로 그리면 틀린다. VPC → Region → Subnet 순서가 맞다
- **프로젝트가 최상위 경계**다
- 방화벽 규칙이 VPC 전역에 적용되고 태그/서비스 계정으로 대상을 고른다.
  서브넷 경계선으로 표현하면 오해를 부른다

## 4. 라벨 표기 관례

- 리전: `asia-northeast3`, 존: `asia-northeast3-a`

## 확인이 필요한 항목 ⚠

- 전 항목
