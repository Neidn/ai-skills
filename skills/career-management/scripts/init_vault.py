#!/usr/bin/env python3
"""빈 career vault 골격을 만든다.

사용: python init_vault.py <대상 경로>
대상 경로가 이미 있고 비어 있지 않으면 덮어쓰지 않고 종료한다.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "vault-template"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    target = Path(sys.argv[1]).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        print(f"중단: {target} 가 비어 있지 않다. 기존 vault를 덮어쓰지 않는다.")
        return 1
    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True)
    print(f"생성: {target}")
    print("다음: profile.md, facts.md부터 채운다. 비공개 git 레포로 관리할 것을 권장한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
