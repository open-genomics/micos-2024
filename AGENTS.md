# AGENTS.md - MICOS-2024 项目上下文

> 本文件为 AI 编程助手提供完整的项目上下文和开发指南

## 项目身份

**MICOS-2024** (Metagenomic Intelligence and Comprehensive Omics Suite) 是一个端到端的宏基因组综合分析平台，专注于微生物组学数据分析。

| 属性 | 值 |
|------|-----|
| **组织** | open-genomics |
| **许可证** | MIT |
| **语言** | Python 3.10+ / R 4.3.0 |
| **文档** | https://lessup.github.io/micos-2024/ |

---

## 架构概览

### 核心模块

```
micos/
├── __init__.py              # 包初始化与版本号
├── cli.py                   # Click CLI 入口
├── config.py                # Pydantic 配置模型
├── sample.py                # 样本数据模型
├── full_run.py              # 完整流程编排器
├── quality_control.py       # 质量控制模块
├── taxonomic_profiling.py   # 物种分类模块
├── diversity_analysis.py    # 多样性分析模块
├── functional_annotation.py # 功能注释模块
├── summarize_results.py     # 结果汇总模块
└── utils.py                 # 通用工具函数
```

### 分析流程

```
原始 FASTQ
    │
    ▼
┌─────────────────────────────────┐
│  Stage 1: 质量控制               │
│  FastQC → KneadData             │
│  (适配体去除、宿主过滤)           │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Stage 2: 物种分类               │
│  Kraken2 → Kraken-BIOM → Krona  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Stage 3: 多样性分析             │
│  QIIME2 → Phyloseq (R)          │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Stage 4: 功能注释               │
│  HUMAnN3                        │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Stage 5: 结果汇总               │
│  HTML 报告 + 可视化图表          │
└─────────────────────────────────┘
```

### WDL 任务定义（实验性单步骤参考）

> **注意**：以下 WDL 文件是实验性单步骤参考，不是生产工作流。
> 当前没有顶层 WDL workflow、固定运行时输入或执行验证 CI。
> 生产分析请使用 `micos full-run`。

| 目录 | 步骤 | 工具 |
|------|------|------|
| `steps/01_quality_control/` | 质量控制 | FastQC |
| `steps/02_read_cleaning/` | 读长清洗 | KneadData |
| `steps/03_taxonomic_profiling_kraken/` | 物种分类 | Kraken2 |
| `steps/04_taxonomic_conversion_biom/` | BIOM 转换 | kraken-biom |
| `steps/05_taxonomic_visualization_krona/` | 可视化 | Krona |
| `steps/06_qiime2_analysis/` | 多样性分析 | QIIME2 |
| `steps/07_phyloseq_analysis/` | 统计分析 | Phyloseq (R) |
| `steps/08_megan_analysis/` | 可视化 (未集成) | MEGAN |
| `steps/09_qiime2_whole_analysis/` | 全流程 (未集成) | QIIME2 |

---

## 开发指南

### 环境设置

```bash
# 克隆项目
git clone https://github.com/open-genomics/micos-2024.git
cd micos-2024

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖（核心 + 开发工具）
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
```

### 代码风格

- **格式化**: Black (88 字符)
- **导入排序**: isort
- **Linting**: Flake8
- **类型检查**: MyPy
- **安全检查**: Bandit

### 生信工具版本固定策略

**所有生信工具版本固定，不升级**。`environment.yml` 中的版本号为唯一基准，禁止浮动版本号（`>=` / `latest`）。升级需全量回归测试后由维护者决定。

| 工具 | 固定版本 | 说明 |
|------|----------|------|
| Python | 3.10 | 主链路 + 测试基准 |
| R | 4.3.0 | scripts/ 统计分析 |
| FastQC | 0.11.9 | 质量控制 |
| KneadData | 0.12.0 | 读长清洗 |
| Kraken2 | 2.1.3 | 物种分类 |
| Krona | 2.8.1 | 可视化 |
| QIIME2 | 2024.5 | 多样性分析 |
| HUMAnN | 3.0 | 功能注释 |
| kraken-biom | 1.2.0 | BIOM 转换 (pip) |

### 测试

```bash
# 运行所有测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=micos --cov-report=html

# 特定测试标记
pytest -m "not slow" tests/
```

### 提交规范

使用 Conventional Commits:

```
feat(qc): add adapter trimming option
fix(kraken): handle empty classification results
docs: update installation guide
chore(deps): bump pandas to 2.0.0
```

---

## 关键依赖

### Python 核心 (micos/)

