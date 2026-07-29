#!/usr/bin/env python3
"""Count writeup words (markdown-stripped) and enforce the 1,500-word limit."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "kaggle" / "writeup.md").read_text(encoding="utf-8")
text = re.sub(r"[#*`_>|]", " ", text)
text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
words = len(text.split())
(ROOT / "kaggle" / "writeup_word_count.txt").write_text(
    f"{words} words (limit 1500) — counted {__import__('datetime').date.today().isoformat()}\n")
print(f"writeup: {words} words (limit 1500)")
sys.exit(0 if words <= 1500 else 1)
