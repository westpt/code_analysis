#!/bin/bash
# 编译timer项目的Shell脚本

# 使用Clang编译器
echo "使用Clang编译timer项目..."
clang -Wall -Wextra -I include src/timer.c src/timer_internal.c test_timer.c -o timer_test

# 如果编译成功
if [ $? -eq 0 ]; then
    echo "编译成功！可以运行 ./timer_test"
else
    echo "编译失败，请检查错误信息。"
fi