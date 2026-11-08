# -*- coding: utf-8 -*-
"""测试 CLI 默认配置行为。"""

import yaml
from click.testing import CliRunner

from micos.cli import main


def test_full_run_uses_config_defaults(tmp_path, monkeypatch):
    """full-run 从标准配置文件提取默认参数。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    input_dir = tmp_path / "data" / "raw_input"
    input_dir.mkdir(parents=True)
    results_dir = tmp_path / "results"
    kneaddata_db = tmp_path / "db" / "kneaddata"
    kraken2_db = tmp_path / "db" / "kraken2"
    kneaddata_db.mkdir(parents=True)
    kraken2_db.mkdir(parents=True)

    analysis_config = {
        "paths": {
            "input_dir": str(input_dir),
            "output_dir": str(results_dir),
        },
        "resources": {"max_threads": 6},
    }
    databases_config = {
        "quality_control": {"kneaddata": {"human_genome": str(kneaddata_db)}},
        "taxonomy": {"kraken2": {"standard": str(kraken2_db)}},
    }

    (config_dir / "analysis.yaml").write_text(
        yaml.safe_dump(analysis_config), encoding="utf-8"
    )
    (config_dir / "databases.yaml").write_text(
        yaml.safe_dump(databases_config), encoding="utf-8"
    )

    captured = {}

    def fake_run_full_pipeline(
        input_dir_arg,
        results_dir_arg,
        threads,
        kneaddata_db_arg,
        kraken2_db_arg,
        skip_qc=False,
        skip_taxonomy=False,
        skip_functional=False,
        skip_diversity=False,
        metadata_path=None,
    ):
        captured.update(
            {
                "input_dir": input_dir_arg,
                "results_dir": results_dir_arg,
                "threads": threads,
                "kneaddata_db": kneaddata_db_arg,
                "kraken2_db": kraken2_db_arg,
                "metadata_path": metadata_path,
            }
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("micos.cli.run_full_pipeline", fake_run_full_pipeline)

    runner = CliRunner()
    result = runner.invoke(main, ["full-run"])

    assert result.exit_code == 0, result.output
    assert captured == {
        "input_dir": str(input_dir),
        "results_dir": str(results_dir),
        "threads": 6,
        "kneaddata_db": str(kneaddata_db),
        "kraken2_db": str(kraken2_db),
        "metadata_path": None,
    }


def test_full_run_passes_metadata_option(tmp_path, monkeypatch):
    """full-run --metadata 应传递 metadata_path 到 pipeline。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    input_dir = tmp_path / "data" / "raw_input"
    input_dir.mkdir(parents=True)
    results_dir = tmp_path / "results"
    kneaddata_db = tmp_path / "db" / "kneaddata"
    kraken2_db = tmp_path / "db" / "kraken2"
    kneaddata_db.mkdir(parents=True)
    kraken2_db.mkdir(parents=True)
    metadata_file = tmp_path / "samples.tsv"
    metadata_file.write_text("sample-id\tgroup\nS001\tControl\n", encoding="utf-8")

    analysis_config = {
        "paths": {
            "input_dir": str(input_dir),
            "output_dir": str(results_dir),
        },
        "resources": {"max_threads": 4},
    }
    databases_config = {
        "quality_control": {"kneaddata": {"human_genome": str(kneaddata_db)}},
        "taxonomy": {"kraken2": {"standard": str(kraken2_db)}},
    }

    (config_dir / "analysis.yaml").write_text(
        yaml.safe_dump(analysis_config), encoding="utf-8"
    )
    (config_dir / "databases.yaml").write_text(
        yaml.safe_dump(databases_config), encoding="utf-8"
    )

    captured = {}

    def fake_run_full_pipeline(
        input_dir_arg,
        results_dir_arg,
        threads,
        kneaddata_db_arg,
        kraken2_db_arg,
        skip_qc=False,
        skip_taxonomy=False,
        skip_functional=False,
        skip_diversity=False,
        metadata_path=None,
    ):
        captured["metadata_path"] = metadata_path

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("micos.cli.run_full_pipeline", fake_run_full_pipeline)

    runner = CliRunner()
    result = runner.invoke(main, ["full-run", "--metadata", str(metadata_file)])

    assert result.exit_code == 0, result.output
    assert captured["metadata_path"] == str(metadata_file)


