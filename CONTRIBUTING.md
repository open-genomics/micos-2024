# 贡献指南

感谢您对MICOS-2024项目的关注！我们欢迎所有形式的贡献，包括代码、文档、测试、问题报告和功能建议。

## 贡献方式

### 报告问题

如果您发现了bug或有改进建议：

1. 搜索[现有Issues](https://github.com/open-genomics/micos-2024/issues)，确保问题尚未被报告
2. 使用相应的Issue模板：
   - [Bug报告](.github/ISSUE_TEMPLATE/bug_report.md)
   - [功能请求](.github/ISSUE_TEMPLATE/feature_request.md)
3. 提供详细信息：环境信息、重现步骤、期望行为等

### 代码贡献

#### 开发环境设置

```bash
# 1. Fork并克隆项目
git clone https://github.com/open-genomics/micos-2024.git
cd micos-2024

# 2A. 使用 Conda/Mamba（推荐用于生物信息学依赖）
mamba env create -f environment.yml
conda activate micos-2024

# 2B. 使用 Pip（仅进行 Python 开发/贡献时）
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pre-commit install

# 3. 创建开发分支
git checkout -b feature/your-feature-name
```

#### 开发流程

1. 进行开发并提交更改
2. 确保代码通过测试：`pytest -q` 或 `./scripts/verify_installation.sh`
3. 推送到您的fork并创建Pull Request

### 文档贡献

- 修正错别字和语法错误
- 改进文档清晰度
- 添加教程或示例
- 更新API文档

## Pull Request指南

### 提交前检查

- [ ] 代码通过所有测试
- [ ] 代码符合项目规范
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 提交信息清晰明确

### 提交信息格式

```
类型: 简短描述 (不超过50字符)

详细描述（如果需要）
- 解释更改原因
- 描述更改影响
- 引用相关Issue

Fixes #123
```

提交类型 (Conventional Commits)：`feat`、`fix`、`docs`、`style`、`refactor`、`test`、`chore`

## 代码规范

- **Python代码**：遵循PEP 8规范
- **Shell脚本**：使用shellcheck检查
- **文档**：使用Markdown格式
- **测试**：为新功能添加测试

## 获取帮助

- **GitHub Issues**：问题报告和功能讨论
- **GitHub Issues**：一般讨论和问答（Discussions 尚未开启）
- **文档**：查看[故障排除指南](docs/zh/troubleshooting.md)

## 许可证

通过贡献代码，您同意您的贡献将在[MIT许可证](LICENSE)下发布。

感谢您的贡献！🎉