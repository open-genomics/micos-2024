# -*- coding: utf-8 -*-
"""MICOS-2024 命令行界面."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path

import click
import yaml
from click.core import ParameterSource
from pydantic import ValidationError

from micos import __version__
from micos.config import (
    DEFAULT_THREADS,
    AnalysisConfig,
    ConfigError,
    load_databases_config_from_yaml,
    merge_databases_config,
    resolve_full_run_config,
)
from micos.diversity_analysis import run_diversity_analysis
from micos.doctor import run_doctor
from micos.errors import MicosError
from micos.full_run import run_full_pipeline
from micos.functional_annotation import run_functional_annotation
from micos.quality_control import run_qc
from micos.summarize_results import run_summarize
from micos.taxonomic_profiling import run_taxonomic_profiling
from micos.utils import setup_logging

# 返回码定义
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_INVALID_ARGS = 2
EXIT_CONFIG_ERROR = 3
EXIT_MISSING_DEPS = 4
EXIT_DB_ERROR = 5
EXIT_IO_ERROR = 6
EXIT_INTERRUPTED = 130

_PLACEHOLDER_PREFIX = "/path/to/"


def _print_dry_run(
    title: str,
    details: dict[str, object],
    footer: str | None = None,
) -> None:
    """打印 dry-run 预览，不执行实际分析."""
    click.secho(f"=== {title} ===", fg="cyan")
    for label, value in details.items():
        click.echo(f"{label}: {value}")
    if footer:
        click.echo(footer)


def _invoke(label: str, action: Callable[[], None]) -> None:
    """执行模块并在失败时输出统一的错误信息."""
    try:
        action()
    except MicosError as exc:
        click.secho(f"{label}执行失败: {exc}", fg="red")
        sys.exit(exc.exit_code)
    except FileNotFoundError as exc:
        click.secho(f"{label}执行失败: 未找到外部工具或文件: {exc}", fg="red")
        sys.exit(EXIT_MISSING_DEPS)
    except Exception as exc:
        click.secho(f"{label}执行失败: {exc}", fg="red")
        raise


def _is_placeholder_path(path: str | None) -> bool:
    """判断数据库路径是否仍是模板占位符."""
    if path is None:
        return False
    return path.startswith(_PLACEHOLDER_PREFIX) or "${" in path


def _param_source(ctx: click.Context, name: str, config_sources: dict[str, str]) -> str:
    """判断参数最终来源：CLI > analysis.yaml/databases.yaml > 默认。"""
    source = ctx.get_parameter_source(name)
    if source is ParameterSource.COMMANDLINE:
        return "cli"
    if source is ParameterSource.DEFAULT_MAP:
        return config_sources.get(name, "analysis.yaml")
    return "default"


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False),
    help="指定分析配置文件路径。",
)
@click.option(
    "--log-file", type=click.Path(dir_okay=False), help="将日志输出到指定文件."
)
@click.option("--verbose", is_flag=True, help="启用详细的 DEBUG 级别日志.")
@click.option("--dry-run", is_flag=True, help="仅显示将要执行的命令，不实际运行.")
@click.version_option(
    version=__version__, prog_name="MICOS-2024", message="%(prog)s %(version)s"
)
@click.pass_context
def main(
    ctx: click.Context,
    config_path: str | None,
    log_file: str | None,
    verbose: bool,
    dry_run: bool,
) -> None:
    """MICOS-2024 命令行界面."""
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level, log_file=log_file)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["dry_run"] = dry_run

    # 使用 Pydantic 配置加载默认值
    config_file = Path(config_path) if config_path else Path("config/analysis.yaml")
    ctx.obj["config_file"] = config_file
    ctx.obj["config_sources"] = {}

    if config_file.exists():
        # 配置失败在 CLI 边界 fail-closed：稳定退出码，不回退到默认值。
        try:
            resolved = resolve_full_run_config(config_file)
        except (ConfigError, yaml.YAMLError, ValidationError, OSError) as exc:
            click.secho(f"✗ 配置文件加载失败: {exc}", fg="red")
            sys.exit(EXIT_CONFIG_ERROR)

        ctx.obj["config_sources"] = {key: rv.source for key, rv in resolved.items()}
        ctx.default_map = ctx.default_map or {}
        ctx.default_map.setdefault(
            "full-run",
            {
                "input_dir": resolved["input_dir"].value,
                "results_dir": resolved["results_dir"].value,
                "threads": resolved["threads"].value,
                "kneaddata_db": resolved["kneaddata_db"].value,
                "kraken2_db": resolved["kraken2_db"].value,
            },
        )


@main.command("validate-config")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False),
    help="要验证的配置文件路径.",
)
@click.pass_context
def validate_config(ctx: click.Context, config_path: str | None) -> None:
    """验证配置文件的有效性."""
    warnings: list[str] = []
    errors: list[str] = []

    config_file = config_path or ctx.obj.get("config_path") or "config/analysis.yaml"
    config_path_obj = Path(config_file)

    if not config_path_obj.exists():
        click.secho(f"✗ 配置文件不存在: {config_file}", fg="red")
        sys.exit(EXIT_CONFIG_ERROR)

    # 语法 / 未知字段 / 类型错误 → 配置错误退出码
    try:
        config = AnalysisConfig.from_yaml(config_path_obj)
    except (ConfigError, yaml.YAMLError, ValidationError) as exc:
        click.secho(f"✗ 配置文件无效: {exc}", fg="red")
        sys.exit(EXIT_CONFIG_ERROR)

    click.secho("✓ 配置文件语法有效", fg="green")

    db_config_path = config_path_obj.parent / "databases.yaml"
    db_config = load_databases_config_from_yaml(db_config_path)
    db_paths = merge_databases_config(config, db_config)

    # 必需阶段依赖：缺失 → 错误；占位符 → 仅警告
    kneaddata_db = db_paths.get("kneaddata_db")
    if not kneaddata_db:
        errors.append(
            "缺少必需阶段依赖: KneadData 数据库 "
            "(paths.databases.kneaddata 或 databases.yaml 的 "
            "quality_control.kneaddata.human_genome)"
        )
    elif _is_placeholder_path(kneaddata_db):
        warnings.append("KneadData 数据库路径为占位符，尚未填写真实路径")

    kraken2_db = db_paths.get("kraken2_db")
    if not kraken2_db:
        errors.append(
            "缺少必需阶段依赖: Kraken2 数据库 "
            "(paths.databases.kraken2 或 databases.yaml 的 taxonomy.kraken2.standard)"
        )
    elif _is_placeholder_path(kraken2_db):
        warnings.append("Kraken2 数据库路径为占位符，尚未填写真实路径")

    # 非硬性检查仅警告
    if not config.input_dir:
        warnings.append("未配置输入目录 (input_dir)")
    if not config.results_dir:
        warnings.append("未配置结果目录 (results_dir)")
    if not db_config_path.exists():
        warnings.append("数据库配置文件 (databases.yaml) 不存在")

    for warning in warnings:
        click.secho(f"⚠ 警告: {warning}", fg="yellow")

    if errors:
        for err in errors:
            click.secho(f"✗ 错误: {err}", fg="red")
        click.secho("✗ 配置验证未通过!", fg="red")
        sys.exit(EXIT_CONFIG_ERROR)

    click.secho("\n✓ 配置验证完成!", fg="green")
    sys.exit(EXIT_SUCCESS)


@main.command("doctor")
@click.option(
    "--kneaddata-db",
    type=click.Path(exists=False, dir_okay=True),
    help="KneadData 参考数据库路径（可选）。",
)
@click.option(
    "--kraken2-db",
    type=click.Path(exists=False, dir_okay=True),
    help="Kraken2 参考数据库路径（可选）。",
)
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON.")
def doctor(
    kneaddata_db: str | None,
    kraken2_db: str | None,
    json_output: bool,
) -> None:
    """检查外部工具、数据库路径与运行环境。"""
    sys.exit(run_doctor(kneaddata_db, kraken2_db, json_output))


@main.command("full-run")
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="包含原始 FASTQ 文件的输入目录.",
)
@click.option(
    "--results-dir",
    required=True,
    type=click.Path(file_okay=False),
    help="存放所有分析结果的根目录.",
)
@click.option(
    "--threads",
    type=int,
    default=DEFAULT_THREADS,
    help=f"使用的线程数 (默认: {DEFAULT_THREADS}).",
)
@click.option(
    "--kneaddata-db",
    type=click.Path(exists=True, dir_okay=True),
    help="KneadData 参考数据库的路径.",
)
@click.option(
    "--kraken2-db",
    type=click.Path(exists=True, dir_okay=True),
    help="Kraken2 参考数据库的路径.",
)
@click.option(
    "--metadata",
    "metadata_path",
    type=click.Path(exists=True, dir_okay=False),
    help="样本元数据 TSV 文件路径 (sample-id 列与 FASTQ 文件名 join).",
)
@click.option("--skip-qc", is_flag=True, help="跳过质量控制步骤.")
@click.option("--skip-taxonomy", is_flag=True, help="跳过物种分类步骤.")
@click.option("--skip-functional", is_flag=True, help="跳过功能注释步骤.")
@click.option("--skip-diversity", is_flag=True, help="跳过多样性分析步骤.")
@click.pass_context
def full_run(
    ctx: click.Context,
    input_dir: str,
    results_dir: str,
    threads: int,
    kneaddata_db: str | None,
    kraken2_db: str | None,
    metadata_path: str | None,
    skip_qc: bool,
    skip_taxonomy: bool,
    skip_functional: bool,
    skip_diversity: bool,
) -> None:
    """运行完整的 MICOS 分析流程."""
    if not kneaddata_db and not skip_qc:
        raise click.UsageError(
            "错误: 必须通过命令行参数 --kneaddata-db 或配置文件提供 KneadData 数据库路径。"
        )
    if not kraken2_db and not skip_taxonomy:
        raise click.UsageError(
            "错误: 必须通过命令行参数 --kraken2-db 或配置文件提供 Kraken2 数据库路径。"
        )

    if ctx.obj.get("dry_run"):
        config_sources = ctx.obj.get("config_sources", {})
        sources = {
            name: _param_source(ctx, name, config_sources)
            for name in (
                "input_dir",
                "results_dir",
                "threads",
                "kneaddata_db",
                "kraken2_db",
            )
        }
        stages = [
            ("质量控制 (quality-control)", not skip_qc),
            ("物种分类 (taxonomic-profiling)", not skip_taxonomy),
            ("多样性分析 (diversity-analysis)", not skip_diversity),
            ("功能注释 (functional-annotation)", not skip_functional),
            ("结果汇总 (summarize-results)", True),
        ]

        click.secho("=== Resolved Plan (dry-run) ===", fg="cyan")
        click.echo(f"输入目录: {input_dir}")
        click.echo(f"输出目录: {results_dir}")
        click.echo(f"线程数: {threads}")
        click.echo(f"KneadData 数据库: {kneaddata_db or '(未提供)'}")
        click.echo(f"Kraken2 数据库: {kraken2_db or '(未提供)'}")
        click.secho(
            "参数来源 (CLI > analysis.yaml > databases.yaml > 默认):", fg="cyan"
        )
        for name in (
            "input_dir",
            "results_dir",
            "threads",
            "kneaddata_db",
            "kraken2_db",
        ):
            click.echo(f"  {name}: {sources[name]}")
        click.secho("执行阶段:", fg="cyan")
        for stage, enabled in stages:
            click.echo(f"  - {stage}: {'执行' if enabled else '跳过'}")
        click.echo("不执行任何实际操作。")
        return

    _invoke(
        "完整分析流程",
        lambda: run_full_pipeline(
            input_dir,
            results_dir,
            threads,
            kneaddata_db,
            kraken2_db,
            skip_qc=skip_qc,
            skip_taxonomy=skip_taxonomy,
            skip_functional=skip_functional,
            skip_diversity=skip_diversity,
            metadata_path=metadata_path,
        ),
    )


@main.group()
def run() -> None:
    """运行一个分析模块."""


@run.command("quality-control")
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="包含 FASTQ 文件的输入目录.",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False),
    help="存放 QC 结果的输出目录.",
)
@click.option(
    "--threads",
    default=DEFAULT_THREADS,
    type=int,
    help=f"使用的线程数 (默认: {DEFAULT_THREADS}).",
)
@click.option(
    "--kneaddata-db",
    required=True,
    type=click.Path(exists=True, dir_okay=True),
    help="KneadData 参考数据库的路径.",
)
@click.pass_context
def quality_control(
    ctx: click.Context, input_dir: str, output_dir: str, threads: int, kneaddata_db: str
) -> None:
    """运行质量控制 (FastQC + KneadData)."""
    if ctx.obj.get("dry_run"):
        _print_dry_run(
            "Dry Run: Quality Control",
            {
                "输入目录": input_dir,
                "输出目录": output_dir,
                "线程数": threads,
                "KneadData 数据库": kneaddata_db,
            },
        )
        return

    _invoke(
        "质量控制模块",
        lambda: run_qc(input_dir, output_dir, threads, kneaddata_db),
    )


@run.command("taxonomic-profiling")
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="包含 KneadData 清理后 FASTQ 文件的输入目录.",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False),
    help="存放物种分类结果的输出目录.",
)
@click.option(
    "--threads",
    default=DEFAULT_THREADS,
    type=int,
    help=f"使用的线程数 (默认: {DEFAULT_THREADS}).",
)
@click.option(
    "--kraken2-db",
    required=True,
    type=click.Path(exists=True, dir_okay=True),
    help="Kraken2 参考数据库的路径.",
)
@click.option("--confidence", type=float, default=0.1, help="Kraken2 分类置信度阈值.")
@click.pass_context
def taxonomic_profiling(
    ctx: click.Context,
    input_dir: str,
    output_dir: str,
    threads: int,
    kraken2_db: str,
    confidence: float,
) -> None:
    """运行物种分类 (Kraken2 + Krona)."""
    if ctx.obj.get("dry_run"):
        _print_dry_run(
            "Dry Run: Taxonomic Profiling",
            {
                "输入目录": input_dir,
                "输出目录": output_dir,
                "线程数": threads,
                "Kraken2 数据库": kraken2_db,
                "置信度阈值": confidence,
            },
        )
        return

    _invoke(
        "物种分类模块",
        lambda: run_taxonomic_profiling(
            input_dir, output_dir, threads, kraken2_db, confidence
        ),
    )


@run.command("diversity-analysis")
@click.option(
    "--input-biom",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="输入的 BIOM 表文件.",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False),
    help="存放多样性分析结果的输出目录.",
)
@click.pass_context
def diversity_analysis(ctx: click.Context, input_biom: str, output_dir: str) -> None:
    """运行多样性分析 (QIIME2)."""
    if ctx.obj.get("dry_run"):
        _print_dry_run(
            "Dry Run: Diversity Analysis",
            {"输入 BIOM 文件": input_biom, "输出目录": output_dir},
        )
        return

    _invoke(
        "多样性分析模块",
        lambda: run_diversity_analysis(input_biom, output_dir),
    )


@run.command("functional-annotation")
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="包含 KneadData 清理后 FASTQ 文件的输入目录.",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False),
    help="存放功能注释结果的输出目录.",
)
@click.option(
    "--threads",
    default=DEFAULT_THREADS,
    type=int,
    help=f"使用的线程数 (默认: {DEFAULT_THREADS}).",
)
@click.pass_context
def functional_annotation(
    ctx: click.Context, input_dir: str, output_dir: str, threads: int
) -> None:
    """运行功能注释 (HUMAnN)."""
    if ctx.obj.get("dry_run"):
        _print_dry_run(
            "Dry Run: Functional Annotation",
            {
                "输入目录": input_dir,
                "输出目录": output_dir,
                "线程数": threads,
            },
        )
        return

    _invoke(
        "功能注释模块",
        lambda: run_functional_annotation(input_dir, output_dir, threads),
    )


@run.command("summarize-results")
@click.option(
    "--results-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="包含所有分析结果的根目录.",
)
@click.option(
    "--output-file",
    required=True,
    type=click.Path(dir_okay=False),
    help="输出的 HTML 报告文件路径.",
)
@click.pass_context
def summarize_results(ctx: click.Context, results_dir: str, output_file: str) -> None:
    """汇总所有分析结果并生成 HTML 报告."""
    if ctx.obj.get("dry_run"):
        _print_dry_run(
            "Dry Run: Summarize Results",
            {"结果目录": results_dir, "输出文件": output_file},
        )
        return

    _invoke(
        "结果汇总模块",
        lambda: run_summarize(results_dir, output_file),
    )


if __name__ == "__main__":
    main()
