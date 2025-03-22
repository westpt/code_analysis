#!/bin/bash

# 简化版C代码分析Shell脚本
# 用于清理output目录并执行C代码分析

# 输出目录
OUTPUT_DIR="output"

# 清理输出目录
echo "清理输出目录: $OUTPUT_DIR"
if [ -d "$OUTPUT_DIR" ]; then
    # 保留.gitkeep文件，删除其他所有文件
    find "$OUTPUT_DIR" -type f -not -name ".gitkeep" -exec rm -f {} \;
else
    echo "创建输出目录: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

# 执行分析命令
CMD="python -m src.cli.analyze_c_code examples/sample_c_files/timer/analysis_config.json --output-dir $OUTPUT_DIR --json"

echo "执行分析命令: $CMD"
eval $CMD

# 检查命令执行状态
if [ $? -ne 0 ]; then
    echo "错误: 分析过程中出现错误" >&2
    exit 1
fi

echo "分析完成。结果已保存到 $OUTPUT_DIR/"
exit 0