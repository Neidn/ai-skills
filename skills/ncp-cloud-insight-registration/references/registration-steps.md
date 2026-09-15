# Cloud Insight 등록 절차 레퍼런스

> 검증 상태: **미검증(초안)**. 공식 문서(guide.ncloud-docs.com)와 공개된 안내를
> 바탕으로 조사했지만, 실제 콘솔에서 단계별로 재현·확인하지는 못했다. ⚠ 표시는
> 운영 환경에서 재확인이 필요한 항목이다. 이 문서를 실제로 써 본 뒤 맞는 부분과
> 틀린 부분을 갱신해 달라.

## 0. 알아둘 것 — Metric 종류

Cloud Insight로 들어오는 지표는 세 종류로 나뉜다. 어떤 걸 "등록"이라고 부르는지가
여기서 갈리므로 먼저 구분한다.

| 종류 | 설명 | 별도 신청 필요 여부 |
|---|---|---|
| System Metric | 리소스 생성 시 기본으로 수집되는 지표 | 불필요 (자동) |
| Extended Metric | 상세 모니터링을 신청해야 보이는 지표 (예: Server의 CPU 상세 지표) | **필요** |
| Custom Metric | AddProcessPlugin 등 API로 직접 등록하는 프로세스/커스텀 지표 | 필요 (API 호출) |

"Cloud Insight 등록"이라고 할 때 보통 의미하는 건 System Metric은 자동으로 잡히니
**Extended Metric(상세 모니터링) 신청** 쪽이다. 사용자가 어느 쪽을 원하는지 모호하면
물어본다.

## 1. 사전조건

- **Cloud Insight 서비스 사용 신청** — 콘솔 좌측 메뉴 Services ▸ Management &
  Governance ▸ Cloud Insight로 처음 진입하면 사용 신청 절차가 뜬다. VPC 환경 기준.
  현재는 무료로 제공되나 요금 정책이 바뀔 수 있다는 안내가 있다 ⚠ 최신 요금 정책은
  콘솔에서 재확인
- **계정 권한** — Main Account는 기본적으로 전체 권한. Sub Account로 작업한다면
  Cloud Insight 관련 권한(조회/설정)이 부여되어 있는지 먼저 확인한다. Sub Account는
  Main Account에서만 생성 가능하고, 생성 시 Console 접근/API 접근 유형을 고른다
- **환경 구분** — VPC 환경과 Classic 환경은 모니터링 신청 메뉴 위치와 가능 여부가
  다르다 ⚠ 대상 리소스가 어느 환경인지 먼저 확인
- **대상 리소스가 이미 생성되어 있어야 한다** — Cloud Insight는 기존 리소스를
  모니터링 대상으로 등록하는 서비스이지, 리소스를 새로 만들지 않는다

## 2. Server 등록

1. 대상 서버가 **VPC 환경**인지 확인한다 (Classic 서버는 절차가 다를 수 있음 ⚠)
2. 서버 콘솔(Server ▸ 대상 서버 선택)에서 **상세 모니터링** 옵션을 확인한다.
   기본 System Metric은 서버 생성과 동시에 Cloud Insight로 전송되지만, CPU 등 일부
   지표는 Type이 Extended로 표시되어 상세 모니터링을 신청해야 확인 가능하다
3. 상세 모니터링을 활성화(Enable)한다 ⚠ 정확한 버튼 위치·소요 시간(적용까지 몇 분
   걸리는지)은 콘솔에서 재확인 필요
4. Cloud Insight 콘솔 ▸ Dashboard 또는 Configuration에서 해당 서버가 모니터링
   대상 목록에 나타나는지 확인한다
5. (선택) 프로세스 단위 모니터링이 필요하면 `AddProcessPlugin` API로 프로세스를
   등록한다 ⚠ 이 API의 정확한 파라미터는 API 가이드에서 재확인

## 3. Load Balancer 등록

⚠ **이 절은 특히 미검증.** Server만큼 구체적인 자료를 확인하지 못했다.

- LB는 생성과 함께 System Metric이 Cloud Insight로 자동 수집되는 것으로 보인다
  ⚠ Server처럼 별도 "상세 모니터링" 신청이 필요한지, 아니면 자동으로 Extended
  Metric까지 잡히는지 확인 필요
- Cloud Insight 콘솔에서 LB가 모니터링 대상 목록에 보이는지로 등록 여부를 확인한다
- ALB/NLB/NPLB 종류에 따라 제공되는 지표 항목이 다를 수 있다 ⚠

## 4. Cloud DB 등록 (MySQL/PostgreSQL/Redis 등)

⚠ **이 절도 미검증.**

- Cloud DB 상품은 설치(생성) 직후 기본 모니터링이 바로 가능하다는 안내가 있다 —
  즉 Server처럼 별도 상세 모니터링 신청 없이 System Metric이 잡힐 가능성이 높다
  ⚠ 실제로 Extended Metric 신청이 필요한 지표가 있는지 콘솔에서 확인
- Master/Standby 구성이면 Cloud Insight에 두 인스턴스가 각각 별도 대상으로
  잡히는지 확인한다 ⚠
- 에러 로그·슬로우 쿼리 로그는 Cloud Insight가 아니라 DB 상품 자체 콘솔에서 보는
  경로일 수 있다 ⚠ Cloud Insight 등록과 혼동하지 않는다

## 5. 등록 후 공통 확인

- Cloud Insight 콘솔 ▸ Configuration에서 리소스가 **Target**으로 잡혔는지 확인한다
  (Target Group 설정은 Event Rule/알람 쪽 기능이라 이 스킬 범위 밖이지만, 대상이
  등록됐는지 확인하는 화면으로는 같이 쓰인다 ⚠ 메뉴명 재확인 필요)
- Dashboard에서 지표가 실제로 값이 들어오기 시작하는지 확인한다. 등록 직후에는
  첫 데이터 포인트까지 지연이 있을 수 있다 ⚠ 지연 시간 확인 필요

## 확인이 필요한 항목 ⚠ (요약)

- Server 상세 모니터링 활성화의 정확한 콘솔 경로와 적용 소요 시간
- LB 등록에 별도 신청이 필요한지 여부
- Cloud DB 등록에 별도 신청이 필요한지 여부, Master/Standby 개별 등록 여부
- VPC vs Classic 환경별 절차 차이
- Cloud Insight 사용 신청의 현재 요금 정책
- Sub Account에 필요한 정확한 권한 이름

이 목록이 채워지는 대로 상단 "검증 상태"를 **부분 검증**으로 올린다.
