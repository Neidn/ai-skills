# 포맷별 적용법

대상 포맷 절 하나만 읽는다. 원칙(토큰)은 `design-tokens.md`에 있고, 여기서는 그걸
각 포맷에서 **어떻게 realize 하는지**만 다룬다.

## Markdown

색·글꼴·크기를 제어할 수 없다. 위계와 규격만 지킨다.

- 제목은 `#`~`####` 4단계까지만. 그 이상 깊어지면 구조를 다시 본다(→ document-structure).
- 콜아웃은 인용구 + 볼드 라벨: `> **주의** — …`
- 표는 GFM 표. 정렬 지정자(`---:`)로 숫자 열 우측 정렬.
- 코드블록은 언어 명시. 인라인 코드는 명령·경로·값에만.
- 강조는 볼드만. 이탤릭·취소선·색은 쓰지 않는다(렌더러마다 다르게 나옴).

렌더 대상이 GitHub/위키면 여기까지가 최선이다. 색·타이포가 필요하면 HTML로 내보낸다.

## HTML / 인쇄(PDF)

가장 완전하게 토큰을 적용할 수 있다.

1. `assets/document.css`를 `<head>`에 링크하거나 인라인한다.
2. 브랜드 색이 있으면 `:root`의 `--accent` 한 줄만 교체한다.
3. 인쇄용 PDF는 브라우저 인쇄(또는 `weasyprint`, `Playwright`의 `page.pdf()`)로 뽑는다.
   `@media print` 규칙(페이지 여백·색 유지)이 CSS에 이미 들어 있다.

```bash
# 예: weasyprint로 PDF
pip install weasyprint --break-system-packages
weasyprint report.html report.pdf
```

- 색약·흑백 인쇄 대비를 위해 강조는 색+굵기를 함께 쓴다.
- `page-break-inside: avoid`가 표·콜아웃에 걸려 있어 요소가 페이지 경계에서 잘리지 않는다.

## docx (Word)

두 가지 길이 있다. **기존 Word 문서를 손보면** 스타일 갤러리에, **스크립트로 생성하면**
python-docx 스타일에 토큰을 매핑한다. docx 파일을 직접 만들거나 편집할 때는 이 저장소가
아니라 환경에 설치된 `docx` 스킬의 절차를 따르되, 값은 아래 매핑을 쓴다.

- Word 스타일 `제목 1/2/3`, `본문`에 `design-tokens.md`의 크기·굵기·간격을 그대로 넣는다.
- 색은 글자색/음영에 `text`·`accent`·상태색의 HEX를 넣는다.
- 표는 "격자" 대신 헤더 행 음영 + 아래 테두리만 남긴 사용자 표 스타일을 만든다.
- 콜아웃은 1×1 표(배경색 + 좌측 굵은 테두리)로 만든다. Word엔 콜아웃 기본형이 없다.
- 목차는 Word 필드 TOC를 쓴다(→ table-of-contents `by-format.md`).

python-docx 요약:

```python
from docx.shared import Pt, RGBColor
s = doc.styles['Heading 1']
s.font.size = Pt(28); s.font.bold = True
s.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
```

## PPT (PowerPoint)

슬라이드 마스터에 토큰을 한 번 매핑하면 전 슬라이드에 적용된다. pptx 파일을 직접 다룰
때는 환경의 `pptx` 스킬 절차를 따르되 값은 아래를 쓴다.

- 마스터 테마 색: `dk1=text`, `lt1=흰색`, `accent1=accent`, 나머지 accent에 상태 4색.
- 제목 자리표시자=H1/H2 스케일, 본문 자리표시자=본문 스케일. 슬라이드마다 크기를 손대지 않는다.
- 한 슬라이드 = 한 메시지. 색 강조는 슬라이드당 1곳.
- 표·콜아웃은 문서용보다 더 크고 성기게. 발표 화면은 멀리서 본다.
