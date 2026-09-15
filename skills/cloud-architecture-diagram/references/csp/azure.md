# Azure 구성도 레퍼런스

> 검증 상태: **미검증**. 뼈대만 있는 상태다. 이 파일로 구성도를 그릴 때는
> 아래 내용이 확인되지 않았음을 사용자에게 먼저 알린다.

## 1. 리소스 → kind 매핑

| Azure 리소스 | kind | 비고 |
|---|---|---|
| VNet | `vpc` | |
| Subnet | `public` / `private` | ⚠ Azure는 서브넷 자체에 public/private 속성이 없다. NSG와 라우팅으로 판단 |
| Virtual Machine | `server` | |
| Load Balancer / Application Gateway | `lb` | ⚠ App Gateway는 전용 서브넷 필요 |
| NAT Gateway | `gateway` | |
| Azure SQL / Database for MySQL | `db` | |
| Storage Account | `storage` | VNet 밖 |
| AKS | `k8s` | |
| VPN Gateway / ExpressRoute | `gateway` / `network` | ⚠ GatewaySubnet 전용 서브넷 필요 |

## 2. 자산 수집

```bash
az network vnet list -o json
az network vnet subnet list --vnet-name <VNET> -g <RG> -o json
az vm list -d -o json
az network lb list -o json
```

## 3. 구성도에서 틀리기 쉬운 것 ⚠ 전부 미검증

- **리소스 그룹이 VNet과 직교한다.** 하나의 VNet 리소스가 여러 리소스 그룹에
  흩어질 수 있어 계층 설계가 NCP/AWS와 다르다. 구성도 계층은 네트워크 기준으로
  잡고, 리소스 그룹은 라벨에 표기하는 편이 낫다
- **구독(Subscription)이 최상위 경계**다
- GatewaySubnet, AzureFirewallSubnet 등 **이름이 고정된 전용 서브넷**이 있다
- NSG는 서브넷과 NIC 양쪽에 붙을 수 있다

## 4. 라벨 표기 관례

- 리전 표기: `koreacentral`
- 가용성 영역: `Zone 1/2/3`

## 확인이 필요한 항목 ⚠

- 전 항목
