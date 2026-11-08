# -*- coding: utf-8 -*-
"""测试 scripts/download_databases.sh 的校验清单解析（不联网）。"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "download_databases.sh"

HASH_A = "a" * 64
HASH_B = "b" * 64


def _bash(snippet: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """在 source 了下载脚本的 bash 中执行片段（脚本自身不会跑 main）。"""
    script = f'set -e\nsource "{SCRIPT}"\n{snippet}'
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _manifest(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "checksums.sha256"
    path.write_text(content, encoding="utf-8")
    return path


def test_url_basename_decodes_percent_encoding():
    """URL basename 应解码百分号编码，便于匹配上游归档文件名。"""
    result = _bash(
        'url_basename "https://x/Kraken2%20PlusPF%20%2820231230%29.tar.gz?token=1"'
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Kraken2 PlusPF (20231230).tar.gz"


def test_manifest_entry_with_spaces_and_binary_marker(tmp_path):
    """清单按整段文件名匹配：支持空格与 sha256sum 的二进制模式星号。"""
    manifest = _manifest(
        tmp_path,
        f"{HASH_A}  kraken2_standard_20230605.tar.gz\n"
        f"{HASH_B} *Kraken2 PlusPF (20231230).tar.gz\n",
    )
    result = _bash(
        'MICOS_DB_CHECKSUMS="{}" resolve_expected_sha pluspf '
        '"https://x/Kraken2%20PlusPF%20%2820231230%29.tar.gz" ""'.format(manifest),
        env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == HASH_B


def test_explicit_env_var_wins_over_manifest(tmp_path):
    """显式 MICOS_KRAKEN2_*_SHA256 优先于清单。"""
    manifest = _manifest(tmp_path, f"{HASH_A}  kraken2_standard_20230605.tar.gz\n")
    explicit = "c" * 64
    result = _bash(
        'MICOS_DB_CHECKSUMS="{}" resolve_expected_sha standard '
        '"https://x/kraken2_standard_20230605.tar.gz" "{}"'.format(manifest, explicit),
        env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == explicit


def test_missing_entry_in_explicit_manifest_is_an_error(tmp_path):
    """给了清单却查不到条目时必须失败，而不是静默跳过校验。"""
    manifest = _manifest(tmp_path, f"{HASH_A}  something_else.tar.gz\n")
    result = _bash(
        'MICOS_DB_CHECKSUMS="{}" resolve_expected_sha standard '
        '"https://x/kraken2_standard_20230605.tar.gz" ""'.format(manifest),
        env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0
    assert "没有" in result.stderr


def test_unreadable_manifest_is_an_error(tmp_path):
    """清单不可读时应报错并指明路径。"""
    missing = tmp_path / "absent.sha256"
    result = _bash(
        'MICOS_DB_CHECKSUMS="{}" resolve_expected_sha standard '
        '"https://x/kraken2_standard_20230605.tar.gz" ""'.format(missing),
        env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0
    assert "无法读取校验清单" in result.stderr


def test_no_manifest_and_no_explicit_hash_skips_verification():
    """未提供任何校验来源时返回空串（调用方据此告警），不报错。"""
    result = _bash(
        'resolve_expected_sha standard "https://x/kraken2_standard_20230605.tar.gz" ""',
        env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
