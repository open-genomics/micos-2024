---
title: 测试策略
---

# 测试策略

本文档描述 MICOS-2024 的实际测试方法。

## 测试理念

测试聚焦**命令拼装层**：验证各模块正确构建工具命令、正确发现样本、正确串联步骤，而不依赖实际生信工具（FastQC、Kraken2 等）的安装。这使得测试可以在任何有 Python 环境的 CI 上快速运行。

## Mock 策略

核心手段是用 pytest 的 `monkeypatch` 替换 `run_command_live`，捕获模块构建的命令列表并断言其内容：

```python
def test_run_qc_assembles_fastqc_and_kneaddata_commands(tmp_path, monkeypatch):
    commands = []

    def fake_run(cmd):
        commands.append(list(cmd))

    monkeypatch.setattr(quality_control, "run_command_live", fake_run)

    # 创建临时配对 FASTQ 文件
    (input_dir / "sample001_R1.fastq.gz").write_text("r1")
    (input_dir / "sample001_R2.fastq.gz").write_text("r2")

    quality_control.run_qc(input_dir=input_dir, output_dir=output_dir, ...)

    # 断言命令拼装正确
    assert commands[0][0] == "fastqc"
    assert commands[1][0] == "kneaddata"
```

对于需要串联后续步骤的场景（如 Kraken2 生成 `.report` 后触发 kraken-biom），mock 函数会模拟工具生成输出文件：

```python
def fake_run(cmd):
    commands.append(list(cmd))
    if cmd[0] == "kraken2":
        Path(cmd[cmd.index("--report") + 1]).write_text("report")
```

样本发现逻辑通过替换 `Sample` 类来隔离测试：

```python
class FakeSample:
    @staticmethod
    def discover_cleaned(input_dir, ...):
        captured["metadata_path"] = metadata_path
        return []
```

## 测试文件

| 测试文件 | 覆盖模块 |
| --- | --- |
| `test_cli.py` | CLI 命令注册和参数解析 |
| `test_config.py` | Pydantic 配置模型和 YAML 加载 |
| `test_sample.py` | Sample 数据模型和样本发现 |
| `test_utils.py` | run_command_live、日志、默认值提取 |
| `test_quality_control.py` | FastQC + KneadData 命令拼装 |
| `test_taxonomic_profiling.py` | Kraken2 + kraken-biom + Krona 命令拼装 |
| `test_diversity_analysis.py` | QIIME2 命令拼装 |
| `test_functional_annotation.py` | HUMAnN 命令拼装 |
| `test_summarize_results.py` | HTML 报告生成 |
| `test_full_run.py` | 流程编排和步骤跳过 |
| `test_shell_wrappers.py` | Shell 包装层回归 |
| `test_orchestration_docs.py` | 编排口径的文档一致性（CLI 唯一生产编排、WDL 实验性、不支持断点续传） |
| `test_docs_whitepaper.py` | 文档站组件和页面完整性 |

## 测试标记

`pyproject.toml` 中注册了三个 pytest 标记：

```toml
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

运行特定类型：

```bash
pytest -m unit          # 仅单元测试
pytest -m "not slow"    # 跳过慢测试
pytest tests/ -v        # 全部测试
```

## 覆盖率

CI 中覆盖率阈值为 55%：

```bash
pytest tests/ --cov=micos --cov-report=xml --cov-fail-under=55
```

生成本地覆盖率报告：

```bash
pytest tests/ --cov=micos --cov-report=html
```

## 测试数据

测试用 `tmp_path` fixture 创建临时 FASTQ 文件，不依赖外部数据集：

```python
def test_xxx(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "sample001_R1.fastq.gz").write_text("r1")
    (input_dir / "sample001_R2.fastq.gz").write_text("r2")
```

## CI 集成

GitHub Actions 在 Python 3.10/3.11 两个版本上运行测试矩阵，执行 Black、isort、Flake8、MyPy 检查和 pytest，覆盖率上传至 Codecov。
