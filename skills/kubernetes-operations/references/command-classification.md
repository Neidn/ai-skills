# kubectl 명령 분류

이 스킬에서 "조회"와 "승인 필요"를 나누는 기준은 **클러스터 상태를 바꾸는가,
또는 민감정보를 노출하는가**다. 읽기 전용 플래그(`--dry-run`)가 붙어도 실제로
쓰기 동작을 하면 승인 필요로 취급한다.

## 조회 — 바로 실행

| 명령 | 비고 |
|---|---|
| `get` | `secret`/`secrets` 리소스는 제외 (아래 "승인 필요 — 민감정보" 참고) |
| `describe` | Secret을 대상으로 해도 값 자체는 마스킹되어 나오므로 조회로 취급 |
| `logs` | |
| `top` (node/pod) | |
| `explain` | 스키마 설명, 클러스터 상태와 무관 |
| `api-resources`, `api-versions`, `version` | |
| `cluster-info` | |
| `events` | |
| `diff` | 실제로 적용하지 않고 차이만 보여줌 |
| `auth can-i` | 권한 확인 질의일 뿐 실제 권한을 바꾸지 않음 (`auth reconcile`과 다름) |
| `rollout status`, `rollout history` | `rollout`의 조회 서브커맨드만 해당 |
| `config current-context`, `config get-contexts` | 컨텍스트 확인용 |

## 승인 필요 — 클러스터 상태 변경

| 명령 | 비고 |
|---|---|
| `apply`, `create`, `replace` | 리소스 생성/치환 |
| `delete` | 이름을 명시한 단일 리소스만. Namespace·PVC·PV·CRD 등과 셀렉터·`--all`·디렉터리 단위 삭제는 아래 "승인해도 실행 안 함" |
| `patch`, `edit`, `set` | 기존 리소스 필드 변경. `edit`은 대화형이라 이 스킬(비대화형 실행) 환경에서는 대신 `patch`나 `apply`로 동일 변경을 수행하고 승인받는 편이 낫다 |
| `scale`, `autoscale` | replica 수 변경 |
| `label`, `annotate` | 조회 모드가 없다 — 인자 없이 실행해도 항상 쓰기 동작이므로 명령 자체를 승인 필요로 취급 |
| `cordon`, `uncordon`, `drain` | 노드 스케줄링 상태 변경. `drain`은 여러 파드를 동시에 축출하므로 영향 범위를 특히 꼼꼼히 보여준다 |
| `taint` | 노드 테인트 변경 |
| `rollout restart`, `rollout undo`, `rollout pause`, `rollout resume` | `rollout`의 상태 변경 서브커맨드만. `status`/`history`는 조회 |
| `exec` | 컨테이너 내부에서 명령 실행. 읽기 전용처럼 보이는 명령(`exec -- cat file`)이어도 컨테이너 프로세스에 개입하는 행위라 일괄 승인 필요로 취급 |
| `cp` | 파일을 컨테이너 안팎으로 복사. 컨테이너 파일시스템을 바꿀 수 있음 |

## 승인 필요 — 민감정보 노출

| 명령 | 비고 |
|---|---|
| `get secret`, `get secrets` (모든 출력 형식) | 테이블 출력은 값을 안 보여주지만, 어떤 Secret이 존재하는지 자체도 민감할 수 있어 통째로 승인 필요로 묶는다. `-o yaml`/`-o json`/`-o jsonpath=...`처럼 `data` 필드가 base64로 노출되는 형식은 특히 주의 — base64는 암호화가 아니라 인코딩이라 즉시 디코딩 가능하다는 점을 승인 요청 시 같이 안내한다 |
| `describe secret` | 값 자체는 마스킹되어 나오므로 조회로 취급해도 되지만, 어떤 키가 존재하는지는 노출된다. 팀 정책에 따라 승인 필요로 올릴 수도 있음 — 애매하면 사용자에게 물어본다 |

## 승인 필요 — 파괴적 옵션

일반 `delete`보다 되돌리기 어렵거나 강제로 종료시키는 옵션은 별도로 강조해서
승인받는다. "delete니까 이미 승인 필요 목록에 있다"로 넘기지 말고, 이 옵션들이
왜 더 위험한지(정상 종료 절차 생략, 즉시 강제 종료) 승인 요청에 명시한다.

| 옵션/명령 | 비고 |
|---|---|
| `delete --force --grace-period=0` | 정상 종료(SIGTERM, PreStop 훅)를 건너뛰고 즉시 삭제 |
| `delete pod <name> --grace-period=0 --force` | 위와 동일, Pod 대상 |
| `kubectl exec ... -- kill` 등으로 프로세스 강제 종료 | `exec` 자체가 이미 승인 필요지만, 강제 종료 목적이면 승인 요청에 그 의도를 명시 |
| Eviction API를 통한 축출 (`kubectl drain`이 내부적으로 사용) | `drain` 항목과 동일하게 취급 |

## 승인해도 실행 안 함

되돌릴 수 없거나 영향 범위를 통제할 수 없는 작업. 승인을 받아도 실행하지 않고,
거절 사유와 함께 사용자가 직접 하도록 안내한다. 조치계획에도 넣지 않는다.