def _write_config_files(tmp_path, analysis: dict, databases: dict | None = None):
    """在 tmp_path/config 下写入分析/数据库配置。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    analysis_path = config_dir / "analysis.yaml"
    analysis_path.write_text(yaml.safe_dump(analysis), encoding="utf-8")
    if databases is not None:
        (config_dir / "databases.yaml").write_text(
            yaml.safe_dump(databases), encoding="utf-8"
        )
    return config_dir


def test_validate_config_rejects_unknown_field(tmp_path, monkeypatch):
    """validate-config 对未知字段返回非零退出码。"""
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(
        yaml.safe_dump({"paths": {"input_dir": "/x", "unknown_field": 1}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["validate-config", "--config", str(bad_config)])

    assert result.exit_code == 3, result.output


def test_validate_config_rejects_corrupted_yaml(tmp_path, monkeypatch):
    """validate-config 对损坏 YAML 返回非零退出码。"""
    bad_config = tmp_path / "broken.yaml"
    bad_config.write_text("paths:\n  input_dir: [unclosed\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["validate-config", "--config", str(bad_config)])

    assert result.exit_code == 3, result.output


def test_validate_config_rejects_missing_required_db(tmp_path, monkeypatch):
    """validate-config 对缺失必需阶段依赖（数据库）返回非零。"""
    valid_without_db = tmp_path / "analysis.yaml"
    valid_without_db.write_text(
        yaml.safe_dump(
            {
                "paths": {
                    "input_dir": "/data/input",
                    "output_dir": "/data/results",
                },
                "resources": {"max_threads": 8},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["validate-config", "--config", str(valid_without_db)])

    assert result.exit_code == 3, result.output
    assert "KneadData" in result.output or "Kraken2" in result.output


def test_validate_config_warns_on_placeholder_db(tmp_path, monkeypatch):
    """validate-config 对占位符数据库路径仅警告（退出码 0）。"""
    valid_config = tmp_path / "analysis.yaml"
    valid_config.write_text(
        yaml.safe_dump(
            {
                "paths": {
                    "input_dir": "/data/input",
                    "output_dir": "/data/results",
                    "databases": {
                        "kneaddata": "/path/to/kneaddata_db",
                        "kraken2": "/path/to/kraken2_db",
                    },
                },
                "resources": {"max_threads": 8},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["validate-config", "--config", str(valid_config)])

    assert result.exit_code == 0, result.output
    assert "占位符" in result.output


def test_config_error_at_cli_boundary_exits_stable_code(tmp_path, monkeypatch):
    """CLI 边界遇到损坏配置应以稳定配置退出码（3）退出，而非静默回退默认值。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "analysis.yaml").write_text(
        "paths:\n  input_dir: [unclosed\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["full-run"])

    assert result.exit_code == 3, result.output


def test_full_run_dry_run_prints_resolved_plan_with_sources(tmp_path, monkeypatch):
    """--dry-run 输出 resolved plan（阶段、参数来源），且不执行外部工具。"""
    _write_config_files(
        tmp_path,
        {
            "paths": {
                "input_dir": "data/raw_input",
                "output_dir": "results",
            },
            "resources": {"max_threads": 6},
        },
        {
            "quality_control": {"kneaddata": {"human_genome": "db/kneaddata"}},
            "taxonomy": {"kraken2": {"standard": "db/kraken2"}},
        },
    )
    # Click 对 --input-dir / --kneaddata-db / --kraken2-db 做 exists=True 校验，
    # 相对路径按配置文件目录解析后需要存在。
    (tmp_path / "config" / "data" / "raw_input").mkdir(parents=True)
    (tmp_path / "config" / "db" / "kneaddata").mkdir(parents=True)
    (tmp_path / "config" / "db" / "kraken2").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["--dry-run", "full-run"])

    assert result.exit_code == 0, result.output
    assert "Resolved Plan" in result.output
    assert "质量控制" in result.output
    assert "物种分类" in result.output
    assert "结果汇总" in result.output
    assert "input_dir: analysis.yaml" in result.output
    assert "kneaddata_db: databases.yaml" in result.output
    assert "kraken2_db: databases.yaml" in result.output
    # 不执行外部工具：不应触发 run_full_pipeline
    assert "不执行任何实际操作" in result.output


