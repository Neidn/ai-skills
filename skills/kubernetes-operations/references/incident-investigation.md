# 장애 조사 절차

알람이나 장애 보고를 받고 원인을 찾을 때 읽는다. 조사는 조회 명령만으로 한다.
조치가 필요해지면 SKILL.md의 승인 워크플로로 넘어간다.

클러스터 밖 정보(외부 LB 헬스, 감사 로그, 메트릭 이력, 중앙 로그, 노드 내부)는 환경
프로필의 `platform_hooks`에 적힌 방법으로만 조회한다. 비어 있으면 그 항목은
"미확인"으로 적고, 도구를 추측해서 호출하지 않는다.

## 조사 원칙

- 근거(값·상태·로그 줄)를 남긴다. 확인하지 못한 것은 "미확인"으로 적는다.
  **확인한 것과 추정한 것을 구분해서 쓴다.**
- 숫자가 비슷하다는 이유만으로 대상을 확정하지 않는다. 같은 알람의 이전 조사에서
  확정한 원인이 있으면 우선 근거로 쓰되, 그 원인이 지금도 그대로인지 직접 다시 확인한다.
- 설정은 일부가 아니라 실제 적용된 것을 본다. 매니페스트 파일이나 Helm values가 아니라
  `kubectl get <리소스> -o yaml`로 클러스터에 들어간 값을, ConfigMap은 파드가 실제로
  마운트한 버전인지(파드 생성 시각 vs ConfigMap 변경 시각)를 확인한다.
- 이름으로 구성을 추정하지 않는다. 이미지 태그·리소스 이름에 어떤 단어가 있어도 실제
  동작은 스펙·로그로 확인한다.
- 알람 수치를 `df`·`top` 값과 숫자로 맞춰 대상을 고르지 않는다. 알람 설정 자체가 틀린
  경우가 흔하다.
- 조사 중 발견한 다른 문제(여유 부족한 다른 볼륨, 재시작이 잦은 다른 파드)는 "무관"으로
  넘기지 말고 원인을 확인해 별도로 보고한다.

## 1. 대상 확정

1. 알람의 대상 식별자를 쿠버네티스 리소스로 바꾼다. 모니터링 도구의 식별자(컨테이너
   ID, 앱 이름, 에이전트 ID)는 파드·노드 이름과 다를 수 있다.
   - 프로필 `platform_hooks.alert_mapping`이 있으면 그 규칙을 쓴다.
   - 컨테이너 ID만 있으면 `namespaces_in_scope` 범위에서 파드의
     `status.containerStatuses[].containerID`와 대조한다. 전체 클러스터를 무차별로
     훑지 않는다.
   - 끝까지 못 찾으면 "대상 미확정"으로 적고 알람 본문으로 범위를 한정한다.
2. URL·서비스 알람은 진입점부터 따라간다: 외부 LB → Ingress(또는 Gateway) →
   Service → Endpoints/EndpointSlice → 파드 → 컨테이너. 프로필 `services[].flow`가
   있으면 거기서 시작한다.
3. 확정한 대상(클러스터 컨텍스트, 네임스페이스, 리소스)을 첫 보고에 적고 조사가 끝날
   때까지 바꾸지 않는다. 바꿔야 하면 사유를 적는다. 이전 조사의 대상과 다르면 그
   사실도 적는다.
4. 결과에는 명령마다 대상(컨텍스트/네임스페이스/리소스)을 함께 적는다.

## 2. 증상별 확인 순서

