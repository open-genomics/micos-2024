# -*- coding: utf-8 -*-
"""测试 shell 包装层脚本."""

import subprocess
from pathlib import Path


# 使用相对路径，支持在不同环境中运行
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
RUN_MODULE = PROJECT_ROOT / 'scripts' / 'run_module.sh'
RUN_FULL = PROJECT_ROOT / 'scripts' / 'run_full_analysis.sh'


def test_run_module_help():
    """run_module.sh 应展示当前支持的包装层模块."""
    result = subprocess.run(
        ['bash', str(RUN_MODULE), '--help'],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert 'quality_control' in result.stdout
    assert 'summarize_results' in result.stdout


def test_run_module_rejects_unsupported_module():
    """未收敛到 Python 主链路的模块应直接拒绝."""
    result = subprocess.run(
        ['bash', str(RUN_MODULE), 'network_analysis'],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert '当前未纳入稳定 Shell 包装层' in result.stderr


def test_run_module_missing_config_reports_module_requirement(tmp_path):
    """配置文件缺失时不应在读取默认值阶段静默退出，而应给出模块参数提示."""
    missing = tmp_path / 'missing.yaml'
    result = subprocess.run(
        ['bash', str(RUN_MODULE), 'quality_control', '--config', str(missing)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert '质量控制模块需要 KneadData 数据库路径' in result.stderr


def test_run_full_analysis_rejects_legacy_skip_and_resume():
    """完整流程包装层不再维护 skip/resume 逻辑."""
    result = subprocess.run(
        ['bash', str(RUN_FULL), '--skip', 'functional_analysis'],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert '--skip/--resume-from 当前不再支持' in result.stderr
