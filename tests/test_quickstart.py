"""The README quickstart is code that readers copy, so it runs as a test."""
import re
from pathlib import Path


def test_readme_quickstart_runs():
    readme = Path(__file__).resolve().parent.parent / "README.md"
    text = readme.read_text(encoding="utf-8")
    section = text.split("## For developers", 1)[1]
    blocks = re.findall(r"```python\n(.*?)```", section, re.S)
    assert len(blocks) == 1, "expected exactly one python block in the quickstart"
    exec(compile(blocks[0], "README quickstart", "exec"), {})
