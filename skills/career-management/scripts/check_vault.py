#!/usr/bin/env python3
"""career vault 점검 리포트.

사용: python check_vault.py <vault 경로> [--json] [--stale-days N]

검사 항목
- projects/*.md 필수 frontmatter 누락, domains 표준값 이탈
- [직접 입력 필요] / [확인 필요] 개수 (파일별)
- updated 기준 오래된 파일
- facts.md "[금지] 틀린 표현 → 바른 표현" 위반 (sources/, outputs/ 제외)
- companies/*.md 에 연결되지 않은 프로젝트, 존재하지 않는 company 참조
외부 의존성 없음 (표준 라이브러리만).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

REQUIRED = ["id", "title", "company", "period", "role", "status", "domains", "disclosure", "updated"]
DOMAINS = {
    "클라우드 인프라·IaC", "Kubernetes·GitOps", "운영 자동화·사내 도구",
    "DB·미들웨어", "보안·컴플라이언스", "모니터링·AI", "리더십",
}
STATUS = {"production", "poc", "ongoing", "done", "lab", "paused"}
DISCLOSURE = {"public", "anonymize", "internal"}
TODO_MARKS = ("[직접 입력 필요]", "[확인 필요]")
SKIP_DIRS = {"sources", "outputs", ".git"}


def parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm: dict[str, object] = {}
    for line in text[3:end].splitlines():
        line = line.split(" #", 1)[0].rstrip()
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]") and val not in TODO_MARKS:
            fm[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
        else:
            fm[key] = val.strip("'\"")
    return fm


def parse_forbidden(facts: Path) -> list[tuple[str, str]]:
    if not facts.exists():
        return []
    out = []
    for line in facts.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*-\s*\[금지\]\s*(.+?)\s*(?:→|->)\s*(.+)$", line)
        if m:
            out.append((m.group(1).strip().strip('"'), m.group(2).strip()))
    return out


def to_date(v: object) -> date | None:
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def check(vault: Path, stale_days: int) -> dict[str, object]:
    report: dict[str, object] = {"vault": str(vault), "errors": [], "warnings": [], "todos": {}, "forbidden": []}
    errors: list[str] = report["errors"]  # type: ignore[assignment]
    warnings: list[str] = report["warnings"]  # type: ignore[assignment]
    todos: dict[str, int] = report["todos"]  # type: ignore[assignment]

    projects = sorted((vault / "projects").glob("*.md"))
    companies = {p.stem: p.read_text(encoding="utf-8") for p in (vault / "companies").glob("*.md")}
    today = date.today()

    for p in projects:
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        rel = f"projects/{p.name}"
        missing = [k for k in REQUIRED if not fm.get(k)]
        if missing:
            errors.append(f"{rel}: frontmatter 누락 {missing}")
        if fm.get("id") and fm["id"] != p.stem:
            errors.append(f"{rel}: id '{fm['id']}' ≠ 파일명 '{p.stem}'")
        bad = [d for d in fm.get("domains", []) or [] if d not in DOMAINS] if isinstance(fm.get("domains"), list) else []
        if bad:
            warnings.append(f"{rel}: 표준 외 domains {bad}")
        if fm.get("status") and fm["status"] not in STATUS:
            warnings.append(f"{rel}: status '{fm['status']}' 표준 외")
        if fm.get("disclosure") and fm["disclosure"] not in DISCLOSURE:
            warnings.append(f"{rel}: disclosure '{fm['disclosure']}' 표준 외")
        if fm.get("disclosure") == "anonymize" and not fm.get("public_alias"):
            warnings.append(f"{rel}: anonymize인데 public_alias 없음")
        comp = fm.get("company")
        if comp and comp not in companies:
            errors.append(f"{rel}: company '{comp}' 에 해당하는 companies/{comp}.md 없음")
        elif comp and f"[[{p.stem}]]" not in companies[comp]:
            warnings.append(f"{rel}: companies/{comp}.md 프로젝트 목록에 [[{p.stem}]] 없음")
        d = to_date(fm.get("updated", ""))
        if d and (today - d).days > stale_days:
            warnings.append(f"{rel}: {(today - d).days}일 동안 갱신 안 됨")

    forbidden = parse_forbidden(vault / "facts.md")
    for f in sorted(vault.rglob("*.md")):
        parts = set(f.relative_to(vault).parts)
        if parts & SKIP_DIRS:
            continue
        rel = str(f.relative_to(vault))
        text = f.read_text(encoding="utf-8")
        n = sum(text.count(m) for m in TODO_MARKS)
        if n:
            todos[rel] = n
        if rel == "facts.md":
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for wrong, right in forbidden:
                if wrong in line:
                    report["forbidden"].append({"file": rel, "line": lineno, "found": wrong, "use": right})  # type: ignore[union-attr]

    report["summary"] = {
        "projects": len(projects),
        "companies": len(companies),
        "errors": len(errors),
        "warnings": len(warnings),
        "todo_marks": sum(todos.values()),
        "forbidden_hits": len(report["forbidden"]),  # type: ignore[arg-type]
    }
    return report


def print_human(r: dict[str, object]) -> None:
    s = r["summary"]  # type: ignore[index]
    print(f"# vault 점검: {r['vault']}")
    print(f"프로젝트 {s['projects']} · 회사 {s['companies']} · 오류 {s['errors']} · 경고 {s['warnings']}"
          f" · 빈칸 표시 {s['todo_marks']} · 금지 표현 {s['forbidden_hits']}")
    for title, key in (("오류", "errors"), ("경고", "warnings")):
        items = r[key]  # type: ignore[index]
        if items:
            print(f"\n## {title}")
            for i in items:
                print(f"- {i}")
    if r["forbidden"]:
        print("\n## 금지 표현 위반")
        for h in r["forbidden"]:  # type: ignore[union-attr]
            print(f"- {h['file']}:{h['line']} '{h['found']}' → {h['use']}")
    if r["todos"]:
        print("\n## 빈칸 표시가 많은 파일")
        for f, n in sorted(r["todos"].items(), key=lambda x: -x[1])[:15]:  # type: ignore[union-attr]
            print(f"- {f}: {n}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stale-days", type=int, default=180)
    a = ap.parse_args()
    vault = Path(a.vault).expanduser().resolve()
    if not (vault / "projects").is_dir():
        print(f"vault가 아니다(projects/ 없음): {vault}", file=sys.stderr)
        return 2
    r = check(vault, a.stale_days)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print_human(r)
    return 1 if r["summary"]["errors"] else 0  # type: ignore[index]


if __name__ == "__main__":
    sys.exit(main())
