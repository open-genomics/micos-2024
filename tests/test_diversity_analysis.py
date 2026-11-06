# -*- coding: utf-8 -*-
"""测试多样性分析模块（命令拼装层）。"""

import pytest

from micos import diversity_analysis
from micos.errors import MissingInputError


def test_diversity_analysis_assembles_qiime2_commands(tmp_path, monkeypatch):
    """run_diversity_analysis 应拼装 import/alpha/beta 并导出 TSV."""
    commands = []

    def fake_run(cmd):
        commands.append(list(cmd))

    monkeypatch.setattr(diversity_analysis, "run_command_live", fake_run)

    biom = tmp_path / "feature-table.biom"
    biom.write_text("{}")
    out = tmp_path / "output"

    diversity_analysis.run_diversity_analysis(biom, out)

    assert len(commands) == 5  # import + alpha + alpha export + beta + beta export
    assert commands[0][:3] == ["qiime", "tools", "import"]
    assert commands[1][:3] == ["qiime", "diversity", "alpha"]
    assert commands[2][:3] == ["qiime", "tools", "export"]
    assert commands[3][:3] == ["qiime", "diversity", "beta"]
    assert commands[4][:3] == ["qiime", "tools", "export"]
    assert str(out / "alpha_diversity") in commands[2]
    assert str(out / "beta_diversity") in commands[4]

    # import 命令应携带 BIOM 路径与类型
    import_cmd = commands[0]
    assert str(biom) in import_cmd
    assert "FeatureTable[Frequency]" in import_cmd


def test_diversity_analysis_fails_when_biom_missing(tmp_path, monkeypatch):
    """BIOM 文件不存在时应 fail-closed，不调用任何命令."""
    commands = []
    monkeypatch.setattr(
        diversity_analysis,
        "run_command_live",
        lambda cmd: commands.append(list(cmd)),
    )

    with pytest.raises(MissingInputError, match="BIOM"):
        diversity_analysis.run_diversity_analysis(
            tmp_path / "nonexistent.biom", tmp_path / "output"
        )

    assert commands == []
