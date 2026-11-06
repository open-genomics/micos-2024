# -*- coding: utf-8 -*-
"""样本数据模型模块。

提供样本 (Sample) 领域对象，统一样本发现和处理逻辑。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing_extensions import Self


def _canonical_metadata_field(field: str) -> str:
    """规范化常见样本 ID 表头写法。"""
    key = field.lstrip("#").strip()
    if key.lower() in {"sampleid", "sample-id", "sample_id"}:
        return "sample-id"
    return key


def _resolve_metadata_id_column(
    header_fields: list[str], sample_id_column: str
) -> str | None:
    """在表头中解析样本 ID 列，兼容大小写和连字符/下划线差异。"""
    if sample_id_column in header_fields:
        return sample_id_column
    target = _canonical_metadata_field(sample_id_column)
    for column in header_fields:
        if _canonical_metadata_field(column) == target:
            return column
    return None


@dataclass
class Sample:
    """样本数据模型 - 表示一个测序样本。

    这是一个**深层模块**，隐藏了样本发现和验证的复杂性：
    - 调用者只需知道样本名和路径
    - 样本发现、配对验证等逻辑被隐藏

    Attributes:
        name: 样本名称（唯一标识符）
        r1_path: R1 端 FASTQ 文件路径
        r2_path: R2 端 FASTQ 文件路径（单端测序时为 None）
        metadata: 样本元数据（可选）
    """

    name: str
    r1_path: Path
    r2_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def load_metadata(
        metadata_path: Path,
        sample_id_column: str = "sample-id",
    ) -> dict[str, dict[str, Any]]:
        """加载样本元数据 TSV 文件。

        支持 `config/samples.tsv.template` 格式：首行为表头，以 `#` 开头的行
        视为注释跳过。同时兼容 QIIME 风格的 `#SampleID` 表头。

        Args:
            metadata_path: TSV 元数据文件路径
            sample_id_column: 样本 ID 列名（默认 "sample-id"）

        Returns:
            样本 ID 到元数据字典的映射；文件不存在时返回空字典

        Raises:
            ValueError: 表头缺少 sample_id_column 列
        """
        if not metadata_path.exists():
            return {}

        lines = metadata_path.read_text(encoding="utf-8").splitlines()
        header_index: int | None = None
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            # QIIME 风格表头以 # 开头，但它是表头而不是注释。
            if stripped.startswith("#SampleID") or stripped.startswith("#sample-id"):
                header_index = index
                break
            if stripped.startswith("#"):
                continue
            header_index = index
            break

        if header_index is None:
            return {}

        header_fields = [
            _canonical_metadata_field(field)
            for field in lines[header_index].lstrip("#").split("\t")
        ]
        id_column = _resolve_metadata_id_column(header_fields, sample_id_column)
        if id_column is None:
            raise ValueError(
                f"元数据文件缺少样本 ID 列 '{sample_id_column}'，"
                f"实际列: {header_fields}"
            )

        data_lines = [
            line
            for line in lines[header_index + 1 :]
            if line.strip() and not line.lstrip().startswith("#")
        ]
        reader = csv.DictReader(data_lines, fieldnames=header_fields, delimiter="\t")

        metadata: dict[str, dict[str, Any]] = {}
        for row in reader:
            sample_id = (row.get(id_column) or "").strip()
            if not sample_id:
                continue
            metadata[sample_id] = {
                key: value for key, value in row.items() if key != id_column
            }
        return metadata

    @classmethod
    def discover_paired(
        cls,
        input_dir: Path,
        r1_pattern: str = "*_R1.fastq.gz",
        r2_suffix: str = "_R2.fastq.gz",
        metadata_path: Path | None = None,
        sample_id_column: str = "sample-id",
    ) -> list[Self]:
        """发现配对的 FASTQ 样本。

        Args:
            input_dir: 输入目录
            r1_pattern: R1 文件的 glob 模式
            r2_suffix: R2 文件的后缀（从 R1 文件名推导）
            metadata_path: 可选的元数据 TSV 文件路径，提供后按 sample-id
                列与发现的样本名 join，填充 Sample.metadata
            sample_id_column: 元数据文件中样本 ID 列名

        Returns:
            发现的样本列表

        Example:
            >>> samples = Sample.discover_paired(
            ...     Path("data/"),
            ...     metadata_path=Path("config/samples.tsv"),
            ... )
            >>> for sample in samples:
            ...     print(f"{sample.name}: {sample.r1_path.name}, group={sample.metadata.get('group')}")
        """
        metadata_map = cls._optional_metadata(metadata_path, sample_id_column)
        r1_suffix = r1_pattern.lstrip("*")
        samples: list[Self] = []

        for r1_file in sorted(input_dir.glob(r1_pattern)):
            name = cls._extract_sample_name(r1_file.name, r1_pattern)
            r1_name = r1_file.name
            if r1_suffix and r1_name.endswith(r1_suffix):
                r2_name = r1_name[: -len(r1_suffix)] + r2_suffix
            else:
                r2_name = r1_name.replace("_R1", "_R2", 1)
            samples.append(
                cls._from_discovered(
                    name, r1_file, r1_file.parent / r2_name, metadata_map
                )
            )

        return samples

    @classmethod
    def discover_cleaned(
        cls,
        input_dir: Path,
        pattern: str = "*_paired_1.fastq",
        metadata_path: Path | None = None,
        sample_id_column: str = "sample-id",
    ) -> list[Self]:
        """发现清洗后的配对样本（KneadData 输出）。

        Args:
            input_dir: 输入目录（通常是 kneaddata 输出目录）
            pattern: _paired_1 文件的 glob 模式
            metadata_path: 可选的元数据 TSV 文件路径，提供后按 sample-id
                列与发现的样本名 join，填充 Sample.metadata
            sample_id_column: 元数据文件中样本 ID 列名

        Returns:
            发现的样本列表
        """
        metadata_map = cls._optional_metadata(metadata_path, sample_id_column)
        samples: list[Self] = []

        for r1_file in sorted(input_dir.glob(pattern)):
            r2_name = r1_file.name.replace("_paired_1", "_paired_2")
            samples.append(
                cls._from_discovered(
                    cls._extract_cleaned_sample_name(r1_file.name),
                    r1_file,
                    r1_file.parent / r2_name,
                    metadata_map,
                )
            )

        return samples

    @classmethod
    def _optional_metadata(
        cls,
        metadata_path: Path | None,
        sample_id_column: str,
    ) -> dict[str, dict[str, Any]]:
        """加载可选元数据；未提供路径时返回空映射."""
        if metadata_path is None:
            return {}
        return cls.load_metadata(metadata_path, sample_id_column)

    @classmethod
    def _from_discovered(
        cls,
        name: str,
        r1_path: Path,
        r2_path: Path,
        metadata_map: dict[str, dict[str, Any]],
    ) -> Self:
        """由发现到的 R1/R2 路径构建样本，R2 缺失时视为单端."""
        return cls(
            name=name,
            r1_path=r1_path,
            r2_path=r2_path if r2_path.exists() else None,
            metadata=metadata_map.get(name, {}),
        )

    @staticmethod
    def _extract_sample_name(filename: str, pattern: str) -> str:
        """从文件名提取样本名。

        Args:
            filename: 文件名
            pattern: glob 模式（用于参考）

        Returns:
            样本名

        Example:
            >>> Sample._extract_sample_name("sample001_R1.fastq.gz", "*_R1.fastq.gz")
            'sample001'
        """
        # 移除扩展名
        name = filename
        for ext in [".fastq.gz", ".fq.gz", ".fastq", ".fq"]:
            if name.endswith(ext):
                name = name[: -len(ext)]
                break

        # 移除 _R1 或 _R2 后缀（仅移除末尾一次，避免误删样本名中的 _R1 子串）
        for suffix in ("_R1", "_R2"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break

        return name

    @staticmethod
    def _extract_cleaned_sample_name(filename: str) -> str:
        """从清洗后的文件名提取样本名。

        Args:
            filename: 文件名（如 sample001_paired_1.fastq）

        Returns:
            样本名
        """
        # 移除 _paired_1 或 _paired_2 后缀
        name = filename
        for suffix in ["_paired_1.fastq", "_paired_2.fastq"]:
            if suffix in name:
                name = name.replace(suffix, "")
                break

        return name

    @property
    def is_paired(self) -> bool:
        """检查是否为双端测序。"""
        return self.r2_path is not None

    @property
    def files(self) -> list[Path]:
        """获取所有 FASTQ 文件路径。"""
        files = [self.r1_path]
        if self.r2_path:
            files.append(self.r2_path)
        return files

    def validate(self) -> bool:
        """验证样本文件是否存在。

        Returns:
            True 如果所有文件都存在

        Raises:
            FileNotFoundError: 如果文件不存在
        """
        for file_path in self.files:
            if not file_path.exists():
                raise FileNotFoundError(f"样本文件不存在: {file_path}")
        return True

    def __str__(self) -> str:
        """返回样本的字符串表示。"""
        if self.is_paired and self.r2_path is not None:
            return (
                f"Sample({self.name}, paired: {self.r1_path.name}, {self.r2_path.name})"
            )
        return f"Sample({self.name}, single: {self.r1_path.name})"

    def __repr__(self) -> str:
        """返回样本的详细表示。"""
        return f"Sample(name={self.name!r}, r1_path={self.r1_path!r}, r2_path={self.r2_path!r})"
