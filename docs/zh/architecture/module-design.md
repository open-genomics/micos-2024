---
title: 模块设计原理
---

# 模块设计原理

本文档描述 MICOS-2024 的实际代码架构，面向贡献者。

## 设计理念

各处理模块遵循**深层模块**原则：对外暴露简洁的函数接口，内部隐藏样本发现、命令构建、错误处理等细节。调用者只需提供输入目录、输出目录和必要参数。

## CLI 层

`micos/cli.py` 使用 Click 框架，结构为两层命令组：

- `main` group：`validate-config`、`full-run`
- `run` group：`quality-control`、`taxonomic-profiling`、`diversity-analysis`、`functional-annotation`、`summarize-results`

全局选项包括 `--config`、`--log-file`、`--verbose`、`--dry-run`。`full-run` 额外支持 `--skip-qc`、`--skip-taxonomy`、`--skip-functional`、`--skip-diversity` 跳过指定阶段。

## 编排层

`micos/full_run.py` 的 `run_full_pipeline()` 函数串行调用五个阶段模块：

```
run_qc → run_taxonomic_profiling → run_diversity_analysis → run_functional_annotation → run_summarize
```

各阶段间通过 `results/` 子目录传递中间产物：KneadData 清洗读段 -> Kraken2 报告 -> BIOM 表 -> 多样性产物 -> HTML 汇总报告。

## 架构图

<ArchitectureDiagram />

## 模块处理模式

每个处理模块是一个 `run_*()` 函数，遵循统一模式：

1. 用 `Sample.discover_paired()` 或 `Sample.discover_cleaned()` 发现样本
2. 串行遍历样本，为每个样本构建工具命令
3. 调用 `run_command_live()` 执行命令并实时输出
4. 收集结果文件（如合并所有 `.report` 生成 BIOM 表）

以 `taxonomic_profiling.py` 为例：

```python
def run_taxonomic_profiling(input_dir, output_dir, threads, kraken2_db, confidence=0.1, metadata_path=None):
    samples = Sample.discover_cleaned(input_path, metadata_path=metadata_arg)
    for sample in samples:
        kraken2_cmd = ["kraken2", "--db", str(kraken2_db), "--paired", ...]
        run_command_live(kraken2_cmd)
    # 合并报告生成 BIOM + Krona
```

## Sample 数据模型

`micos/sample.py` 的 `Sample` 是一个 `@dataclass`：

```python
@dataclass
class Sample:
    name: str
    r1_path: Path
    r2_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_paired(self) -> bool: ...
    @property
    def files(self) -> list[Path]: ...
```

样本发现通过类方法完成：

- `Sample.discover_paired(input_dir)` — 发现原始配对 FASTQ（R1/R2）
- `Sample.discover_cleaned(input_dir)` — 发现 KneadData 清洗后的配对读段
- `Sample.load_metadata(path)` — 加载 TSV 元数据，按 `sample-id` 列关联

## 配置系统

`micos/config.py` 使用 Pydantic 模型提供类型安全的配置：

```python
class AnalysisConfig(BaseModel):
    paths: PathsConfig          # input_dir, output_dir, databases
    resources: ResourcesConfig  # max_threads

    @classmethod
    def from_yaml(cls, path: Path) -> "AnalysisConfig": ...
```

数据库路径通过 `merge_databases_config()` 从 `analysis.yaml` 和 `databases.yaml` 合并提取，支持两种来源：`paths.databases` 直接配置或 `databases.yaml` 分层配置。

## 工具执行

`micos/utils.py` 的 `run_command_live()` 用 `subprocess.Popen` 执行外部工具，实时打印 stdout，失败时抛出 `subprocess.CalledProcessError`。各模块捕获该异常后记录错误日志并重新抛出。

## 返回码

`micos/cli.py` 定义了显式退出码常量：

| 常量 | 码 | 含义 |
| --- | --- | --- |
| `EXIT_SUCCESS` | 0 | 成功 |
| `EXIT_GENERAL_ERROR` | 1 | 一般错误 |
| `EXIT_INVALID_ARGS` | 2 | 参数无效 |
| `EXIT_CONFIG_ERROR` | 3 | 配置错误 |
| `EXIT_MISSING_DEPS` | 4 | 缺少依赖 |
| `EXIT_DB_ERROR` | 5 | 数据库错误 |
| `EXIT_IO_ERROR` | 6 | I/O 错误 |
| `EXIT_INTERRUPTED` | 130 | 用户中断 (SIGINT) |

## 扩展点

### 添加新分析模块

1. 在 `micos/` 创建模块文件，实现 `run_*()` 函数
2. 在 `cli.py` 的 `run` group 中添加对应命令
3. 在 `full_run.py` 中接入编排
4. 编写 `tests/test_*.py`
5. 更新文档

### 添加专家分析脚本

`scripts/` 下的脚本（如 `network_analysis.py`、`phylogenetic_analysis.py`）是主 CLI 之外的扩展能力，不属于稳定公共接口。新增时在 `scripts/README.md` 中说明用途和依赖。
