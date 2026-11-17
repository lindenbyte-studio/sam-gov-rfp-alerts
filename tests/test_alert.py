"""Offline tests: digest building and the Slack / e-mail / Markdown renderers (no network, no Apify token).

Run: pip install -r requirements.txt pytest && pytest -q
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import alert  # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "sample_items.json").read_text(encoding="utf-8"))


def _cfg(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # any state file goes to a temp dir
    cfg = alert.load_config(ROOT / "config.yml")
    return cfg


def test_slack_payload_from_real_sample(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    digest, kept = alert.make_digest(FIXTURE, cfg, None)
    assert digest.total == len(kept) > 0
    payload = alert.build_slack_payload(digest)
    json.dumps(payload)  # must be serialisable
    blocks = payload["blocks"]
    assert payload["text"]
    assert blocks[0]["type"] == "header" and len(blocks[0]["text"]["text"]) <= 150
    assert len(blocks) <= alert.MAX_SLACK_BLOCKS
    sections = [b for b in blocks if b["type"] == "section"]
    assert len(sections) == len(digest.entries)
    for b, e in zip(sections, digest.entries):
        assert len(b["text"]["text"]) <= 3000
        if e.url:
            assert f"<{e.url}|" in b["text"]["text"]


def test_slack_payload_truncates_and_escapes():
    entries = [alert.Entry(title=f"A & B <{i}>", url=f"https://example.com/{i}", meta=["x"], detail="d" * 5000)
               for i in range(120)]
    d = alert.Digest(title="T" * 400, summary="s", entries=entries, notes=["n1"], total=120)
    p = alert.build_slack_payload(d)
    assert len(p["blocks"]) <= alert.MAX_SLACK_BLOCKS
    texts = json.dumps(p)
    assert "A &amp; B &lt;0&gt;" in texts and "and 74 more" in texts
    assert all(len(b["text"]["text"]) <= 3000 for b in p["blocks"] if b["type"] == "section")


def test_empty_results_build_no_entries(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    digest, kept = alert.make_digest([], cfg, None)
    assert digest.total == 0 and kept == [] and digest.entries == []


def test_email_and_markdown_render(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    digest, _ = alert.make_digest(FIXTURE, cfg, None)
    subject, text, html_body = alert.render_email(digest)
    md = alert.render_markdown(digest)
    assert subject and digest.entries[0].title in text and "<html" not in text
    assert digest.entries[0].url in html_body and digest.entries[0].url in md


def test_items_file_dry_run(tmp_path, monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out"
    rc = alert.main(["--config", str(ROOT / "config.yml"), "--out", str(out), "--dry-run",
                     "--items-file", str(ROOT / "tests" / "fixtures" / "sample_items.json")])
    assert rc == 0
    assert (out / "digest.md").exists() and (out / "items.csv").exists() and (out / "items.json").exists()


def test_dedupe_skips_already_sent(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, monkeypatch)
    first, _ = alert.make_digest(FIXTURE, cfg, None)
    second, kept = alert.make_digest(FIXTURE, cfg, None)
    assert first.total == len(FIXTURE) and second.total == 0 and kept == []


def test_posted_window_auto_covers_weekend():
    from datetime import datetime
    monday, tuesday = datetime(2026, 11, 16), datetime(2026, 11, 17)
    assert alert.posted_window("auto", monday) == 3
    assert alert.posted_window("auto", tuesday) == 1
    assert alert.posted_window(None, tuesday) == 1
    assert alert.posted_window(7, monday) == 7
    cfg = {"input": {"keywords": ["x"], "postedWithinDays": 2}, "alert": {}}
    assert alert.build_input(cfg)["postedWithinDays"] == 2 and alert.build_input(cfg)["sortBy"] == "newest"
