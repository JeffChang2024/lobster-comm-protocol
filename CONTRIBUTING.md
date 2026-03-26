# 贡献指南 | Contributing Guide

感谢你对龙虾通信协议（LCP）的关注！我们欢迎所有形式的贡献。

## 贡献方式

### 🐛 报告问题
- 使用 [Issue 模板](../../issues/new/choose) 报告 bug 或提出建议
- 清楚描述问题的复现步骤
- 如果是规范问题，请引用具体的章节号

### 📖 改进文档
- 修正错别字、语法错误
- 改善表述清晰度
- 添加更多示例

### 🔧 贡献代码
1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add: your feature description'`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

### 🌐 翻译
- 我们欢迎将规范翻译成其他语言
- 翻译文件放在 `spec/` 目录下，命名为 `LCP-1.0-spec-{lang}.md`

## 规范修改流程

对 LCP 规范的实质性修改（非错别字/格式）需要经过以下流程：

1. **提出 RFC**：在 Issues 中创建一个带 `rfc` 标签的议题
2. **社区讨论**：至少 7 天的公开讨论期
3. **草案 PR**：将修改作为 Draft PR 提交
4. **审阅**：至少 2 位维护者审阅通过
5. **合并**：更新版本号和变更日志

## 代码规范

### Python 参考实现
- Python 3.8+
- 仅使用标准库（零外部依赖）
- 类型注解
- Docstring（Google 风格）
- 通过所有测试：`python -m pytest reference-impl/tests/`

### 提交信息格式

```
<type>: <description>

[optional body]
```

类型：
- `spec`: 规范文档修改
- `impl`: 参考实现修改
- `schema`: JSON Schema 修改
- `docs`: 文档修改
- `test`: 测试修改
- `ci`: CI/CD 修改

## 行为准则

- 保持尊重和包容
- 以技术事实为基础进行讨论
- 龙虾精神：坚硬的外壳（严格的标准），温和的内心（友好的社区）🦞

## 许可

- 规范文档贡献遵循 CC BY 4.0
- 代码贡献遵循 MIT 许可证
