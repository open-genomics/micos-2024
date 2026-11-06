# -*- coding: utf-8 -*-
"""功能注释模块 (HUMAnN)。

该模块是**深层模块**，隐藏了功能注释的复杂性：
- 调用者只需提供输入目录和配置
- 样本发现、文件合并、工具调用等逻辑被隐藏
"""

from __future__ import annotations

import gzip
import logging
import shutil
import subprocess
from pathlib import Path

from micos.errors import NoSamplesError
from micos.sample import Sample
from micos.utils import run_command_live

logger = logging.getLogger(__name__)


def run_functional_annotation(
    input_dir: str | Path,
    output_dir: str | Path,
    threads: int,
    metadata_path: str | Path | None = None,
) -> None:
    """执行功能注释 (HUMAnN).

    这是一个深层模块的接口，调用者只需提供必要的配置，
    样本发现、文件合并、工具调用等细节被隐藏。

    Args:
        input_dir: 输入目录（KneadData 清理后的 FASTQ 文件）
        output_dir: 输出目录
        threads: 线程数
        metadata_path: 可选的样本元数据 TSV 路径，按 sample-id 列
            与发现的样本名 join 填充 Sample.metadata

    Raises:
        subprocess.CalledProcessError: 工具执行失败时抛出
        FileNotFoundError: 工具未安装时抛出
    """
    logger.info("步骤 4: 开始功能注释分析...")

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    temp_input_path = output_path / "temp_humann_input"
    temp_input_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 使用 Sample 类发现清洗后的样本
    metadata_arg = Path(metadata_path) if metadata_path else None
    samples = Sample.discover_cleaned(input_path, metadata_path=metadata_arg)
    if not samples:
        raise NoSamplesError(
            f"在 {input_path} 中未找到 KneadData 清洗后的配对样本；"
            "期望命名形如 sample_paired_1.fastq / sample_paired_2.fastq。"
        )

    # 2. 为每个样本准备 HUMAnN 输入并运行
    for sample in samples:
        logger.info(f"处理样本: {sample.name}")

        # 查找 unmatched 文件（如果存在）
        unmatched1_file = sample.r1_path.parent / f"{sample.name}_unmatched_1.fastq"
        unmatched2_file = sample.r1_path.parent / f"{sample.name}_unmatched_2.fastq"

        concatenated_file = temp_input_path / f"{sample.name}_concatenated.fastq.gz"
        logger.info(f"合并样本 {sample.name} 的 reads 到 {concatenated_file}")

        # 合并所有 reads
        files_to_concat: list[Path] = [sample.r1_path]
        if sample.is_paired and sample.r2_path is not None:
            files_to_concat.append(sample.r2_path)
        if unmatched1_file.exists():
            files_to_concat.append(unmatched1_file)
        if unmatched2_file.exists():
            files_to_concat.append(unmatched2_file)

        with gzip.open(concatenated_file, "wb") as f_out:
            for f_in_path in files_to_concat:
                opener = gzip.open if f_in_path.suffix == ".gz" else open
                with opener(f_in_path, "rb") as f_in:
                    shutil.copyfileobj(f_in, f_out)

        # 运行 HUMAnN
        logger.info(f"--> 正在为样本 {sample.name} 运行 HUMAnN...")
        humann_cmd = [
            "humann",
            "--input",
            str(concatenated_file),
            "--output",
            str(output_path),
            "--threads",
            str(threads),
            "--output-basename",
            sample.name,
        ]
        try:
            run_command_live(humann_cmd)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"HUMAnN 运行失败: {e}")
            logger.error("请确保 humann 已安装并位于系统的 PATH 中。")
            raise

    # 清理临时文件
    shutil.rmtree(temp_input_path)
    logger.info("功能注释分析完成。")
