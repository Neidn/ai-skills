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
| `delete` | 단일 리소스든 라벨 셀렉터 기반이든 동일. 셀렉터 기반이면 영향받는 리소스 목록을 먼저 `get`으로 보여준다 |
| `patch`, `edit`, `set` | 기존 리소스 필드 변경. `edit`은 대화형이라 이 스킬(비대화형 실행) 환경에서는 대신 `patch`나 `apply`로 동일 변경을 수행하고 승인받는 편이 낫다 |
| `scale`, `autoscale` | replica 수 변경 |
| `label`, `annotate` | 조회 모드가 없다 — 인자 없이 실행해도 항상 쓰기 동작이므로 명령 자체를 승인 필요로 취급 |
| `cordon`, `uncordon`, `drain` | 노드 스케줄링 상태 변경. `drain`은 여러 파드를 동시에 축출하므로 영향 범위를 특히 꼼꼼히 보여준다 |
| `taint` | 노드 테인트 변경 |
| `rollout restart`, `rollout undo`, `rollout pause`, `rollout resume` | `rollout`의 상태 변경 서브커맨드만. `status`/`history`는 조회 |
| `exec` | 컨테이너 내부에서 명령 실행. 읽기 전용처럼 보이는 명령(`exec -- cat file`)이어도 컨테이너 프로세스에 개입하는 행위라 일괄 승인 필요로 취급 |
| `cp` | 파일을 컨테이너 안팎으로 복사. 컨테이너 파일시스템을 바꿀 수 있음 |
| `auth reconcile` | RBAC 규칙을 실제로 생성/갱신함 (`auth can-i`와 혼동 주의) |

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
- **레이블 셀렉터 기반 대량 작업** (`delete -l app=foo`, `label -l ...`) — 몇 개
  리소스에 영향을 주는지 미리 `get -l app=foo`로 확인해서 승인 요청에 개수와
  목록을 포함한다. "몇 개인지 모른 채" 승인받지 않는다
