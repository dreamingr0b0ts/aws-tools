import subprocess

import precommit_checks as pc


def test_staged_py_filters_python_files(monkeypatch):
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="a.py\nREADME.md\npkg/b.py\nscript.sh\n",
    )
    monkeypatch.setattr(pc, "sh", lambda cmd: fake)
    assert pc.staged_py() == ["a.py", "pkg/b.py"]


def test_staged_py_empty(monkeypatch):
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
    monkeypatch.setattr(pc, "sh", lambda cmd: fake)
    assert pc.staged_py() == []


def test_tool_falls_back_to_path(monkeypatch):
    # No local .venv binary -> resolve via PATH (shutil.which).
    monkeypatch.setattr(pc.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(pc.Path, "exists", lambda self: False)
    assert pc.tool("ruff") == "/usr/bin/ruff"
