# 환경 프로필

스킬 본문에는 고객사·플랫폼별 값이 들어 있지 않다. 클러스터 접속 방법, 승인자,
서비스 구성, 플랫폼 기능(LB 헬스·감사 로그·메트릭) 조회 방법은 환경 프로필 하나에
모아 두고, 스킬은 실행할 때 이 파일에서 값을 읽는다. 고객사나 도구가 바뀌면
프로필만 바꾼다.

## 찾는 순서

1. 환경변수 `K8S_OPS_PROFILE`이 가리키는 파일
2. 작업 디렉터리의 `k8s-ops-profile.yaml`

여러 고객사를 다루면 고객사마다 파일을 따로 두고 `K8S_OPS_PROFILE`로 바꿔 가리킨다.
프로필에는 내부 구성 정보가 들어가므로 공개 레포에 커밋하지 않는다.

## 프로필이 없거나 비어 있을 때

| 상황 | 동작 |
|---|---|
| 프로필 없음 | 조회는 진행한다. 기본값으로 동작한다: 승인자 = 대화 중인 사용자, 승인 채널 = 이 대화, 금지 목록 = 기본 목록, 환경 = **prod로 간주**. 작업 끝에 프로필 작성을 한 번 제안한다 |
| `clusters[].context`가 비어 있음 | 사용자가 말한 대상과 현재 컨텍스트가 같은지 매번 확인받는다 |
| `approval.*`가 비어 있음 | 위 기본값을 쓴다. 다른 사람이 승인자라면 변경 작업을 진행하지 않고 채워 달라고 한다 |
| [권장] 항목이 비어 있음 | 작업은 진행하고, 그 때문에 확인하지 못한 범위를 결과에 "미확인"으로 적는다 |
| `platform_hooks.*`가 비어 있음 | 해당 조회를 하지 않고 "미확인"으로 적는다. 도구를 추측해서 호출하지 않는다 |

값을 추측하거나 다른 고객사 프로필에서 가져오지 않는다. 조회로 확인할 수 있는 값은
직접 조회해 근거와 함께 채움안을 보여 주고, 조회로 알 수 없는 값만 묻는다.

## 작성 규칙

- 비밀정보(토큰, 키, 비밀번호, kubeconfig 내용)는 값을 쓰지 않는다. 주입한
  **환경변수 이름**이나 파일 경로만 적는다.
- 모르는 값은 비워 두고 `# TODO`를 단다.
- 값을 바꾸면 맨 아래 `변경 이력`에 날짜, 변경자, 내용을 남긴다.

## 양식

`assets/k8s-ops-profile.example.yaml`을 복사해서 쓴다. 각 키의 의미와 [필수]·[권장]
표시는 파일 안 주석에 있다. 주요 묶음은 다음과 같다.

| 묶음 | 담는 것 |
|---|---|
| `profile` | 고객사·환경 식별자 |
| `clusters` | 컨텍스트, prod/stg/dev, kubeconfig 경로·발급 방법, 운영 범위 네임스페이스, 읽기 전용 여부 |
| `approval` | 승인자, 승인 경로, 토큰 규칙, 고객사별 추가 금지 작업 |
| `secrets_env` | 비밀정보의 환경변수 이름 |
| `executor` | 실행 경로와 그 제약(중간 실행 계층 등) |
| `platform_hooks` | LB 헬스, 감사 로그, 메트릭, 중앙 로그, 노드 접근, 알람 매핑, 알림 경로를 얻는 방법 |
| `services` | 서비스별 진입 경로, 워크로드, 재검증 대상, 의존성, 배치 일정, 책임 경계 |
| `known_limits` | 조회 불가 대상, 권한 부족 등 알려진 제약 |

## 작업별 필요 항목

| 항목 | 조회 | 변경 | 장애 조사 |
|---|---|---|---|
| `clusters[].context`, `env` | 필수 | 필수 | 필수 |
| `approval.*` | - | 필수 (없으면 기본값) | - |
| `executor.*` | 선택 | 선택 | 선택 |
| `platform_hooks.*` | - | 선택 | 권장 |
| `services` | - | 권장 (재검증 범위) | 권장 (경로 추적) |
| `known_limits` | 권장 | 권장 | 권장 |

## 값 찾는 방법

| 항목 | 찾는 방법 |
|---|---|
| `clusters[].context` | `kubectl config get-contexts` |
| `clusters[].platform` | `kubectl get nodes -o wide`, 노드의 `spec.providerID`·라벨 |
| `namespaces_in_scope` | `kubectl get ns` 결과를 보여 주고 사용자에게 범위를 확인 |
| `services[].workloads`, `flow` | `kubectl get ingress,svc,deploy,sts,ds -n <ns>`, Ingress 백엔드 → Service 셀렉터 → 워크로드 라벨 대조 |
| `services[].required_components` | 워크로드 목록으로 초안을 만들고 사용자에게 확인 |
| `services[].schedules` | `kubectl get cronjob -A` + 클러스터 밖 배치는 사용자에게 묻는다 |
| `approval.*`, `platform_hooks.*`, `scope_note` | 조회로 알 수 없다. 사용자에게 묻는다 |
| `known_limits` | `kubectl auth can-i --list -n <ns>`로 권한 범위를 확인해 초안 작성 |
