# -*- coding: utf-8 -*-
"""测试样本数据模型模块。"""

from __future__ import annotations

from pathlib import Path

import pytest

from micos.sample import Sample


class TestSample:
    """测试 Sample 类。"""

    def test_create_paired_sample(self) -> None:
        """创建双端样本。"""
        r1 = Path("data/sample001_R1.fastq.gz")
        r2 = Path("data/sample001_R2.fastq.gz")

        sample = Sample(name="sample001", r1_path=r1, r2_path=r2)

        assert sample.name == "sample001"
        assert sample.r1_path == r1
        assert sample.r2_path == r2
        assert sample.is_paired is True

    def test_create_single_end_sample(self) -> None:
        """创建单端样本。"""
        r1 = Path("data/sample001.fastq.gz")

        sample = Sample(name="sample001", r1_path=r1)

        assert sample.name == "sample001"
        assert sample.r1_path == r1
        assert sample.r2_path is None
        assert sample.is_paired is False

    def test_files_property_returns_all_paths(self) -> None:
        """files 属性应返回所有文件路径。"""
        r1 = Path("data/sample001_R1.fastq.gz")
        r2 = Path("data/sample001_R2.fastq.gz")

        sample = Sample(name="sample001", r1_path=r1, r2_path=r2)

        assert sample.files == [r1, r2]

    def test_files_property_single_end(self) -> None:
        """单端样本的 files 属性应只返回一个路径。"""
        r1 = Path("data/sample001.fastq.gz")

        sample = Sample(name="sample001", r1_path=r1)

        assert sample.files == [r1]

    def test_metadata_default_empty_dict(self) -> None:
        """元数据默认为空字典。"""
        sample = Sample(name="test", r1_path=Path("test.fastq"))

        assert sample.metadata == {}

    def test_metadata_can_be_set(self) -> None:
        """可以设置元数据。"""
        sample = Sample(
            name="test",
            r1_path=Path("test.fastq"),
            metadata={"group": "control", "batch": "A"},
        )

        assert sample.metadata["group"] == "control"
        assert sample.metadata["batch"] == "A"


class TestSampleDiscovery:
    """测试样本发现功能。"""

    def test_discover_paired_finds_samples(self, tmp_path: Path) -> None:
        """discover_paired 应发现配对的样本。"""
        # 创建测试文件
        (tmp_path / "sample001_R1.fastq.gz").write_text("r1")
        (tmp_path / "sample001_R2.fastq.gz").write_text("r2")
        (tmp_path / "sample002_R1.fastq.gz").write_text("r1")
        (tmp_path / "sample002_R2.fastq.gz").write_text("r2")

        samples = Sample.discover_paired(tmp_path)

        assert len(samples) == 2
        assert samples[0].name == "sample001"
        assert samples[1].name == "sample002"
        assert all(s.is_paired for s in samples)

    def test_discover_paired_handles_missing_r2(self, tmp_path: Path) -> None:
        """discover_paired 应处理缺失的 R2 文件。"""
        (tmp_path / "sample001_R1.fastq.gz").write_text("r1")
        # 不创建 R2 文件

        samples = Sample.discover_paired(tmp_path)

        assert len(samples) == 1
        assert samples[0].is_paired is False

    def test_discover_paired_returns_sorted_samples(self, tmp_path: Path) -> None:
        """discover_paired 应返回按名称排序的样本。"""
        (tmp_path / "sample_b_R1.fastq.gz").write_text("r1")
        (tmp_path / "sample_b_R2.fastq.gz").write_text("r2")
        (tmp_path / "sample_a_R1.fastq.gz").write_text("r1")
        (tmp_path / "sample_a_R2.fastq.gz").write_text("r2")

        samples = Sample.discover_paired(tmp_path)

        assert samples[0].name == "sample_a"
        assert samples[1].name == "sample_b"

    def test_discover_cleaned_finds_kneaddata_output(self, tmp_path: Path) -> None:
        """discover_cleaned 应发现 KneadData 输出的样本。"""
        (tmp_path / "sample001_paired_1.fastq").write_text("r1")
        (tmp_path / "sample001_paired_2.fastq").write_text("r2")
        (tmp_path / "sample002_paired_1.fastq").write_text("r1")
        (tmp_path / "sample002_paired_2.fastq").write_text("r2")

        samples = Sample.discover_cleaned(tmp_path)

        assert len(samples) == 2
        assert samples[0].name == "sample001"
        assert samples[1].name == "sample002"

    def test_discover_empty_directory(self, tmp_path: Path) -> None:
        """空目录应返回空列表。"""
        samples = Sample.discover_paired(tmp_path)

        assert samples == []


