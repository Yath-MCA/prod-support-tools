import threading

from core.run_history import RunHistoryStore


def test_add_entry_completes_without_deadlock(tmp_path, monkeypatch):
    monkeypatch.setattr(
        RunHistoryStore,
        "history_file_path",
        classmethod(lambda cls: tmp_path / "suite_run_history.json"),
    )
    monkeypatch.setattr(RunHistoryStore, "base_dir", classmethod(lambda cls: tmp_path))

    done = threading.Event()
    error = {}

    def worker():
        try:
            RunHistoryStore.add_entry({
                "tool_id": "element_extractor",
                "action": "extract",
                "source_path": r"C:\data\doc",
                "output_dir": str(tmp_path),
                "report_path": str(tmp_path / "report.html"),
                "params": {"query_value": "ext-link"},
                "summary": "test",
            })
            done.set()
        except Exception as exc:
            error["e"] = exc
            done.set()

    t = threading.Thread(target=worker)
    t.start()
    finished = done.wait(timeout=5)
    assert finished, "add_entry deadlocked (did not finish within 5s)"
    assert "e" not in error
    entries = RunHistoryStore.load_entries()
    assert len(entries) == 1
    assert entries[0]["tool_id"] == "element_extractor"
    assert entries[0]["report_path"].endswith("report.html")