| 증상 | 확인 순서 |
|---|---|
| 서비스 5xx·타임아웃 | 외부 LB 헬스(`lb_health`) → Ingress 컨트롤러 로그(상태 코드, upstream) → Service 셀렉터와 Endpoints가 비었는지 → 파드 Ready·readiness 실패 이벤트 → 앱 로그 → 클러스터 밖 의존성(`services[].dependencies`) |
| CrashLoopBackOff | `describe pod`의 `lastState`(reason, exit code) → `logs --previous` → 참조하는 ConfigMap·Secret **키 존재 여부**(값은 보지 않음) → `rollout history`로 직전 변경 → 리소스 limits |
| OOMKilled·메모리 | `lastState.terminated.reason` → limits 대비 `top pod` → 노드 `MemoryPressure` → 장애 시각과 `schedules` 대조 |
| Pending | 이벤트의 `FailedScheduling` 사유 → 노드 allocatable 대비 requests 합 → taint/toleration, nodeSelector/affinity → PVC가 Pending인지. `FailedScheduling` 이벤트도 `PodScheduled` 컨디션도 없으면 스케줄러가 시도하지 못한 것이다 — 스케줄 가능한 노드 수와 스케줄러 상태부터 본다 |
| ImagePullBackOff | 이벤트 메시지 → 이미지 이름·태그 → `imagePullSecrets` **이름** 존재 여부 → 레지스트리 접근 경로 |
| replicas가 갑자기 줄거나 0 | 아래 3. 변경 이력의 `managedFields` → HPA 상태(`describe hpa`) → GitOps·배포 도구의 동기화 기록 |
| 노드 NotReady | 노드 conditions와 이벤트 → 같은 노드풀의 다른 노드와 비교 → 노드에 있던 파드의 재배치 상태 → 노드 내부는 `node_access`. 노드 재기동·교체는 플랫폼 작업이라 안내만 한다 |
| 노드 디스크·ephemeral-storage | 노드 `DiskPressure`, eviction 이벤트 → 어떤 파드가 쫓겨났는지 → 이미지·컨테이너 로그 누적 여부(`node_access`) |
| PVC Pending | PVC 이벤트의 `FailedBinding`·`ProvisioningFailed` 메시지 → `storageClassName`과 기본 StorageClass 존재 여부 → CSI 드라이버 상태 |
| PVC 용량 부족 | PVC 요청 용량과 StorageClass `allowVolumeExpansion` → 사용률은 메트릭(`metrics`) 우선, 없으면 컨테이너 안 `df`(exec라 승인 필요) → 증가 추세로 남은 기간 추정 |
| LB·Ingress 경유만 실패 | 직접 접근(port-forward, 대상이 민감하면 승인)과 경유 접근 비교 → 각 홉의 TLS(SNI, 기본 인증서, TLS Secret **이름**) → 헬스체크 경로 → NetworkPolicy·보안그룹 |

### 컨테이너 안 디스크를 볼 때 (exec 승인 후)

1. 최상위의 일반 파일부터 본다(`ls -la <경로>`). 하위 디렉터리별 `du`만 보면 최상위
   대형 파일을 놓친다.
2. `du -ah --max-depth=1 <경로>`로 파일과 디렉터리를 한 번에 보고, 정렬은 결과를 받은
   뒤에 한다.
3. `df`와 하위 합계가 맞지 않으면 1·2단계로 실제 파일을 먼저 찾는다. 근거 없이 "삭제된
   파일을 프로세스가 잡고 있다"고 추정하지 않는다.
4. 이전에 지목된 파일은 정확한 경로로 지금도 있는지 다시 확인한다.

## 3. 변경 이력 대조

**클러스터 안**

- 이벤트: `kubectl events -n <ns>`. 이벤트는 기본 1시간 정도만 보존되므로 늦게 보면
  사라져 있다. 없다고 "변경 없음"이 아니다.
