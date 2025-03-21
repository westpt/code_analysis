# C代码业务逻辑分析工具 - 项目结构设计

## 目录结构

```
/
├── src/                    # 源代码目录
│   ├── analyzer/          # 分析器核心代码
│   │   ├── __init__.py
│   │   ├── c_code_analyzer.py
│   │   ├── business_logic_extractor.py
│   │   └── utils.py
│   ├── visualization/     # 可视化相关代码
│   │   ├── __init__.py
│   │   ├── cfg_visualizer.py
│   │   ├── dfg_visualizer.py
│   │   └── module_visualizer.py
│   └── cli/               # 命令行接口
│       ├── __init__.py
│       └── commands.py
├── tests/                 # 测试目录
│   ├── unit/              # 单元测试
│   │   ├── test_c_code_analyzer.py
│   │   ├── test_business_logic_extractor.py
│   │   └── test_visualizers.py
│   ├── integration/       # 集成测试
│   │   └── test_end_to_end.py
│   └── fixtures/          # 测试用例和数据
│       ├── simple_c_code.c
│       ├── complex_c_code.c
│       └── expected_outputs/
├── examples/              # 示例代码
│   ├── simple_analysis.py
│   ├── module_extraction.py
│   ├── visualization_demo.py
│   └── sample_c_files/    # 示例C代码文件
│       ├── hello_world.c
│       ├── linked_list.c
│       └── binary_tree.c
├── docs/                  # 文档
│   ├── api/               # API文档
│   ├── user_guide/        # 用户指南
│   ├── developer_guide/   # 开发者指南
│   └── examples/          # 使用示例文档
├── scripts/               # 实用脚本
│   ├── setup_dev_env.py   # 开发环境设置脚本
│   └── generate_docs.py   # 文档生成脚本
├── .github/               # GitHub相关配置
│   └── workflows/         # GitHub Actions工作流
│       ├── tests.yml
│       └── publish.yml
├── analyze_c_code.py      # 主入口脚本
├── setup.py               # 安装配置
├── requirements.txt       # 依赖列表
├── requirements-dev.txt   # 开发依赖列表
├── README.md              # 项目说明
├── LICENSE                # 许可证文件
└── .gitignore             # Git忽略文件
```

## 文件说明

### 源代码目录 (src/)

#### analyzer/
- **c_code_analyzer.py**: C代码分析器，负责解析C代码并构建控制流图和数据流图
- **business_logic_extractor.py**: 业务逻辑提取器，负责从分析结果中提取业务模块
- **utils.py**: 通用工具函数

#### visualization/
- **cfg_visualizer.py**: 控制流图可视化
- **dfg_visualizer.py**: 数据流图可视化
- **module_visualizer.py**: 业务模块可视化

#### cli/
- **commands.py**: 命令行接口实现

### 测试目录 (tests/)

#### unit/
单元测试文件，测试各个组件的功能

#### integration/
集成测试，测试整个分析流程

#### fixtures/
测试用的C代码文件和预期输出结果

### 示例目录 (examples/)
提供各种使用示例，帮助用户快速上手

### 文档目录 (docs/)
详细的API文档、用户指南和开发者指南

## 重构计划

1. **重构现有代码**:
   - 将现有的`c_code_analyzer.py`和`business_logic_extractor.py`移动到`src/analyzer/`目录
   - 将可视化相关代码分离到`src/visualization/`目录
   - 将命令行接口代码移动到`src/cli/`目录

2. **添加测试**:
   - 为核心功能编写单元测试
   - 创建集成测试验证整个分析流程
   - 准备测试用的C代码文件

3. **完善文档**:
   - 编写详细的API文档
   - 创建用户指南和开发者指南
   - 提供丰富的使用示例

4. **添加CI/CD配置**:
   - 设置GitHub Actions进行自动测试
   - 配置自动发布流程

## 开发规范

1. **代码风格**:
   - 遵循PEP 8规范
   - 使用类型注解
   - 编写详细的文档字符串

2. **版本控制**:
   - 使用语义化版本控制
   - 每个功能在单独的分支上开发
   - 提交前运行测试

3. **测试覆盖率**:
   - 核心功能的测试覆盖率应达到80%以上
   - 每个新功能都应有对应的测试

## 下一步计划

1. 创建基本目录结构
2. 重构现有代码到新的目录结构
3. 编写基本的单元测试
4. 完善文档
5. 添加更多示例