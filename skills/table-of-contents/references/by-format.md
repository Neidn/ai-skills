# 포맷별 목차 생성

## docx (Word)

**필드 TOC를 넣는다. 목차를 타이핑하지 않는다.**

- 전제: 본문 제목에 Word 스타일(제목 1/2/3)이 적용돼 있어야 한다. 스타일이 없으면 필드가
  아무것도 못 잡는다. 제목이 "굵게 키운 본문"이면 먼저 스타일부터 입힌다.
- 삽입: 참조 ▸ 목차 ▸ 자동 목차. 또는 필드 `TOC \o "1-3" \h \z \u`.
- 갱신: 제목이 바뀌면 목차 우클릭 ▸ 필드 업데이트. 페이지 번호도 이때 갱신된다.

python-docx로 생성할 때는 라이브러리가 필드 TOC를 직접 못 만드므로, TOC 필드 XML을
문단에 삽입한 뒤 "열 때 갱신" 상태로 둔다:

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_toc(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'TOC \\o "1-3" \\h \\z \\u')
    run._r.addprevious(fld)
```

Word에서 문서를 처음 열 때 "이 문서의 필드를 업데이트하시겠습니까?"에 예를 누르면 채워진다.
이 동작을 사용자에게 미리 알린다.

## HTML

각 제목에 `id`를 주고 `<nav>`로 목록을 만든다.

```html
<nav class="toc" aria-label="목차">
  <ol>
    <li><a href="#sec-overview">1. 개요</a>
      <ol><li><a href="#sec-purpose">1.1 목적</a></li></ol>
    </li>
  </ol>
</nav>
<h2 id="sec-overview">1. 개요</h2>
<h3 id="sec-purpose">1.1 목적</h3>
```

- `id`는 영숫자·하이픈으로. 한글 제목이면 `sec-1`, `sec-1-1`처럼 번호 기반 id를 권장(안정적).
- 번호는 CSS `counter`로 자동화하면 순서가 바뀌어도 따라온다:

```css
body { counter-reset: h2; }
h2 { counter-reset: h3; }
h2::before { counter-increment: h2; content: counter(h2) ". "; }
h3::before { counter-increment: h3; content: counter(h2) "." counter(h3) " "; }
```

- 긴 문서는 `position: sticky`로 목차를 화면에 고정하면 탐색이 쉽다.

## Markdown

자동 번호·자동 TOC가 없다. 제목에서 앵커를 만들어 링크한다.

**GitHub 앵커 변환 규칙** (이걸 정확히 따라야 링크가 걸린다):

1. 소문자로.
2. 공백은 하이픈(`-`)으로.
3. 영숫자·하이픈·언더스코어·한글 외 문자 제거(마침표·괄호·콜론 등 삭제).
4. 한글은 그대로 유지된다.

```
## 2.1 네트워크 구성 (VPC)   →   #21-네트워크-구성-vpc
```

목차 생성 스크립트(표준 라이브러리만):

```python
import re, sys
def slug(t):
    t = t.strip().lower()
    t = re.sub(r'[^\w\s가-힣-]', '', t)
    return re.sub(r'\s+', '-', t)

for line in open(sys.argv[1], encoding='utf-8'):
    m = re.match(r'^(#{2,4})\s+(.*)', line)
    if not m: continue
    depth = len(m.group(1)) - 2
    title = m.group(2).strip()
    print('  ' * depth + f'- [{title}](#{slug(title)})')
```

- 같은 제목이 2번 나오면 GitHub는 두 번째에 `-1`을 붙인다. 중복 제목은 애초에 피한다.
- 뷰어에 따라 규칙이 조금 다르다(GitLab·Obsidian 등). 대상 뷰어를 확인한다.

## PPT

- 아젠다(목차) 슬라이드 1장 + 각 섹션 시작에 구분 슬라이드.
- PowerPoint "구역(Section)" 기능으로 묶으면 개요 보기에서 관리된다.
- 아젠다와 섹션 제목 텍스트를 **같은 문구**로 맞춘다(불일치가 가장 흔한 실수).
- 발표용이라 3단계 번호는 과하다. 1단계(섹션)만 번호 매기거나 번호 없이 간다.