def test_full_run_dry_run_cli_override_reports_cli_source(tmp_path, monkeypatch):
    """CLI 覆盖的参数来源应报告为 cli。"""
    _write_config_files(
        tmp_path,
        {
            "paths": {
                "input_dir": "data/raw_input",
                "output_dir": "results",
            },
            "resources": {"max_threads": 6},
        },
        {
            "quality_control": {"kneaddata": {"human_genome": "db/kneaddata"}},
            "taxonomy": {"kraken2": {"standard": "db/kraken2"}},
        },
    )
    (tmp_path / "config" / "data" / "raw_input").mkdir(parents=True)
    (tmp_path / "config" / "db" / "kneaddata").mkdir(parents=True)
    (tmp_path / "config" / "db" / "kraken2").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["--dry-run", "full-run", "--threads", "32"])

    assert result.exit_code == 0, result.output
    assert "threads: cli" in result.output


def test_full_run_maps_no_samples_to_stable_exit_code(tmp_path, monkeypatch):
    """NoSamplesError 应映射为稳定的输入错误退出码。"""
    from micos.errors import NoSamplesError

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    results_dir = tmp_path / "results"
    db = tmp_path / "db"
    db.mkdir()

    def fake_run_full_pipeline(*args, **kwargs):
        raise NoSamplesError("没有样本")

    monkeypatch.setattr("micos.cli.run_full_pipeline", fake_run_full_pipeline)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "full-run",
            "--input-dir",
            str(input_dir),
            "--results-dir",
            str(results_dir),
            "--kneaddata-db",
            str(db),
            "--kraken2-db",
            str(db),
        ],
    )

    assert result.exit_code == 6, result.output
    assert "没有样本" in result.output


def test_version_command_reports_release_version():
    """--version 应报告发布版本，而不是 git dev 版本。"""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "1.2.0" in result.output


def test_full_run_skip_taxonomy_without_biom_is_usage_error(tmp_path):
    """--skip-taxonomy 且未跳过多样性时，CLI 应提前给出用法错误而不是下游失败."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    db = tmp_path / "db"
    db.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "full-run",
            "--input-dir",
            str(input_dir),
            "--results-dir",
            str(tmp_path / "results"),
            "--kneaddata-db",
            str(db),
            "--skip-taxonomy",
        ],
    )

    assert result.exit_code == 2, result.output
    assert "feature-table.biom" in result.output
    assert "--skip-diversity" in result.output


def test_doctor_uses_config_database_paths(tmp_path, monkeypatch):
    """doctor 未显式传参时应读取配置文件中的数据库路径。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "analysis.yaml").write_text(
        yaml.safe_dump(
            {
                "paths": {
                    "input_dir": str(tmp_path / "input"),
                    "output_dir": str(tmp_path / "results"),
                    "databases": {
                        "kneaddata": str(tmp_path / "db" / "kneaddata"),
                        "kraken2": str(tmp_path / "db" / "kraken2"),
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_run_doctor(kneaddata_db, kraken2_db, json_output):
        captured.update(
            kneaddata_db=kneaddata_db, kraken2_db=kraken2_db, json_output=json_output
        )
        return 0

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("micos.cli.run_doctor", fake_run_doctor)

    result = CliRunner().invoke(main, ["doctor", "--json"])

    assert result.exit_code == 0, result.output
    assert captured["kneaddata_db"] == str(tmp_path / "db" / "kneaddata")
    assert captured["kraken2_db"] == str(tmp_path / "db" / "kraken2")
    assert captured["json_output"] is True
