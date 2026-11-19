# Change Proposal: declare-python-production-orchestrator

## Metadata

- Status: `Archived`
- Repository: `holtwood-genomics/micos-2024`
- Audit base: `c2c399f89c9cadf590c3a6dd13f31d51794018a5`
- Capability: `workflow-orchestration`
- Task IDs: `MICOS-DOC-001`, `ORG-GOV-001`
- Decision IDs: `MICOS-ORCH-001`

## Why

仓库当前由 `micos full-run` 的 Python 实现执行生产链路，现有 WDL 是分散步骤且没有顶层 workflow 或执行 CI，resume 也未实现。公开文档把项目描述成 WDL 全流程并支持恢复，会让用户基于不存在的能力运行科研分析。

## Changes

**Production orchestration contract**

- From: Python、shell、WDL 和 resume 的支持层级表述相互冲突。
- To: Python CLI 是唯一生产编排器；shell 只是薄包装；WDL 是实验性单步骤参考；当前明确不支持 resume。
- Reason: 公开能力与实际执行入口一致。
- Impact: 文档/规格契约修正，不删除 WDL，不改变当前 Python 执行结果。

## Scope

- README、docs、CLI help、shell/WDL 目录说明和相关 contributor guidance；
- 仓库内 workflow-orchestration spec；
- 文档一致性测试或确定性搜索检查。

## Out of scope

- 不实现 resume、run manifest 或 stage cache；
- 不修改科学参数、配置模型或 Python stage 行为；
- 不创建顶层 WDL，不删除现有 WDL；
- 不修复容器/环境版本和个人绝对路径（独立 change）。

## Compatibility and rollback

不改变生产代码输出。若文档发现某个 WDL 已具备未经审计的完整入口，必须先以执行证据更新 proposal，而不是继续保留“双生产入口”措辞。

## Approval

- `MICOS-ORCH-001`: Accepted on 2026-08-13
- Apply approval: `authorized by organization owner`