| 명령 | 비고 |
|---|---|
| `delete namespace`/`ns` | 안의 모든 리소스와 데이터가 함께 지워진다 |
| `delete pvc`, `delete pv` | reclaimPolicy가 Delete면 실제 볼륨 데이터까지 사라진다 |
| `delete crd` | 해당 종류의 커스텀 리소스가 전부 지워진다 |
| `delete storageclass`, `delete node` | 클러스터 범위 리소스 |
| `delete -l <셀렉터>`, `delete --all`, `delete -f <디렉터리>` | 몇 개가 지워질지 실행 시점에 바뀔 수 있다 |
| Role·ClusterRole·RoleBinding·ClusterRoleBinding 대상 `apply`/`create`/`patch`/`edit`/`replace`/`delete` | 권한 변경 |
| `auth reconcile` | RBAC 규칙을 실제로 생성/갱신함 (`auth can-i`와 혼동 주의) |
| 클러스터·노드·클러스터 구성요소(CNI·CSI·Ingress 컨트롤러 등) 버전 변경 | 보통 플랫폼 CLI·콘솔 작업이지만, kubectl·Helm으로 하는 경우도 같다 |
| `exec`로 디렉터리·와일드카드 통삭제(`rm -rf <dir>`, `rm *.log`) | 파일 삭제는 절대경로로 명시한 파일 1개당 명령 1개만 승인 대상 |

프로필 `approval.extra_forbidden`에 적힌 작업도 이 등급으로 취급한다.

## Helm

Helm은 릴리스 정보를 대상 네임스페이스의 Secret(`helm.sh/release.v1` 타입)에
저장한다. 그래서 `helm list`·`status`·`history` 같은 조회도 Secret 읽기 권한이
필요하다. Secret 권한이 없는 읽기 전용 계정에서는 실패하므로, 그때는
`kubectl get <종류> -l app.kubernetes.io/managed-by=Helm`으로 대신 본다.
`--kube-context`, `-n` 같은 전역 플래그는 kubectl과 마찬가지로 동사 뒤에 붙인다.

| 분류 | 명령 | 비고 |
|---|---|---|
| 조회 | `list`/`ls`, `status`, `history`, `get notes`, `get metadata`, `show`, `template`, `lint`, `search`, `repo list`, `version` | `template`·`lint`는 로컬 렌더링 |
| 승인 필요 (민감정보) | `get values`, `get manifest`, `get all`, `get hooks` | values에 비밀번호가 들어 있거나 매니페스트에 Secret이 포함될 수 있다. 꼭 필요한 키만, 마스킹해서 보여 준다 |
| 승인 필요 | `upgrade`, `install`, `upgrade --install`, `rollback`, `test` | `test`는 테스트 파드를 만든다. 미리보기는 `upgrade --dry-run=server`나 diff 플러그인 결과를 붙인다 |
| 승인 필요 (파괴적) | `upgrade --force` | 리소스를 지우고 다시 만들 수 있다. 일반 `upgrade`와 구분해 이유를 승인 요청에 적는다 |
| 승인 필요 (로컬 환경) | `repo add`/`update`/`remove`, `plugin install`/`update` | 클러스터는 안 바꾸지만 외부 저장소에 접근하거나 외부 코드를 설치한다 |
| 승인해도 실행 안 함 | `uninstall`/`delete`/`del`/`un` | 릴리스의 리소스가 함께 지워진다. PVC는 남는 경우가 많지만 차트에 따라 다르다 |
| 승인해도 실행 안 함 | 클러스터 구성요소 릴리스(CNI·CSI·Ingress 컨트롤러·cert-manager 등)의 `upgrade` | 위 "버전 변경"과 같다. 애플리케이션 릴리스의 `upgrade`는 승인 필요 |

## 애매한 케이스

- **`apply/create --dry-run=client`** — 클라이언트에서만 검증, 서버에 아무 요청도
  안 감. 조회로 취급해도 된다
- **`apply/create --dry-run=server`** — 서버가 검증은 하지만 저장은 안 함(admission
  webhook까지 태움). 실제 변경은 없으므로 조회로 취급하되, 이 결과를 승인 요청 시
  "미리보기"로 활용하면 좋다 (`references`의 승인 워크플로 2단계 참고)
- **`port-forward`** — 클러스터 상태는 안 바꾸지만 로컬 포트를 열어 클러스터
  내부 서비스에 직접 네트워크 접근을 만든다. 상태 변경은 아니라서 "승인 필요"
  기본 목록엔 없지만, 접근 자체가 민감할 수 있으니 대상 서비스가 민감하면
  (예: DB, 내부 관리 콘솔) 승인을 받는 편이 낫다 — 애매하면 물어본다
- **`kubectl run`** — 사실상 `create`와 동일 (Pod 생성). 승인 필요
- **`kubectl proxy`** — API 서버로의 로컬 프록시를 연다. `port-forward`와 같은
  기준으로 판단
- **레이블 셀렉터 기반 대량 작업** (`label -l ...`, `annotate -l ...`) — 몇 개
  리소스에 영향을 주는지 미리 `get -l app=foo`로 확인해서 승인 요청에 개수와
  목록을 포함한다. "몇 개인지 모른 채" 승인받지 않는다. 셀렉터 기반 `delete`는
  "승인해도 실행 안 함"이다
- **`exec`로 파일 삭제** — 절대경로로 명시한 파일 1개당 삭제 명령 1개만 승인 대상이다.
  삭제 전 `ls -la <정확한 경로>`로 존재를 확인하고, 계획의 경로와 실제 명령의 경로가
  같은지 대조한다
