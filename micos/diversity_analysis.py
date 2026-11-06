# -*- coding: utf-8 -*-
"""多样性分析模块 (QIIME2)。

该模块是**深层模块**，隐藏了多样性分析的复杂性：
- 调用者只需提供 BIOM 文件和输出目录
- QIIME2 命令构建、执行、结果收集等逻辑被隐藏
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from micos.errors import MissingInputError
from micos.utils import run_command_live

logger = logging.getLogger(__name__)


def run_diversity_analysis(
    input_biom: str | Path,
    output_dir: str | Path,
) -> None:
    """执行多样性分析 (QIIME2).

    这是一个深层模块的接口，调用者只需提供必要的配置，
    QIIME2 命令构建、执行、结果收集等细节被隐藏。

    Args:
        input_biom: 输入的 BIOM 表文件
        output_dir: 输出目录

    Raises:
        subprocess.CalledProcessError: 工具执行失败时抛出
        FileNotFoundError: 工具未安装时抛出
    """
    logger.info("步骤 3: 开始多样性分析...")

    input_biom_path = Path(input_biom)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not input_biom_path.exists():
        raise MissingInputError(f"未找到多样性分析所需的 BIOM 文件: {input_biom_path}")

    # 1. 导入数据到 QIIME2
    logger.info("--> 正在导入 BIOM 表到 QIIME2...")
    feature_table_qza = output_path / "feature-table.qza"
    import_cmd = [
        "qiime",
        "tools",
        "import",
        "--input-path",
        str(input_biom_path),
        "--type",
        "FeatureTable[Frequency]",
        "--output-path",
        str(feature_table_qza),
    ]
    try:
        run_command_live(import_cmd)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"QIIME2 BIOM 导入失败: {e}")
        logger.error("请确保 qiime 已安装并位于系统的 PATH 中。")
        raise

    # 2. Alpha 多样性
    logger.info("--> 正在计算 Alpha 多样性 (Shannon)...")
    alpha_div_qza = output_path / "shannon.qza"
    alpha_cmd = [
        "qiime",
        "diversity",
        "alpha",
        "--i-table",
        str(feature_table_qza),
        "--p-metric",
        "shannon",
        "--o-alpha-diversity",
        str(alpha_div_qza),
    ]
    try:
        run_command_live(alpha_cmd)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"QIIME2 Alpha 多样性分析失败: {e}")
        raise

    logger.info("--> 正在导出 Alpha 多样性表...")
    alpha_export_dir = output_path / "alpha_diversity"
    alpha_export_dir.mkdir(parents=True, exist_ok=True)
    run_command_live(
        [
            "qiime",
            "tools",
            "export",
            "--input-path",
            str(alpha_div_qza),
            "--output-path",
            str(alpha_export_dir),
        ]
    )

    # 3. Beta 多样性
    logger.info("--> 正在计算 Beta 多样性 (Bray-Curtis)...")
    beta_div_qza = output_path / "bray-curtis.qza"
    beta_cmd = [
        "qiime",
        "diversity",
        "beta",
        "--i-table",
        str(feature_table_qza),
        "--p-metric",
        "braycurtis",
        "--o-distance-matrix",
        str(beta_div_qza),
    ]
    try:
        run_command_live(beta_cmd)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"QIIME2 Beta 多样性分析失败: {e}")
        raise

    logger.info("--> 正在导出 Beta 距离矩阵...")
    beta_export_dir = output_path / "beta_diversity"
    beta_export_dir.mkdir(parents=True, exist_ok=True)
    run_command_live(
        [
            "qiime",
            "tools",
            "export",
            "--input-path",
            str(beta_div_qza),
            "--output-path",
            str(beta_export_dir),
        ]
    )

    logger.info("多样性分析完成。")