| 包 | 版本 | 用途 |
|---|------|------|
| click | ≥8.0.0 | CLI 框架 |
| pyyaml | ≥6.0 | 配置解析 |
| pydantic | ≥2.0.0 | 配置验证 |

### Python 扩展 (scripts/，通过 `pip install -e ".[scripts]"` 安装)

| 包 | 用途 |
|---|------|
| numpy | 数值计算 |
| pandas | 数据处理 |
| scipy | 科学计算 |
| scikit-learn | 机器学习 (network_analysis.py) |
| biopython | 序列处理 (phylogenetic_analysis.py) |
| matplotlib | 静态图表 |
| seaborn | 统计可视化 |

### R 包 (scripts/)

| 包 | 用途 |
|---|------|
| phyloseq | 微生物组数据整合 |
| DESeq2 | 差异丰度分析 |
| vegan | 群落生态学分析 |
| ggtree | 系统发育树可视化 |

---

## 配置系统

### 配置文件层次

1. `config/analysis.yaml.template` - 分析参数模板
2. `config/databases.yaml.template` - 数据库路径模板
3. `config/samples.tsv.template` - 样本信息模板

### 环境变量

| 变量 | 描述 |
|------|------|
| `MICOS_DB_ROOT` | 数据库根目录 |
| `MICOS_THREADS` | 默认线程数 |
| `MICOS_TEMP_DIR` | 临时文件目录 |
| `MICOS_DB_CHECKSUMS` | sha256sum 格式的清单文件，`scripts/download_databases.sh` 按上游归档文件名查表 |
| `MICOS_KRAKEN2_<TYPE>_SHA256` | 单个 Kraken2 归档的 SHA256，优先级高于清单 |

### 数据库下载校验

`scripts/download_databases.sh` 在解压前校验归档的 SHA256，来源优先级：
`MICOS_KRAKEN2_<TYPE>_SHA256` 环境变量 > `MICOS_DB_CHECKSUMS` 清单 > 跳过（明确告警）。

清单就是 `sha256sum` 的输出格式，文件名可含空格（上游 PlusPF 归档名就带空格与括号）：

```
<64 位十六进制>  kraken2_standard_20230605.tar.gz
<64 位十六进制> *Kraken2 PlusPF (20231230).tar.gz
```

文件名匹配先试 URL 的 basename（百分号编码已解码），再试本地保存名
`<type>.tar.gz`。**显式提供了清单却查不到条目、或清单不可读时脚本直接失败**，
不会退化成"以为校验了其实没有"。Kraken2 数据库上游不发布官方校验值，
清单需自行在可信渠道下载后生成（`sha256sum` 或 `sha256sum -b`）。

---

## 容器化

### Docker 镜像

每个分析步骤都有对应的 Dockerfile:

```bash
# 构建 Kraken2 镜像
docker build -t micos-kraken2:2.1.3 steps/03_taxonomic_profiling_kraken/
```

### Singularity 支持

```bash
# 构建 Singularity 镜像
sudo singularity build kraken2.sif steps/03_taxonomic_profiling_kraken/kraken2.def
```

---

## 常见任务

### 添加新分析模块

1. 在 `micos/` 创建模块文件
2. 编写测试 `tests/test_new_module.py`
3. 更新 `micos/full_run.py` 编排
4. 更新文档
5. （可选）在 `steps/` 创建实验性 WDL 单步骤参考

### 修改分析流程

1. 更新 `micos/full_run.py`
2. 运行回归测试
3. 更新 CHANGELOG
4. （可选）同步实验性 WDL 单步骤参考

### 添加新数据库

1. 更新 `config/databases.yaml.template`
2. 更新 `scripts/download_databases.sh`
3. 更新文档说明数据库来源

---

## 故障排除

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| Kraken2 数据库未找到 | 检查 `databases.yaml` 中的路径 |
| 内存不足 | 减少 `--threads` 或增加 swap |
| QIIME2 插件错误 | 激活正确的 QIIME2 环境 |

### 日志位置

- 分析日志: `results/logs/`
- 错误日志: `results/logs/errors.log`
- 调试模式: 设置 `--verbose` 或 `LOG_LEVEL=DEBUG`

---

## 代码模式库

### 模式 1: Shell 命令包装