class TestSampleMetadata:
    """测试样本元数据加载与 join 功能。"""

    def test_load_metadata_basic(self, tmp_path: Path) -> None:
        """load_metadata 应正确加载 TSV 元数据。"""
        tsv = tmp_path / "samples.tsv"
        tsv.write_text(
            "sample-id\tgroup\ttreatment\n"
            "S001\tControl\tNone\n"
            "S002\tTreatment\tDrugA\n",
            encoding="utf-8",
        )

        metadata = Sample.load_metadata(tsv)

        assert "S001" in metadata
        assert metadata["S001"]["group"] == "Control"
        assert metadata["S001"]["treatment"] == "None"
        assert metadata["S002"]["group"] == "Treatment"
        # sample-id 列不应出现在值字典中
        assert "sample-id" not in metadata["S001"]

    def test_load_metadata_skips_comment_lines(self, tmp_path: Path) -> None:
        """load_metadata 应跳过以 # 开头的注释行。"""
        tsv = tmp_path / "samples.tsv"
        tsv.write_text(
            "# 这是注释\n"
            "# 列说明：sample-id | group\n"
            "sample-id\tgroup\n"
            "S001\tControl\n",
            encoding="utf-8",
        )

        metadata = Sample.load_metadata(tsv)

        assert metadata == {"S001": {"group": "Control"}}

    def test_load_metadata_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """文件不存在时应返回空字典。"""
        metadata = Sample.load_metadata(tmp_path / "nonexistent.tsv")

        assert metadata == {}

    def test_load_metadata_missing_id_column_raises(self, tmp_path: Path) -> None:
        """表头缺少 sample-id 列时应抛出 ValueError。"""
        tsv = tmp_path / "samples.tsv"
        tsv.write_text("id\tgroup\nS001\tControl\n", encoding="utf-8")

        with pytest.raises(ValueError, match="sample-id"):
            Sample.load_metadata(tsv)

    def test_load_metadata_custom_id_column(self, tmp_path: Path) -> None:
        """应支持自定义 sample_id_column。"""
        tsv = tmp_path / "samples.tsv"
        tsv.write_text("id\tgroup\nS001\tControl\n", encoding="utf-8")

        metadata = Sample.load_metadata(tsv, sample_id_column="id")

        assert metadata == {"S001": {"group": "Control"}}

    def test_load_metadata_empty_file_returns_empty(self, tmp_path: Path) -> None:
        """空文件应返回空字典。"""
        tsv = tmp_path / "samples.tsv"
        tsv.write_text("", encoding="utf-8")

        assert Sample.load_metadata(tsv) == {}

    def test_load_metadata_qiime_sample_id_header(self, tmp_path: Path) -> None:
        """应兼容 QIIME 风格的 #SampleID 表头。"""
        tsv = tmp_path / "metadata.tsv"
        tsv.write_text(
            "#SampleID\ttreatment\n" "S001\tControl\n" "S002\tDrugA\n",
            encoding="utf-8",
        )

        metadata = Sample.load_metadata(tsv)

        assert metadata == {
            "S001": {"treatment": "Control"},
            "S002": {"treatment": "DrugA"},
        }

    def test_load_metadata_bundled_example(self) -> None:
        """仓库自带示例元数据应可直接加载。"""
        project_root = Path(__file__).resolve().parents[1]
        metadata = Sample.load_metadata(
            project_root / "data" / "raw_input" / "metadata.tsv"
        )

        assert "SRR8291345_Control_T12-1" in metadata
        assert metadata["SRR8291345_Control_T12-1"]["treatment"] == "Control"

    def test_discover_paired_with_metadata_join(self, tmp_path: Path) -> None:
        """discover_paired 应按 sample-id join 元数据。"""
        # 创建 FASTQ
        (tmp_path / "S001_R1.fastq.gz").write_text("r1")
        (tmp_path / "S001_R2.fastq.gz").write_text("r2")
        (tmp_path / "S002_R1.fastq.gz").write_text("r1")
        (tmp_path / "S002_R2.fastq.gz").write_text("r2")

        # 创建元数据
        meta = tmp_path / "samples.tsv"
        meta.write_text(
            "sample-id\tgroup\ttreatment\n"
            "S001\tControl\tNone\n"
            "S002\tTreatment\tDrugA\n",
            encoding="utf-8",
        )

        samples = Sample.discover_paired(tmp_path, metadata_path=meta)

        assert len(samples) == 2
        assert samples[0].metadata["group"] == "Control"
        assert samples[1].metadata["group"] == "Treatment"
        assert samples[1].metadata["treatment"] == "DrugA"

    def test_discover_paired_metadata_partial_match(self, tmp_path: Path) -> None:
        """元数据中不存在的样本应得到空 metadata。"""
        (tmp_path / "S001_R1.fastq.gz").write_text("r1")
        (tmp_path / "S001_R2.fastq.gz").write_text("r2")
        (tmp_path / "S003_R1.fastq.gz").write_text("r1")
        (tmp_path / "S003_R2.fastq.gz").write_text("r2")

        meta = tmp_path / "samples.tsv"
        meta.write_text("sample-id\tgroup\nS001\tControl\n", encoding="utf-8")

        samples = Sample.discover_paired(tmp_path, metadata_path=meta)

        assert samples[0].name == "S001"
        assert samples[0].metadata["group"] == "Control"
        assert samples[1].name == "S003"
        assert samples[1].metadata == {}

    def test_discover_paired_without_metadata_keeps_empty(self, tmp_path: Path) -> None:
        """不传 metadata_path 时 metadata 应为空。"""
        (tmp_path / "S001_R1.fastq.gz").write_text("r1")
        (tmp_path / "S001_R2.fastq.gz").write_text("r2")

        samples = Sample.discover_paired(tmp_path)

        assert samples[0].metadata == {}

    def test_discover_cleaned_with_metadata_join(self, tmp_path: Path) -> None:
        """discover_cleaned 应支持 metadata join。"""
        (tmp_path / "S001_paired_1.fastq").write_text("r1")
        (tmp_path / "S001_paired_2.fastq").write_text("r2")

        meta = tmp_path / "samples.tsv"
        meta.write_text("sample-id\tgroup\nS001\tControl\n", encoding="utf-8")

        samples = Sample.discover_cleaned(tmp_path, metadata_path=meta)

        assert len(samples) == 1
        assert samples[0].metadata["group"] == "Control"

    def test_discover_paired_metadata_with_comments(self, tmp_path: Path) -> None:
        """元数据文件含注释行时仍应正确 join。"""
        (tmp_path / "S001_R1.fastq.gz").write_text("r1")
        (tmp_path / "S001_R2.fastq.gz").write_text("r2")

        meta = tmp_path / "samples.tsv"
        meta.write_text(
            "# 注释行\n" "sample-id\tgroup\n" "S001\tControl\n",
            encoding="utf-8",
        )

        samples = Sample.discover_paired(tmp_path, metadata_path=meta)

        assert samples[0].metadata["group"] == "Control"


