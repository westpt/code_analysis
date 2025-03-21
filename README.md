# C代码业务逻辑分析工具

这是一个强大的C代码分析工具，能够自动提取和分析C代码中的业务逻辑结构。该工具通过构建控制流图（CFG）和数据流图（DFG），结合社区检测算法，识别代码中的业务模块，并分析模块间的依赖关系。

## 主要功能

- **代码结构分析**
  - 构建控制流图（CFG）
  - 构建数据流图（DFG）
  - 变量使用追踪（全局变量、静态变量、堆变量）
  - 函数调用关系分析

- **业务逻辑提取**
  - 基于社区检测的模块识别
  - 模块间依赖关系分析
  - 模块复杂度评估
  - 自动生成模块文档

- **可视化功能**
  - 控制流图可视化
  - 数据流图可视化
  - 业务模块依赖关系图
  - 支持导出为DOT格式

## 安装说明

### 安装LLVM/Clang

本工具依赖于LLVM/Clang进行C代码解析，请先安装LLVM/Clang：

#### Windows系统

1. 访问LLVM官方下载页面：https://releases.llvm.org/download.html 或 https://github.com/llvm/llvm-project/releases
2. 下载适合您Windows版本的预编译安装包（如LLVM-xx.x.x-win64.exe）
3. 运行安装程序，建议选择"添加LLVM到系统PATH"
4. 安装完成后，重启计算机以确保环境变量生效

#### Linux系统

1. 使用包管理器安装：
   ```bash
   # Ubuntu/Debian
   sudo apt-get install llvm clang
   
   # CentOS/RHEL
   sudo yum install llvm clang
   ```

2. 或从源码编译（如需特定版本）：
   ```bash
   git clone https://github.com/llvm/llvm-project.git
   cd llvm-project
   mkdir build && cd build
   cmake -DLLVM_ENABLE_PROJECTS=clang -DCMAKE_BUILD_TYPE=Release -G "Unix Makefiles" ../llvm
   make
   sudo make install
   ```

#### 验证安装

打开命令行/终端，输入以下命令验证安装是否成功：
```bash
clang --version
```

如果显示版本信息，则表示安装成功。

主要依赖：
- networkx：图分析库
- matplotlib：可视化支持
- clang：C代码解析
- python-louvain：（可选）用于社区检测
- pydot：（可选）用于导出DOT格式图

## 使用示例

```python
# 分析C代码文件
from c_code_analyzer import CCodeAnalyzer
from business_logic_extractor import BusinessLogicExtractor

# 初始化分析器
analyzer = CCodeAnalyzer('your_code.c')
analyzer.analyze()

# 提取业务逻辑
extractor = BusinessLogicExtractor(analyzer)

# 提取业务模块
modules, dependencies = extractor.extract_modules()

# 分析模块复杂度
complexity = extractor.analyze_module_complexity()

# 生成模块文档
documentation = extractor.generate_module_documentation()

# 可视化模块依赖
extractor.visualize_modules('modules.png')
```

## 核心类说明

### CCodeAnalyzer
负责C代码的底层分析，包括：
- 解析C代码语法树
- 构建控制流图和数据流图
- 识别变量和函数调用
- 追踪变量使用情况

### BusinessLogicExtractor
负责高层业务逻辑分析，包括：
- 识别业务模块
- 分析模块间依赖
- 评估模块复杂度
- 生成模块文档
- 可视化分析结果

## 输出说明

1. **模块识别**：
   - 基于函数调用关系自动识别业务模块
   - 每个模块包含相关的函数和变量

2. **复杂度指标**：
   - 节点数量（函数数量）
   - 内部边数（模块内调用）
   - 外部边数（跨模块调用）
   - 全局变量使用数
   - 堆变量使用数

3. **可视化输出**：
   - business_modules.png：模块依赖关系图
   - control_flow_graph.png：控制流图
   - data_flow_graph.png：数据流图
   - module_graph.dot：DOT格式的模块图

## 注意事项

- 确保系统已安装clang库
- 对于大型代码库，建议安装python-louvain以获得更好的模块划分效果
- 可视化大型图形可能需要较大内存