- 롤아웃: `kubectl rollout history <워크로드> -n <ns>`
- 누가 바꿨는지: `kubectl get <워크로드> -n <ns> --show-managed-fields -o yaml`에서
  해당 필드(예: `f:spec` 아래 `f:replicas`)를 가진 항목의 `manager`, `operation`,
  `subresource`, `time`을 **함께** 본다. manager 이름만으로는 구분이 안 되는 경우가 있다.
  kubectl v1.34에서 확인한 값은 다음과 같다.

  | 변경 | manager | operation | subresource |
  |---|---|---|---|
  | `kubectl scale` | `kubectl` | Update | `scale` |
  | `kubectl apply --server-side` | `kubectl` | Apply | 없음 |
  | `kubectl apply` (client-side) | `kubectl-client-side-apply` | Update | 없음 |
  | `kubectl patch` | `kubectl-patch` | Update | 없음 |
  | `kubectl rollout restart` | `kubectl-rollout` (`restartedAt` 어노테이션) | Update | 없음 |
  | `kubectl set image` 등 | `kubectl-set` | Update | 없음 |

  컨트롤러(HPA·Helm·GitOps 도구)와 다른 버전의 kubectl은 이름이 다를 수 있다. 예:
  배포판에 따라 컨트롤러 manager가 `kube-controller-manager`가 아닐 수 있다. 표에 없는
  이름은 그대로 근거로 적고 추정으로 바꾸지 않는다. 각 manager는 마지막 변경 시각만
  남으므로 이전 이력은 `rollout history`와 이벤트로 보충한다.

**클러스터 밖**

- 노드풀 변경, LB·보안그룹 변경, 스토리지 증설 같은 플랫폼 변경은 `audit_log`로 장애
  시각 앞뒤를 대조한다.
- 감사 로그에는 컨테이너 내부 변경(파일 생성 등)이 남지 않는다. 감사 로그에 없다고
  "변경 없음"으로 단정하지 않는다.

## 4. 안을 볼 수 없을 때

권한 부족, 파드가 이미 사라짐, 노드 접근 불가처럼 직접 볼 수 없어도 "미확인"으로
끝내지 않는다. 다음 근거를 찾는다.

- 메트릭 이력(`metrics`): 메모리·CPU·디스크 IO·재시작 횟수 추이
- 중앙 로그(`logs`): 사라진 파드의 마지막 로그
- 같은 역할의 다른 파드·노드와 비교
- 장애 시각과 `services[].schedules`(배치·백업)가 겹치는지
- 사용자에게 화면·로그 캡처 요청

권한 부족은 `kubectl auth can-i <verb> <resource> -n <ns>`로 확인하고, 필요한 권한을
안내한다. 권한을 직접 바꾸지 않는다.

## 5. 복구 후 사후 분석 (필수)

서비스가 복구됐다고 바로 종결하지 않는다.

- 재시작된 파드: `logs --previous`, `lastState`, 재시작 횟수, 이벤트를 시간순으로 정리
- 노드 문제였으면: 노드 conditions 이력, 플랫폼 로그(`node_access`, `audit_log`)
- 앱 런타임 로그(GC 로그 등)가 없어서 원인을 못 좁혔으면 활성화를 권고
- `services[].required_components`가 **모두** Ready인지 확인. 사이드카, 별도
  워크로드로 뜨는 구성요소, CronJob의 다음 실행도 포함
- 알람이 다시 오지 않아도 일정 시간 뒤 다시 확인한다. 사람이 조치한 경우도 마찬가지다.
  예약 실행 수단이 있으면 재확인을 예약하고, 없으면 재확인 시각을 보고에 적는다.

## 6. 결과 보고

다음 순서로 쓴다.

1. **원인** — 한두 문장. 확정인지 추정인지 표시
2. **근거 표**

   | 확인 항목 | 대상(컨텍스트/네임스페이스/리소스) | 결과 | 확인/추정 |
   |---|---|---|---|

3. **해결 방안** — 조치가 필요하면 SKILL.md의 조치계획 양식으로
4. **재발 방지**
5. **미확인 항목** — 무엇이 없어서 못 봤는지(권한, 프로필 항목, 보존 기간 만료 등)

다른 엔지니어의 분석과 결론이 다르면, 다른 지점과 각자의 근거를 대조표로 남긴다.
보내기 전에 SKILL.md의 "보고·발송 전 검수"를 적용한다.