class TestSampleValidation:
    """测试样本验证功能。"""

    def test_validate_existing_files(self, tmp_path: Path) -> None:
        """validate 应验证存在的文件。"""
        r1 = tmp_path / "test_R1.fastq.gz"
        r2 = tmp_path / "test_R2.fastq.gz"
        r1.write_text("r1")
        r2.write_text("r2")

        sample = Sample(name="test", r1_path=r1, r2_path=r2)

        assert sample.validate() is True

    def test_validate_missing_file_raises(self, tmp_path: Path) -> None:
        """validate 应对缺失文件抛出异常。"""
        r1 = tmp_path / "nonexistent.fastq.gz"

        sample = Sample(name="test", r1_path=r1)

        with pytest.raises(FileNotFoundError):
            sample.validate()


class TestSampleStringRepresentation:
    """测试样本的字符串表示。"""

    def test_str_paired(self) -> None:
        """双端样本的字符串表示。"""
        sample = Sample(
            name="test",
            r1_path=Path("test_R1.fastq.gz"),
            r2_path=Path("test_R2.fastq.gz"),
        )

        s = str(sample)
        assert "test" in s
        assert "paired" in s

    def test_str_single(self) -> None:
        """单端样本的字符串表示。"""
        sample = Sample(name="test", r1_path=Path("test.fastq.gz"))

        s = str(sample)
        assert "test" in s
        assert "single" in s

    def test_repr(self) -> None:
        """repr 应返回详细的表示。"""
        sample = Sample(name="test", r1_path=Path("test.fastq.gz"))

        r = repr(sample)
        assert "Sample" in r
        assert "test" in r


class TestExtractSampleName:
    """测试样本名提取功能。"""

    def test_extract_from_r1_pattern(self) -> None:
        """从 R1 文件名提取样本名。"""
        name = Sample._extract_sample_name("sample001_R1.fastq.gz", "*_R1.fastq.gz")
        assert name == "sample001"

    def test_extract_from_r2_pattern(self) -> None:
        """从 R2 文件名提取样本名。"""
        name = Sample._extract_sample_name("sample001_R2.fastq.gz", "*_R2.fastq.gz")
        assert name == "sample001"

    def test_extract_with_different_extensions(self) -> None:
        """处理不同的扩展名。"""
        assert (
            Sample._extract_sample_name("sample_R1.fq.gz", "*_R1.fastq.gz") == "sample"
        )
        assert (
            Sample._extract_sample_name("sample_R1.fastq", "*_R1.fastq.gz") == "sample"
        )

    def test_extract_cleaned_sample_name(self) -> None:
        """从清洗后的文件名提取样本名。"""
        name = Sample._extract_cleaned_sample_name("sample001_paired_1.fastq")
        assert name == "sample001"
