---
name: kubernetes-operations
description: >
  kubectl로 쿠버네티스 클러스터(범용 K8s, NCP Kubernetes Service 포함)를 직접
  조회·운영한다. 조회(get/describe/logs 등)는 즉시 실행하고, 생성·삭제·설정
  변경·스케일링·롤아웃 재시작·exec·Secret 값 조회처럼 클러스터 상태나 민감정보에
  영향을 주는 작업은 실행 전 반드시 사용자 승인을 받는다. "파드 상태 확인해줘",
  "디플로이먼트 스케일 조정", "이 서비스 재시작", "왜 파드가 CrashLoop인지 봐줘",
  "시크릿 값 확인" 같은 요청에 사용한다.
metadata:
  author: neidn
  version: "1.0"
---

# Kubernetes Operations

kubectl로 클러스터를 직접 운영하되, **조회는 자동 실행, 상태를 바꾸거나 민감정보를
노출하는 작업은 실행 전 승인**이 핵심 원칙이다. 대상은 kubectl로 접근 가능한 모든
클러스터(범용 K8s, NCP Kubernetes Service 등)이며, CSP 특유의 절차는 다루지 않는다.

## 0. 시작 전에 — 대상 클러스터 확인

작업을 시작하기 전에 항상 `kubectl config current-context`로 지금 어느 클러스터를
보고 있는지 확인하고, 사용자가 말한 대상과 일치하는지 확인한다. 네임스페이스도
마찬가지로 `-n <namespace>`를 명시하거나 현재 컨텍스트의 기본 네임스페이스를
확인한다. **컨텍스트를 잘못 짚고 실행하는 것이 이 작업에서 가장 흔하고 위험한
실수다** — 특히 여러 클러스터(dev/staging/prod)를 다루는 환경에서는 매 요청마다
확인한다.

## 1. 명령 분류 — 조회 vs 승인 필요

전체 분류표는 `references/command-classification.md`에 있다. 요약하면:

| 분류 | 처리 | 예시 |
|---|---|---|
| **조회** | 바로 실행 | `get`, `describe`, `logs`, `top`, `explain`, `api-resources`, `version`, `cluster-info`, `events`, `diff`, `auth can-i`, `rollout status/history` |
| **승인 필요** | 실행 전 확인 | `apply`, `create`, `delete`, `patch`, `edit`, `replace`, `scale`, `autoscale`, `set`, `label`, `annotate`, `cordon`, `uncordon`, `drain`, `taint`, `exec`, `cp`, `rollout restart/undo/pause/resume` |
| **승인 필요 (민감정보)** | 실행 전 확인 | `get secret -o yaml\|json` 등 Secret 값이 디코딩되어 노출되는 조회 |
| **승인 필요 (파괴적)** | 실행 전 확인, 근거 요구 | `delete --force`, `--grace-period=0`, `evict` |

애매한 명령(`kubectl apply --dry-run=client/server`, `port-forward` 등)은
`references/command-classification.md`의 "애매한 케이스"를 본다.

## 2. 승인 워크플로

"승인 필요"로 분류된 명령은 절대 먼저 실행하고 나중에 알리지 않는다. 실행 전에
다음을 사용자에게 제시하고 명시적 승인을 받는다.

1. **실행할 명령 전문** — 축약하지 않고 그대로
2. **무엇이 바뀌는가** — 대상 리소스, 네임스페이스, 클러스터. 가능하면 실행 전
   `--dry-run=server`나 `kubectl diff`로 실제 변경될 내용을 미리 보여준다
3. **영향 범위** — 몇 개의 파드/리소스에 영향을 주는지, 다운타임이 발생하는지
4. **롤백 방법** — 문제가 생기면 어떻게 되돌리는지 (예: `kubectl rollout undo`,
   삭제 전 `kubectl get -o yaml`로 백업)

승인은 **변경 단위별로** 받는다. 여러 개의 서로 다른 변경을 하나로 뭉쳐 한 번에
승인받지 않는다. 승인 후 실행하고, 실행 결과를 조회 명령으로 재확인한 뒤 보고한다.

이 저장소(ai-skills) 기준으로는 `.claude/settings.json`에 위 "승인 필요" 명령들을
`ask`로 강제하는 권한 규칙도 걸려 있어 이중 안전장치가 있다. **단, 이 규칙은 이
저장소에서 Claude Code를 쓸 때만 적용된다.** 이 스킬만 다른 프로젝트에 설치하면
도구 권한 강제는 없고, 아래 워크플로(승인 요청 후 실행)를 스스로 지키는 것만
안전장치가 된다 — 그러니 도구 권한 설정 유무와 무관하게 이 워크플로를 항상 따른다.

## 3. 하지 말 것

- **승인 없이 "승인 필요" 명령을 실행하지 않는다.** 도구 권한이 자동 허용되어
  있어도 마찬가지다 — 이 스킬의 워크플로가 우선한다.
- `--force`, `--grace-period=0` 같은 강제 옵션을 사용자 확인 없이 쓰지 않는다.
- Secret 값을 채팅에 그대로 노출하지 않는다. 꼭 필요한 키만, 필요하면 마스킹해서
  보여준다.
- 컨텍스트 확인 없이 "일단 실행해보고" 대상을 짐작하지 않는다.
- 여러 리소스를 한 번에 삭제/수정하는 명령(라벨 셀렉터 기반 `delete -l ...` 등)은
  영향받는 리소스 목록을 먼저 `get`으로 보여준 뒤 승인받는다.

## 4. 검수 — 변경 작업 후 확인

- [ ] 실행한 명령이 승인받은 내용과 정확히 일치하는가
- [ ] 변경이 반영됐는지 조회 명령으로 재확인했는가
- [ ] 의도치 않은 다른 리소스에 영향이 없는가
- [ ] 롤백이 필요해질 경우의 방법을 사용자에게 남겼는가

## 레퍼런스

- `references/command-classification.md` — kubectl 서브커맨드별 조회/승인 필요
  상세 분류, 애매한 케이스(`--dry-run`, `port-forward`, `cp` 등) 설명
