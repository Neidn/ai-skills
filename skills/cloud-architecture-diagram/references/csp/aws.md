# AWS 구성도 레퍼런스

> 검증 상태: **부분 검증**. NCP만큼 실환경 검증이 되어 있지 않다.
> 사용하면서 틀린 부분을 발견하면 그때 고친다.

## 1. 리소스 → kind 매핑

| AWS 리소스 | kind | 비고 |
|---|---|---|
| VPC | `vpc` | 리전 단위 |
| Subnet | `public` / `private` | 판단 기준은 아래 참고 |
| Availability Zone | `zone` | 서브넷을 AZ별로 묶을 때 |
| EC2 | `server` | |
| ALB / NLB | `lb` | 여러 AZ 서브넷에 걸친다 |
| NAT Gateway | `gateway` | 퍼블릭 서브넷, AZ당 하나 |
| Internet Gateway | — | 노드 대신 인터넷 연결선으로 |
| RDS | `db` | Multi-AZ는 Primary/Standby 각각 노드 |
| ElastiCache | `cache` | |
| S3 | `storage` | VPC 밖. Region 그룹 직계 자식 |
| EFS | `storage` | 마운트 타깃이 서브넷에 위치 |
| EKS | `k8s` | 클러스터 그룹 → 노드그룹 하위 그룹 |
| Lambda | `server` | VPC 연결 여부에 따라 위치가 달라짐 |
| Transit Gateway / VGW | `gateway` | |
| Direct Connect | `network` | 온프레미스 그룹과 edge |
| WAF / Shield | `security` | |
| CloudWatch | `monitoring` | |

## 2. 자산 수집

```bash
aws ec2 describe-vpcs \
  --query 'Vpcs[].{id:VpcId,cidr:CidrBlock,name:Tags[?Key==`Name`]|[0].Value}'

aws ec2 describe-subnets \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,cidr:CidrBlock,az:AvailabilityZone,public:MapPublicIpOnLaunch}'

aws ec2 describe-instances \
  --query 'Reservations[].Instances[].{id:InstanceId,type:InstanceType,subnet:SubnetId,state:State.Name,name:Tags[?Key==`Name`]|[0].Value}'

aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[].{name:LoadBalancerName,scheme:Scheme,subnets:AvailabilityZones[].SubnetId}'

aws rds describe-db-instances \
  --query 'DBInstances[].{id:DBInstanceIdentifier,engine:Engine,multiaz:MultiAZ,subnets:DBSubnetGroup.Subnets[].SubnetIdentifier}'
```

## 3. 구성도에서 틀리기 쉬운 것

### 퍼블릭/프라이빗은 라우팅 테이블이 정한다

`MapPublicIpOnLaunch`는 힌트일 뿐 정답이 아니다. **0.0.0.0/0 → IGW 라우트가 있는
서브넷이 퍼블릭**이다. 정확히 그리려면 라우팅 테이블 연결을 확인한다.

```bash
aws ec2 describe-route-tables \
  --query 'RouteTables[].{id:RouteTableId,subnets:Associations[].SubnetId,routes:Routes[].{d:DestinationCidrBlock,gw:GatewayId}}'
```

### AZ 구조를 뭉개지 않는다

Multi-AZ 구성인데 서브넷을 하나로 합쳐 그리면 이중화 여부가 사라진다. AZ가 2개면
서브넷도 용도별로 2개씩 그린다. AZ를 `zone` 그룹으로 묶고 그 안에 서브넷을 두는
방식이 이중화를 가장 잘 보여준다.

### LB는 여러 서브넷에 걸친다

ALB/NLB는 AZ별 서브넷에 ENI를 만든다. 인벤토리 구조상 노드는 부모가 하나뿐이므로,
LB는 VPC 직계 자식으로 두고 각 서브넷과 edge로 연결하거나, 대표 서브넷 하나에 두고
라벨에 `2 AZ`를 적는다. 후자가 그림이 단순하다.

### VPC 밖 서비스

S3, DynamoDB, Route 53, CloudFront는 VPC 내부가 아니다. VPC Endpoint를 쓰는 경우에만
서브넷 안에 엔드포인트 노드를 두고, 서비스 자체는 VPC 밖에 그린다.

### 계정 경계

멀티 계정 구성이면 계정이 VPC보다 상위 경계다. Region 그룹 아래에 계정 그룹을 두거나,
계정별로 최상위 그룹을 나눈다. 계정 번호는 라벨에 넣되 전체를 적지 말고 뒤 4자리만 쓴다.

## 4. 라벨 표기 관례

```
EC2       web-01 (i-0a1b…)
          t3.medium · Amazon Linux 2023

서브넷    prod-public-2a (10.0.1.0/24)
          ap-northeast-2a

RDS       prod-mysql (Primary)
          db.r6g.large · Multi-AZ
```

- AZ는 `ap-northeast-2a` 형식
- 리소스 ID는 전체를 쓰지 말고 앞 6자 정도만
- 태그 `Name`이 있으면 그것을 1번째 줄로
