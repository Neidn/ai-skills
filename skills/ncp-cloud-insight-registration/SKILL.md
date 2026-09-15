---
name: ncp-cloud-insight-registration
description: >
  NCP(Naver Cloud Platform)의 Server, Load Balancer, Cloud DB 등 주요 리소스를
  Cloud Insight 모니터링 대상으로 등록하는 절차를 안내한다. "Cloud Insight 등록",
  "모니터링 대상 등록", "NCP 모니터링 설정", "상세 모니터링 신청"처럼 리소스를
  Cloud Insight에서 보이게 만드는 작업 요청에 사용한다. 알람 규칙·알림 채널(이메일/SMS)
  설정은 범위 밖이며, 모니터링 대상으로 등록하는 것까지만 다룬다.
metadata:
  author: neidn
  version: "1.0"
---

# NCP Cloud Insight 등록

NCP 리소스(Server / LB / DB)를 Cloud Insight 모니터링 대상으로 등록하는 절차를
**사전조건 확인 → 리소스 유형별 등록 → 검수** 순서로 안내한다.

## 범위

- **포함**: Cloud Insight 사용 신청, 리소스별 모니터링 대상 등록, 상세 모니터링(Extended
  Metric) 신청
- **제외**: 알람 규칙(Event Rule), 알림 채널(이메일·SMS·Webhook) 설정, 대시보드 구성.
  이건 등록이 끝난 뒤의 별도 작업이므로 이 스킬로 다루지 않는다. 필요하면 사용자에게
  별도 요청인지 먼저 확인한다.

## 워크플로

### 1. 대상 확정

등록하려는 리소스 목록(리소스 유형·이름·리전)을 먼저 확인한다. 목록이 없으면
추측하지 말고 사용자에게 묻는다.

### 2. 사전조건 확인

`references/registration-steps.md`의 "사전조건" 절을 읽는다. 최소한 다음을 확인한다.

- Cloud Insight 서비스 사용 신청이 되어 있는지 (콘솔 Management & Governance ▸
  Cloud Insight 최초 진입 시 신청 필요)
- 등록 작업을 수행할 계정에 Cloud Insight 권한이 있는지 (Sub Account라면 권한 범위 확인)

이 스킬은 **VPC 환경만** 다룬다. Classic 환경 리소스는 범위 밖이다.

### 3. 리소스 유형별 등록

`references/registration-steps.md`에서 대상 리소스 유형(Server / Load Balancer /
Cloud DB) 절만 읽고 그대로 따른다. **Server만** 상세 모니터링 활성화가 필요하고,
LB·Cloud DB 같은 관리형 서비스는 생성과 동시에 등록되므로 별도 신청 단계가 없다 —
있는 것처럼 안내하지 않는다. 절차 중 **⚠ 확인 필요** 표시가 있는 항목은 콘솔에서
실제로 확인한 뒤 진행하고, 문서와 다르면 그 자리에서 사용자에게 알린다.

### 4. 검수

- [ ] 등록하려던 리소스가 모두 Cloud Insight 대시보드/Configuration에 나타나는가
- [ ] Server라면 System Metric뿐 아니라 필요한 Extended Metric(상세 모니터링)까지
      수집되는가
- [ ] 등록 누락된 리소스가 있다면 원인(권한 부족 / 상세 모니터링 미신청 / 환경 불일치)을
      함께 보고하는가
- [ ] **추측하거나 콘솔에서 재확인이 필요했던 단계를 사용자에게 명시했는가**

### 5. 전달

등록 결과(성공/실패 리소스 목록)와 함께, 절차 중 **⚠로 표시되어 있었거나 이번에
새로 확인된 내용**을 정리해서 보고한다. 새로 확인된 내용은
`references/registration-steps.md`에 반영할지 사용자에게 제안한다 (이 스킬은 이렇게
보강된다).

## 하지 말 것

- 콘솔 메뉴 경로나 절차를 **지어내지 않는다.** 확인 안 된 단계는 ⚠로 남기고 사용자
  확인을 받는다.
- 등록 절차에 알람 규칙·알림 채널 설정을 임의로 끼워 넣지 않는다. 범위 밖이다.
- API 키·Sub Account 인증정보를 문서나 로그에 남기지 않는다.

## 레퍼런스

- `references/registration-steps.md` — 사전조건, 리소스 유형별(Server/LB/DB) 등록
  절차, 검증 상태
