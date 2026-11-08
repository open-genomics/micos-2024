# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- `scripts/download_databases.sh` 支持 `MICOS_DB_CHECKSUMS`：sha256sum 格式的清单，
  按上游归档文件名（URL basename，百分号解码）或本地保存名查表；优先级为
  `MICOS_KRAKEN2_<TYPE>_SHA256` > 清单 > 跳过（明确告警）。显式给了清单却查不到
  条目、或清单不可读时脚本直接失败，不再静默跳过校验；文件名含空格的归档
  （上游 PlusPF）也能匹配。脚本改为仅在直接执行时运行 `main`，便于测试；
  新增 `tests/test_download_databases_script.py`（6 项）
- 修正 README 的 `full-run` / `dry-run` 示例：标注数据库路径占位符，并为 `dry-run` 补齐必需的 `--kneaddata-db` / `--kraken2-db` 参数
- 修复 Kraken2 汇总把未分类 reads 扣两次：report 的 R 行本身就是已分类 reads，
  `total = classified + unclassified`，不再从 root 中再减一次；分类率恢复正常
- Krona 图表改用 Kraken2 逐条输出 `.kraken`（`-q 2 -t 3`），此前误把 report
  第 3 列的 reads 计数当作 taxid；缺少 `.kraken` 时回退到 report 的 `-t 5 -m 2`
- `micos doctor` 未显式传数据库参数时读取配置文件中的路径
- `scripts/run_module.sh` 在配置文件缺失时不再因 `set -e` 提前退出，改由模块给出
  可操作的数据库参数提示；新增回归测试
- Krona Docker 镜像不再关闭 conda 的 TLS 校验，依赖安装恢复证书验证
- 修复 `run_manifest.json` 的 `git_commit` 取自调用者当前目录仓库：`_git_commit()` 现在固定 `cwd` 为包根（`Path(__file__).parents[1]`）；wheel 安装没有 `.git` 时仍返回 `None`，不会误记用户项目版本
- 明确 `--skip-qc` / `--skip-taxonomy` 的语义：`--skip-qc` 时物种分类与功能注释直接读取 `--input-dir`（视为已清洗数据，需 `*_paired_1.fastq` 命名）；`--skip-taxonomy` 且未跳过多样性时，CLI 提前校验 `results/taxonomic_profiling/feature-table.biom`，缺失返回用法错误（退出码 2），`full_run` 的 `MissingInputError` 文本补充前置条件。CLI 帮助与 `docs/zh/reference/cli.md` 同步
- 新增 3 条回归测试：git cwd、skip-qc 下游输入、skip-taxonomy 缺 BIOM 的 CLI/编排错误
- 修复物种分类混入历史报告：`kraken-biom`/Krona 仅使用本次运行实际生成的 `.report`，不再通配输出目录中的旧文件，避免复用 results 目录时样本数虚增
- 修复 HUMAnN 失败时 `temp_humann_input/` 临时合并 FASTQ 残留：样本处理循环改为 `try/finally` 清理（`ignore_errors=True`，不掩盖原始错误）
- 新增 2 条回归测试：历史 `.report` 不参与聚合、HUMAnN 失败后临时目录被清理
- Kraken2 样本并行：样本数大于 1 时用线程池并行执行，并行度与单样本
  `--threads` 共享总线程预算（`workers = min(样本数, threads)`，
  `per_sample_threads = threads // workers`），不再让 N 个进程各开 `threads`
  线程造成 CPU 超订；`kraken-biom` 输入仍按样本发现顺序排列
- `scripts/network_analysis.py` 的相关矩阵改为一次性向量化计算：Spearman
  用 `spearmanr(矩阵)`（每个变量只排秩一次），Pearson 用 `np.corrcoef` +
  t 分布向量化 p 值，替换逐对调用与重复 rank 的 O(n²) 循环
- `scripts/download_databases.sh` 支持 `MICOS_KRAKEN2_*_SHA256` 校验下载包；
  未提供哈希时显式告警，不再静默解压未经校验的 tar.gz

## [1.2.0] - 2026-11-06

- 新增 `results/run_manifest.json`：记录 MICOS/Python/平台/git commit、外部工具版本、数据库路径、输入文件、参数和阶段状态/耗时
- 新增 `micos doctor`（支持 `--json`）：检查外部工具、数据库路径与 Python 环境
- 输入缺失改为 fail-closed：`NoSamplesError`、`MissingInputError`、`StageOutputError` 不再被当成成功；CLI 映射稳定退出码
- HTML 汇总报告升级：概览卡片、Top taxa、Alpha 多样性表、运行清单和产物索引
- QIIME2 多样性阶段新增 Alpha TSV 与 Beta 距离矩阵 TSV 导出
- 样本元数据兼容 QIIME 风格 `#SampleID` 表头；仓库自带示例 metadata 可直接加载
- 修复文档 URL、Conda 快速开始缺少 `pip install -e .`、Discussions 死链等 onboarding 问题
- README 重构为产品首页；赛事背景移入 `docs/zh/research/competition.md`
- 新增 `CITATION.cff`、`SECURITY.md`；CI 增加 Python 3.12，覆盖率门槛提升到 80%
- 版本号改为 `pyproject.toml` 静态维护（1.2.0），`micos --version` 不再显示 git dev 版本
- 配置强制校验（`enforce-effective-configuration`）：生产配置 model 统一 `extra="forbid"`，未知字段立即失败；移除 `max_memory`/`memory_gb` 等未接入 CLI 的愿景字段（迁至 `docs/zh/roadmap.md`）；明确配置优先级（CLI > analysis.yaml > databases.yaml > 默认）并支持 resolved value 来源输出；相对路径按所在配置文件目录解析；`validate-config` 对语法/未知字段/必需 stage 依赖返回非零；`full-run --dry-run` 输出 resolved plan（含 stage、输入、输出、threads、数据库、参数来源）且不执行外部工具
- 清理历史身份与组织引用（LessUp → holtwood / open-genomics）
- 修复文档站英文 404 自动重定向，CI 增加文档构建检查
- 归档遗留 `workflows/wdl_scripts/`，统一以 `steps/` 为权威 WDL 源
- 修复 WDL 语法错误（Directory/None 关键字）、统一 `${}` 为 `~{}`、固定生信工具版本
- 修复 Dockerfile 构建错误与 EOL 基础镜像（Python 3.6、R latest）
- 补齐 4 个流水线模块单元测试与 skip 选项测试，删除 `load_config` 死代码
- 修复 scripts 过时路径与 bash `set -e` 陷阱，清理临时工作文档

## [1.1.0] - 2025-04-16

- Complete Chinese documentation
- New installation, configuration, and troubleshooting guides
- API reference for CLI commands

## [1.0.0] - 2024-10-24

- First stable release for Mammoth Cup 2024
- Quality control (FastQC, KneadData)
- Taxonomic profiling (Kraken2, Krona)
- Diversity analysis (QIIME2)
- Functional annotation (HUMAnN)
- Docker containerization and WDL workflow support

## [0.9.0] - 2024-10-20

- Open source preparation and code cleanup
- Repository restructure
- CI/CD setup
