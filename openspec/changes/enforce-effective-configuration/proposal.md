# Change Proposal: enforce-effective-configuration

## Metadata

- Status: `Proposed`
- Repository: `holtwood-genomics/micos-2024`
- Base commit: `f7f58969fe1e736e591249063650de26b95c490d`
- Capability: `configuration`
- Task IDs: `MICOS-CONFIG-001`
- Decision IDs: none
- Proposed at: `2026-08-19`

## Why

配置要么被明确使用，要么在运行前失败；当前配置模型允许未知字段
（`ConfigDict(extra="allow")`），模板中可能包含未接入 CLI 的愿景参数，且存在
`max_memory`/`memory_gb` 这类名称漂移。用户拼错字段或给出无效 YAML 时可能被
静默忽略或回退到默认值，外部工具在错误配置下启动，浪费计算资源且结果不可复现。

## Evidence

| Fact | Repository evidence | Verification |
|---|---|---|
| 配置模型允许未知字段 | `micos/config.py` 多个 model `ConfigDict(extra="allow")` | `grep -n 'extra=' micos/config.py` |
| 存在 `memory_gb` 字段 | `micos/config.py` `ResourcesConfig.memory_gb` | `grep -n 'memory_gb' micos/config.py` |
| 模板字段与 CLI 接入关系未强制 | `config/analysis.yaml.template` | `grep -n ... config/analysis.yaml.template` |

## Changes

**Strict, traceable, effective configuration**

- From: 未知字段被允许、模板可能含未接入字段、配置错误可能 warning 后使用默认值。
- To: 生产配置 model 对未知字段 `extra="forbid"`；模板只保留已接入 CLI 的字段；
  名称漂移字段（`max_memory`/`memory_gb`）在资源限制实现前不出现于活动配置；
  YAML/Pydantic 失败以配置错误退出；明确的配置优先级并可输出 resolved value 来源；
  相对路径相对所在配置文件解析；`validate-config` 对语法/未知字段/必需 stage 依赖
  返回非零；`--dry-run` 输出 resolved plan（stage、输入、输出、threads、数据库、
  参数来源）且不执行外部工具；不用宽泛 `except Exception` 吞掉配置失败。
- Reason: 让任何被模板展示的字段都能在 dry-run 的 resolved plan 中观察到，拼错字段
  在外部工具启动前失败，保证可复现性。
- Impact: 行为收紧（未知字段/错误配置从允许或警告变为失败），仅影响配置路径；
  不改变科学参数语义或已生效字段。

## Scope

- `micos/config.py`、`micos/cli.py` 的配置解析与校验路径；
- `config/*.template`、配置文档；
- 配置与 CLI 测试（含 `--dry-run`、`validate-config`）。

## Out of scope

- 不一次性把所有愿景参数接入生信工具；
- 不实现 `record-run-manifest`（独立 change）；
- 不修改 stage 科学参数、数据库内容或容器/环境版本；
- 不实现资源限制本身（仅移除未实现的 `memory_gb` 漂移字段）。

## Compatibility and rollback

配置格式收紧为 fail-closed：此前可被静默忽略的未知字段现在会失败。合法的既有配置
（字段均接入且类型正确）不受影响。回滚可还原 `extra="allow"` 与模板，但会退回
静默忽略行为。

## Dependencies and blockers

- 前置：`declare-python-production-orchestrator`（已归档）确认 Python CLI 为唯一
  生产编排器，本 change 在其配置语义上收紧。

## Rollback

还原 `micos/config.py`、`micos/cli.py`、模板与测试；无已生成数据需要兼容。

## Approval

- Approved change scope: `pending`
- Approved breaking values: 未知字段/错误配置从允许或警告改为失败
- Approved by: organization owner