```python
import subprocess
from pathlib import Path
from typing import Optional

def run_kraken2(
    input_reads: Path,
    output_dir: Path,
    db_path: Path,
    threads: int = 16,
    confidence: float = 0.1,
) -> Path:
    """运行 Kraken2 分类.
    
    Args:
        input_reads: 输入 FASTQ 文件
        output_dir: 输出目录
        db_path: Kraken2 数据库路径
        threads: 线程数
        confidence: 分类置信度阈值
        
    Returns:
        输出报告文件路径
        
    Raises:
        subprocess.CalledProcessError: 命令执行失败
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_reads.stem}.report"
    
    cmd = [
        "kraken2",
        "--db", str(db_path),
        "--output", str(output_dir / f"{input_reads.stem}.kraken"),
        "--report", str(output_file),
        "--confidence", str(confidence),
        "--threads", str(threads),
        str(input_reads),
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return output_file
```

### 模式 2: 并行样本处理

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def process_samples_parallel(
    sample_dirs: List[Path],
    output_dir: Path,
    max_workers: int = 8,
) -> Dict[str, Path]:
    """并行处理多样本.
    
    Args:
        sample_dirs: 样本目录列表
        output_dir: 输出根目录
        max_workers: 最大并行进程数
        
    Returns:
        样本名到输出路径的映射
    """
    results = {}
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_sample = {
            executor.submit(process_single_sample, sd, output_dir): sd.name
            for sd in sample_dirs
        }
        
        # 收集结果
        for future in as_completed(future_to_sample):
            sample = future_to_sample[future]
            try:
                result = future.result()
                results[sample] = result
                logger.info(f"完成样本 {sample}")
            except Exception as e:
                logger.error(f"样本 {sample} 处理失败: {e}")
                
    return results
```

### 模式 3: 配置验证

```python
from pathlib import Path
from typing import Dict, Any
import yaml

def validate_config(config_path: Path) -> Dict[str, Any]:
    """验证配置文件.
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        解析后的配置字典
        
    Raises:
        ValueError: 配置无效
        FileNotFoundError: 文件不存在
    """
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # 必需字段检查
    required = ["project", "paths", "resources"]
    for field in required:
        if field not in config:
            raise ValueError(f"缺少必需字段: {field}")
    
    # 路径验证
    for key, path_str in config["paths"].items():
        path = Path(path_str)
        if key.endswith("_dir") and not path.exists():
            raise ValueError(f"路径不存在: {key}={path}")
    
    return config
```

### 模式 4: 错误恢复

```python
import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
T = TypeVar("T")
logger = logging.getLogger(__name__)

def retry_on_error(
    max_retries: int = 3,
    exceptions: tuple = (Exception,),
):
    """错误重试装饰器.
    
    Args:
        max_retries: 最大重试次数
        exceptions: 可重试的异常类型
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                    )
            raise RuntimeError("不应到达此处")
        return wrapper
    return decorator
```

---

## 性能优化指南

### 内存优化

| 场景 | 优化策略 | 示例 |
|------|----------|------|
| 大 FASTQ 文件 | 流式读取 | `for line in gzip.open(...)` |
| 特征表 | 稀疏矩阵 | `scipy.sparse.csr_matrix` |
| 多样本处理 | 分批加载 | 每批 N 个样本 |

### 并行策略

```yaml
# 推荐并行配置
resources:
  # Kraken2: I/O 密集，可高并行
  kraken2_threads: 16
  
  # HUMAnN: 内存密集，适度并行
  humann_threads: 8
  
  # QIIME2: CPU 密集，全核心
  qiime2_threads: 32
```

### I/O 优化

```python
# 使用 SSD 存储临时文件
import tempfile
tempfile.tempdir = "/ssd/tmp"

# 压缩中间文件
import gzip
with gzip.open(output_path, "wb") as f:
    f.write(data)
```

---

## 测试策略

### 单元测试

```python
import pytest
from pathlib import Path
from micos.quality_control import process_fastq

@pytest.fixture
def sample_fastq(tmp_path: Path) -> Path:
    """创建测试 FASTQ 文件."""
    fastq = tmp_path / "test.fastq"
    fastq.write_text("@read1\nACGT\n+\nIIII\n")
    return fastq

def test_process_fastq(sample_fastq: Path, tmp_path: Path):
    """测试 FASTQ 处理."""
    result = process_fastq(
        input_path=sample_fastq,
        output_dir=tmp_path / "output",
    )
    assert result.exists()
```

### 集成测试

```python
@pytest.mark.integration
def test_full_pipeline(test_data_dir: Path, tmp_path: Path):
    """测试完整流程."""
    from micos.cli import main
    
    result = runner.invoke(main, [
        "full-run",
        "--input-dir", str(test_data_dir),
        "--results-dir", str(tmp_path),
        "--threads", "4",
    ])
    assert result.exit_code == 0
```

---

## 相关资源

- [Copilot 指令](.github/copilot-instructions.md)
- [贡献指南](CONTRIBUTING.md)
- [变更日志](CHANGELOG.md)
