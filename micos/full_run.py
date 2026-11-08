# -*- coding: utf-8 -*-
"""完整分析流程的编排模块."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

from micos.diversity_analysis import run_diversity_analysis
from micos.errors import MissingInputError
from micos.functional_annotation import run_functional_annotation
from micos.manifest import RunManifest, StageRecord, utc_now
from micos.quality_control import run_qc
from micos.summarize_results import run_summarize
from micos.taxonomic_profiling import run_taxonomic_profiling

logger = logging.getLogger(__name__)

QUALITY_CONTROL_DIR = "quality_control"
TAXONOMIC_PROFILING_DIR = "taxonomic_profiling"
DIVERSITY_ANALYSIS_DIR = "diversity_analysis"
FUNCTIONAL_ANNOTATION_DIR = "functional_annotation"
SUMMARY_REPORT_NAME = "micos_summary_report.html"


def _record_skip(name: str, manifest: RunManifest, reason: str) -> None:
    """记录被跳过的阶段。"""
    now = utc_now()
    manifest.stages.append(
        StageRecord(
            name=name,
            status="skipped",
            started_at=now,
            finished_at=now,
            duration_sec=0.0,
            error=reason,
        )
    )
    manifest.write()


def _run_stage(
    name: str,
    action: Callable[[], None],
    manifest: RunManifest,
) -> None:
    """执行单个分析阶段，记录状态并在失败时保留上下文."""
    record = StageRecord(name=name, status="running", started_at=utc_now())
    manifest.stages.append(record)
    manifest.write()
    started = time.perf_counter()

    try:
        action()
    except Exception as exc:
        record.status = "failed"
        record.error = str(exc)
        record.finished_at = utc_now()
        record.duration_sec = round(time.perf_counter() - started, 3)
        manifest.write()
        logger.error("%s步骤失败: %s", name, exc, exc_info=True)
        raise
    else:
        record.status = "completed"
        record.finished_at = utc_now()
        record.duration_sec = round(time.perf_counter() - started, 3)
        manifest.write()


def run_full_pipeline(
    input_dir: str,
    results_dir: str,
    threads: int,
    kneaddata_db: str | None,
    kraken2_db: str | None,
    skip_qc: bool = False,
    skip_taxonomy: bool = False,
    skip_functional: bool = False,
    skip_diversity: bool = False,
    metadata_path: str | None = None,
) -> None:
    """按顺序执行完整的分析流程.

    Args:
        input_dir: 输入 FASTQ 文件目录
        results_dir: 结果输出目录
        threads: 线程数
        kneaddata_db: KneadData 数据库路径
        kraken2_db: Kraken2 数据库路径
        skip_qc: 跳过质量控制步骤
        skip_taxonomy: 跳过物种分类步骤
        skip_functional: 跳过功能注释步骤
        skip_diversity: 跳过多样性分析步骤
        metadata_path: 可选的样本元数据 TSV 路径，传递给各模块用于
            按 sample-id 列 join 填充 Sample.metadata
    """
    logger.info("MICOS 完整分析流程开始...")
    if metadata_path:
        logger.info("使用样本元数据: %s", metadata_path)

    results_root = Path(results_dir)
    results_root.mkdir(parents=True, exist_ok=True)

    manifest = RunManifest.create(
        input_dir=input_dir,
        results_dir=results_root,
        parameters={
            "threads": threads,
            "skip_qc": skip_qc,
            "skip_taxonomy": skip_taxonomy,
            "skip_functional": skip_functional,
            "skip_diversity": skip_diversity,
            "metadata_path": metadata_path,
        },
        kneaddata_db=kneaddata_db,
        kraken2_db=kraken2_db,
    )
    manifest.write()
    logger.info("运行清单: %s", results_root / "run_manifest.json")

    qc_output_dir = results_root / QUALITY_CONTROL_DIR
    tax_output_dir = results_root / TAXONOMIC_PROFILING_DIR
    div_output_dir = results_root / DIVERSITY_ANALYSIS_DIR
    func_output_dir = results_root / FUNCTIONAL_ANNOTATION_DIR
    # 跳过 QC 时没有 quality_control/kneaddata 产物；下游直接把
    # --input-dir 当作已清洗数据（需符合 *_paired_1.fastq 命名）。
    kneaddata_output = Path(input_dir) if skip_qc else qc_output_dir / "kneaddata"

    try:
        if skip_qc:
            _record_skip("质量控制", manifest, "--skip-qc")
        else:
            if kneaddata_db is None:
                raise MissingInputError(
                    "kneaddata_db 不能为 None（skip_qc=False 时必须提供）"
                )
            _run_stage(
                "质量控制",
                partial(
                    run_qc,
                    input_dir=input_dir,
                    output_dir=str(qc_output_dir),
                    threads=threads,
                    kneaddata_db=kneaddata_db,
                    metadata_path=metadata_path,
                ),
                manifest,
            )

        if skip_taxonomy:
            _record_skip("物种分类", manifest, "--skip-taxonomy")
        else:
            if kraken2_db is None:
                raise MissingInputError(
                    "kraken2_db 不能为 None（skip_taxonomy=False 时必须提供）"
                )
            _run_stage(
                "物种分类",
                partial(
                    run_taxonomic_profiling,
                    input_dir=str(kneaddata_output),
                    output_dir=str(tax_output_dir),
                    threads=threads,
                    kraken2_db=kraken2_db,
                    metadata_path=metadata_path,
                ),
                manifest,
            )

        if skip_diversity:
            _record_skip("多样性分析", manifest, "--skip-diversity")
        else:
            biom_file = tax_output_dir / "feature-table.biom"
            if not biom_file.exists():
                raise MissingInputError(
                    f"未找到多样性分析所需的 BIOM 文件: {biom_file}。"
                    "使用 --skip-taxonomy 时必须预先提供该文件；"
                    "全新运行请同时跳过依赖它的 --skip-diversity。"
                )
            _run_stage(
                "多样性分析",
                partial(
                    run_diversity_analysis,
                    input_biom=str(biom_file),
                    output_dir=str(div_output_dir),
                ),
                manifest,
            )

        if skip_functional:
            _record_skip("功能注释", manifest, "--skip-functional")
        else:
            _run_stage(
                "功能注释",
                partial(
                    run_functional_annotation,
                    input_dir=str(kneaddata_output),
                    output_dir=str(func_output_dir),
                    threads=threads,
                    metadata_path=metadata_path,
                ),
                manifest,
            )

        # 先写入最终状态，再生成报告，避免报告页显示“running”。
        summary_started_at = utc_now()
        summary_started = time.perf_counter()
        manifest.status = "completed"
        manifest.finished_at = utc_now()
        manifest.write()
        try:
            run_summarize(
                results_dir=str(results_root),
                output_file=str(results_root / SUMMARY_REPORT_NAME),
            )
        except Exception as exc:
            manifest.stages.append(
                StageRecord(
                    name="结果汇总",
                    status="failed",
                    started_at=summary_started_at,
                    finished_at=utc_now(),
                    duration_sec=round(time.perf_counter() - summary_started, 3),
                    error=str(exc),
                )
            )
            manifest.status = "failed"
            manifest.finished_at = utc_now()
            manifest.write()
            raise
        else:
            manifest.stages.append(
                StageRecord(
                    name="结果汇总",
                    status="completed",
                    started_at=summary_started_at,
                    finished_at=utc_now(),
                    duration_sec=round(time.perf_counter() - summary_started, 3),
                )
            )
            manifest.write()
    except Exception:
        manifest.status = "failed"
        manifest.finished_at = utc_now()
        manifest.write()
        raise
    else:
        manifest.status = "completed"
        manifest.finished_at = utc_now()
        manifest.write()

    logger.info("输入目录: %s", input_dir)
    logger.info("结果目录: %s", results_dir)
    logger.info("线程数: %s", threads)
    logger.info("MICOS 完整分析流程已成功完成!")
