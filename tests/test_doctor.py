# -*- coding: utf-8 -*-
"""测试环境自检。"""

from __future__ import annotations

import json

from micos import doctor


def test_doctor_reports_all_tools_found(monkeypatch, capsys, tmp_path):
    """所有工具存在时应返回 0 并输出 JSON。"""
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(doctor, "_tool_version", lambda path: "1.0.0")

    db = tmp_path / "db"
    db.mkdir()
    exit_code = doctor.run_doctor(str(db), str(db), json_output=True)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert all(tool["found"] for tool in payload["tools"])
    assert all(path["exists"] for path in payload["paths"])


def test_doctor_reports_missing_tool(monkeypatch, capsys):
    """缺少工具时应返回非零并列出缺失项。"""
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    monkeypatch.setattr(doctor, "_tool_version", lambda path: None)

    exit_code = doctor.run_doctor(json_output=True)

    assert exit_code == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["missing_tools"]
