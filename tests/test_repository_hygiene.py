import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_relative_markdown_links_resolve():
    pattern = re.compile(r"\[[^]]*\]\(([^)]+)\)")
    for document in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        for target in pattern.findall(document.read_text()):
            if target.startswith(("http://", "https://", "#")):
                continue
            path = (document.parent / target.split("#", 1)[0]).resolve()
            assert path.exists(), f"broken link in {document.relative_to(ROOT)}: {target}"


def test_no_placeholder_or_malformed_artifacts_remain():
    assert not (ROOT / "docs/images").exists()
    assert all(not path.name.startswith(" ") for path in (ROOT / "docs").iterdir())
    assert (ROOT / "docs/05-daily-leakage-summary-workflow.jpeg").is_file()


def test_unsupported_historical_result_strings_are_absent():
    text = "\n".join(
        path.read_text(errors="ignore")
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".json", ".sql", ".py", ".toml", ".yml"}
        and ".git" not in path.parts
        and ".venv" not in path.parts
    )
    unsupported_strings = (
        "$" + "663K",
        "1," + "907%",
        "18-day " + "payback",
        "Real Client " + "Results",
    )
    for unsupported in unsupported_strings:
        assert unsupported not in text
