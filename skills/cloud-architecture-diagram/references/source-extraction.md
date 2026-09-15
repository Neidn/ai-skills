# 자산 수집 경로별 요령

인벤토리 JSON을 채우기 위해 원본을 뽑는 방법. 명령의 정확한 옵션명은 CLI 버전마다
다르므로, 실행 전 `--help`로 확인하고 결과가 비면 리전 코드부터 의심한다.

## 1. Terraform state — 가장 정확

IaC로 관리되는 환경이면 이게 1순위다. 실제 배포 상태와 일치하고 관계까지 들어 있다.

```bash
terraform show -json > tfstate.json

# 리소스 타입별 개수 파악
jq -r '.values.root_module.resources[].type' tfstate.json | sort | uniq -c

# 서버 목록
jq -r '.values.root_module.resources[]
       | select(.type|test("server|instance"))
       | [.name, .values.name, .values.subnet_no // .values.subnet_id] | @tsv' tfstate.json
```

`depends_on`과 참조 관계가 그대로 `edges`가 된다.

## 2. NCP CLI

```bash
# 네트워크 계층
ncloud vpc getVpcList --regionCode KR
ncloud vpc getSubnetList --regionCode KR --vpcNo <VPC_NO>
ncloud vpc getNatGatewayInstanceList --regionCode KR

# 컴퓨트
ncloud vserver getServerInstanceList --regionCode KR

# 로드밸런서
ncloud vloadbalancer getLoadBalancerInstanceList --regionCode KR

# ACG (보안 정책은 그림에 직접 안 그리지만 연결 관계 추론에 쓴다)
ncloud vserver getAccessControlGroupList --regionCode KR
ncloud vserver getAccessControlGroupRuleList --accessControlGroupNo <ACG_NO>
```

- 서브넷 목록에서 `subnetType`(PUBLIC/PRIVATE)을 그대로 `kind`에 매핑한다.
- ACG 인바운드 규칙의 출발지/포트가 `edges`의 근거가 된다. 0.0.0.0/0 인바운드가 있는
  리소스는 인터넷과 연결한다.
- 콘솔에서 CSV로 내려받은 자산 목록이 있으면 CLI보다 그쪽이 빠르다.

## 3. AWS CLI

```bash
aws ec2 describe-vpcs --query 'Vpcs[].{id:VpcId,cidr:CidrBlock,name:Tags[?Key==`Name`]|[0].Value}'
aws ec2 describe-subnets --query 'Subnets[].{id:SubnetId,vpc:VpcId,cidr:CidrBlock,az:AvailabilityZone,public:MapPublicIpOnLaunch}'
aws ec2 describe-instances --query 'Reservations[].Instances[].{id:InstanceId,type:InstanceType,subnet:SubnetId,name:Tags[?Key==`Name`]|[0].Value}'
aws elbv2 describe-load-balancers --query 'LoadBalancers[].{name:LoadBalancerName,scheme:Scheme,subnets:AvailabilityZones[].SubnetId}'
aws rds describe-db-instances --query 'DBInstances[].{id:DBInstanceIdentifier,engine:Engine,subnet:DBSubnetGroup.Subnets[].SubnetIdentifier,multiaz:MultiAZ}'
```

`MapPublicIpOnLaunch`가 true면 `kind: "public"`, 아니면 `private`로 본다.
LB의 `Scheme`이 `internet-facing`이면 인터넷 노드와 연결한다.

## 4. 사람이 준 표 / 스크린샷 / 말로 된 설명

MSP 실무에서 가장 흔한 입력이다. 이 경우 **추측한 부분을 반드시 분리해서 보고한다.**

- 자산 엑셀·CSV: 헤더를 먼저 확인하고 이름/사양/IP/용도 컬럼을 매핑한다.
- 서브넷 정보가 없으면 IP 대역으로 역추정하되, 추정임을 명시한다.
- 연결 관계가 안 적혀 있으면 일반적인 3-tier를 가정하지 말고 물어본다.
  틀린 연결선은 없는 연결선보다 나쁘다.

## 5. 수집 후 공통 정리

1. 리소스마다 `id` 슬러그를 부여한다 (`web01`, `sbn_db`).
2. 서브넷 → VPC → 리전 순으로 부모를 확정한다.
3. 부모를 못 찾은 리소스는 버리지 말고 "미분류" 그룹에 모아 사용자에게 확인받는다.
4. 종료·중지 상태 리소스는 제외하거나 라벨에 `(중지)`를 붙인다. 조용히 섞지 않는다.
