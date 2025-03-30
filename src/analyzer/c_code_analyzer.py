import os
import sys
import json
import glob
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

# 配置libclang路径
import clang.cindex
try:
    # 尝试查找常见的LLVM安装路径
    possible_paths = [
        'C:/Program Files/LLVM/bin',
        'C:/LLVM/bin',
        'D:/Program Files/LLVM/bin',
        'D:/LLVM/bin'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            clang.cindex.Config.set_library_path(path)
            break
except Exception as e:
    print(f"Warning: Failed to set libclang path: {e}")
    print("Please install LLVM/Clang and ensure it's in your PATH")

class CCodeAnalyzer:
    def __init__(self, path, include_paths=None):
        """初始化C代码分析器
        Args:
            path: 可以是单个C文件的路径，也可以是包含C文件的目录路径
            include_paths: 包含头文件的路径列表
        """
        self.files = []
        if os.path.isdir(path):
            self.files.extend(glob.glob(os.path.join(path, '**/*.c'), recursive=True))
            self.files.extend(glob.glob(os.path.join(path, '**/*.h'), recursive=True))
        else:
            self.files.append(path)
        
        self.include_paths = include_paths or []
        self.index = clang.cindex.Index.create()
        self.cfg = nx.DiGraph()  # 控制流图
        self.dfg = nx.DiGraph()  # 数据流图
        self.variables = {}  # 变量信息
        self.global_vars = set()  # 全局变量
        self.static_vars = set()  # 静态变量
        self.heap_vars = set()  # 堆变量
        self.function_calls = []  # 函数调用
        self.business_logic = nx.DiGraph()  # 业务逻辑图
    
    def analyze(self):
        """执行完整的代码分析"""
        # 创建temp目录（如果不存在）
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 创建解析日志文件
        parse_log_file = os.path.join(temp_dir, 'parse_debug.log')
        with open(parse_log_file, 'w', encoding='utf-8') as log_f:
            log_f.write(f"开始解析，文件列表: {self.files}\n")
            log_f.write(f"包含路径: {self.include_paths}\n\n")
            # 记录libclang配置信息
            log_f.write(f"libclang库路径: {clang.cindex.conf.get_filename() if hasattr(clang.cindex, 'conf') else '未知'}\n")
            log_f.write(f"libclang版本: {clang.cindex.Config.library_version if hasattr(clang.cindex.Config, 'library_version') else '未知'}\n")
            # 记录Python和系统信息
            log_f.write(f"Python版本: {sys.version}\n")
            log_f.write(f"操作系统: {sys.platform}\n\n")
            # 记录clang模块信息
            log_f.write(f"clang模块路径: {clang.__file__}\n")
            log_f.write(f"clang.cindex模块路径: {clang.cindex.__file__}\n\n")
        
        # 初始化functions属性，避免AttributeError
        self.functions = {}
        
        for file_path in self.files:
            # 准备编译参数，包括包含路径
            args = []
            
            # 添加源文件所在目录作为include路径
            file_dir = os.path.dirname(file_path)
            if file_dir:
                args.append(f'-I{file_dir}')
                
                # 添加源文件所在目录的父目录作为include路径（处理相对路径的include）
                parent_dir = os.path.dirname(file_dir)
                if parent_dir:
                    args.append(f'-I{parent_dir}')
            
            # 添加用户指定的include路径
            for include_path in self.include_paths:
                args.append(f'-I{include_path}')
            
            # 记录当前文件的解析参数 - 使用独立的with块
            with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                log_f.write(f"\n解析文件: {file_path}\n")
                log_f.write(f"编译参数: {args}\n")
                log_f.write(f"文件是否存在: {os.path.exists(file_path)}\n")
                log_f.write(f"文件大小: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}\n")
                
                # 检查文件内容的前几行
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            first_lines = [next(f) for _ in range(5) if f]
                            log_f.write(f"文件前5行:\n{''.join(first_lines)}\n")
                            
                            # 检查include语句
                            f.seek(0)
                            include_lines = [line for line in f if '#include' in line]
                            if include_lines:
                                log_f.write(f"Include语句:\n{''.join(include_lines)}\n")
                                
                                # 检查每个include文件是否存在
                                for inc_line in include_lines:
                                    inc_path = inc_line.split('#include')[1].strip()
                                    if '"' in inc_path:
                                        # 相对路径include
                                        inc_file = inc_path.strip('"').strip('<>').strip()
                                        # 检查相对于当前文件目录的路径
                                        rel_path = os.path.join(file_dir, inc_file)
                                        log_f.write(f"  检查include文件: {inc_file}\n")
                                        log_f.write(f"  相对路径: {rel_path}, 存在: {os.path.exists(rel_path)}\n")
                                        # 检查相对于父目录的路径
                                        if parent_dir:
                                            parent_path = os.path.join(parent_dir, inc_file)
                                            log_f.write(f"  父目录路径: {parent_path}, 存在: {os.path.exists(parent_path)}\n")
                    except Exception as e:
                        log_f.write(f"读取文件内容失败: {e}\n")
            
            # 解析翻译单元 - 使用独立的try-except块和独立的with块
            try:
                # 添加更多编译选项以提高兼容性
                args.extend(['-std=c99', '-D__STDC_LIMIT_MACROS', '-D__STDC_CONSTANT_MACROS'])
                
                # 添加标准C库头文件路径
                # 尝试添加常见的stdint.h和stdlib.h所在路径
                if sys.platform.startswith('win'):
                    # Windows平台常见的LLVM/Clang包含路径
                    possible_include_paths = [
                        'C:/Program Files/LLVM/lib/clang/*/include',
                        'C:/LLVM/lib/clang/*/include',
                        'D:/Program Files/LLVM/lib/clang/*/include',
                        'D:/LLVM/lib/clang/*/include',
                        # 添加MinGW路径
                        'C:/MinGW/include',
                        'C:/Program Files/MinGW/include',
                        'C:/msys64/mingw64/include',
                        # 添加Visual Studio路径
                        'C:/Program Files/Microsoft Visual Studio/*/VC/Tools/MSVC/*/include',
                        'C:/Program Files (x86)/Microsoft Visual Studio/*/VC/Tools/MSVC/*/include',
                        'C:/Program Files (x86)/Windows Kits/*/Include/*/ucrt'
                    ]
                    
                    # 展开通配符并添加找到的路径
                    for pattern in possible_include_paths:
                        for path in glob.glob(pattern):
                            if os.path.exists(path):
                                args.append(f'-I{path}')
                                with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                                    log_f.write(f"添加标准库头文件路径: {path}\n")
                    
                    # 创建临时stdlib.h文件（如果需要）
                    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp')
                    temp_stdlib_path = os.path.join(temp_dir, 'stdlib.h')
                    if not os.path.exists(temp_stdlib_path):
                        try:
                            with open(temp_stdlib_path, 'w', encoding='utf-8') as f:
                                f.write("// 临时stdlib.h文件，用于解决标准库头文件缺失问题\n")
                                f.write("#ifndef _STDLIB_H\n")
                                f.write("#define _STDLIB_H\n\n")
                                f.write("#include <stddef.h>\n\n")
                                f.write("void* malloc(size_t size);\n")
                                f.write("void free(void* ptr);\n")
                                f.write("void* calloc(size_t num, size_t size);\n")
                                f.write("void* realloc(void* ptr, size_t size);\n")
                                f.write("int system(const char* command);\n")
                                f.write("void exit(int status);\n\n")
                                f.write("#endif /* _STDLIB_H */\n")
                            args.append(f'-I{temp_dir}')
                            with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                                log_f.write(f"创建并添加临时stdlib.h文件: {temp_stdlib_path}\n")
                        except Exception as e:
                            with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                                log_f.write(f"创建临时stdlib.h文件失败: {e}\n")
                else:
                    # Linux/macOS平台常见的包含路径
                    possible_include_paths = [
                        '/usr/include',
                        '/usr/local/include',
                        '/usr/lib/clang/*/include'
                    ]
                    
                    for pattern in possible_include_paths:
                        for path in glob.glob(pattern):
                            if os.path.exists(path):
                                args.append(f'-I{path}')
                                with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                                    log_f.write(f"添加标准库头文件路径: {path}\n")
                
                # 记录最终编译参数
                with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                    log_f.write(f"最终编译参数: {args}\n")
                
                # 使用详细的解析选项
                options = clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
                
                # 尝试使用不同的解析选项
                try:
                    with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                        log_f.write("尝试使用标准解析选项...\n")
                    tu = self.index.parse(file_path, args, options=options)
                except Exception as e1:
                    with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                        log_f.write(f"标准解析失败: {e1}\n")
                        log_f.write("尝试使用更宽松的解析选项...\n")
                    try:
                        # 添加更宽松的解析选项
                        options |= clang.cindex.TranslationUnit.PARSE_INCOMPLETE
                        tu = self.index.parse(file_path, args, options=options)
                    except Exception as e2:
                        with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                            log_f.write(f"宽松解析也失败: {e2}\n")
                            # 记录详细的异常信息
                            import traceback
                            log_f.write("异常堆栈:\n")
                            log_f.write(traceback.format_exc())
                            log_f.write("\n")
                        raise e2
                
                if tu:
                    # 记录解析成功信息
                    with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                        log_f.write(f"成功解析文件: {file_path}\n")
                        log_f.write(f"诊断信息数量: {len(tu.diagnostics)}\n")
                        
                        # 记录所有诊断信息（增强版）
                        if tu.diagnostics:
                            log_f.write("诊断信息详情:\n")
                            for i, diag in enumerate(tu.diagnostics):
                                log_f.write(f"  [诊断 #{i+1}]\n")
                                log_f.write(f"  - 严重性: {diag.severity}\n")
                                log_f.write(f"  - 位置: {diag.location}\n")
                                log_f.write(f"  - 拼写: {diag.spelling}\n")
                                log_f.write(f"  - 类别: {diag.category_name}\n")
                                
                                # 添加更详细的位置信息
                                if diag.location.file:
                                    log_f.write(f"  - 文件: {diag.location.file.name}\n")
                                    log_f.write(f"  - 行号: {diag.location.line}\n")
                                    log_f.write(f"  - 列号: {diag.location.column}\n")
                                    
                                    # 尝试获取错误行的代码内容
                                    try:
                                        with open(diag.location.file.name, 'r', encoding='utf-8') as src_f:
                                            lines = src_f.readlines()
                                            if 0 <= diag.location.line-1 < len(lines):
                                                error_line = lines[diag.location.line-1].rstrip()
                                                log_f.write(f"  - 错误行内容: {error_line}\n")
                                                # 添加指示错误位置的标记
                                                marker = ' ' * (diag.location.column-1) + '^'
                                                log_f.write(f"  - 错误位置: {marker}\n")
                                    except Exception as e:
                                        log_f.write(f"  - 无法读取错误行内容: {e}\n")
                                
                                # 添加更多诊断信息
                                if hasattr(diag, 'option'):
                                    log_f.write(f"  - 选项: {diag.option}\n")
                                if hasattr(diag, 'disable_option'):
                                    log_f.write(f"  - 禁用选项: {diag.disable_option}\n")
                                if hasattr(diag, 'ranges') and diag.ranges:
                                    log_f.write(f"  - 范围数量: {len(diag.ranges)}\n")
                                    for j, range in enumerate(diag.ranges):
                                        log_f.write(f"    范围 #{j+1}: {range.start.line}:{range.start.column} - {range.end.line}:{range.end.column}\n")
                                if hasattr(diag, 'fixits') and diag.fixits:
                                    log_f.write(f"  - 修复建议数量: {len(diag.fixits)}\n")
                                    for j, fixit in enumerate(diag.fixits):
                                        log_f.write(f"    修复建议 #{j+1}: {fixit.value}\n")
                                
                                # 如果诊断信息中包含'timer'，添加更多上下文
                                if 'timer' in diag.spelling.lower():
                                    log_f.write(f"  [发现timer相关错误!]\n")
                                    log_f.write(f"  - 详细分析: 这可能与TimerSystem结构体或Timer结构体定义有关\n")
                                    # 检查include路径是否正确
                                    log_f.write(f"  - 当前include路径: {args}\n")
                                    
                                log_f.write("\n")
                        
                        # 记录翻译单元的基本信息（增强版）
                        log_f.write(f"翻译单元拼写: {tu.spelling}\n")
                        log_f.write(f"翻译单元游标类型: {tu.cursor.kind}\n")
                        log_f.write(f"翻译单元游标拼写: {tu.cursor.spelling}\n")
                        
                        # 添加更多翻译单元信息
                        log_f.write(f"翻译单元包含的文件数量: {len(list(tu.get_includes()))}\n")
                        log_f.write("包含的文件列表:\n")
                        for i, included in enumerate(tu.get_includes()):
                            log_f.write(f"  {i+1}. {included.include.name} (来自 {included.source.name}:{included.location.line})\n")
                        
                        # 检查是否存在未解析的符号
                        log_f.write("\n检查未解析的符号...\n")
                        def check_unresolved_symbols(cursor, log_file):
                            if cursor.kind == clang.cindex.CursorKind.UNEXPOSED_DECL:
                                log_file.write(f"发现未解析声明: {cursor.spelling} 在 {cursor.location.file}:{cursor.location.line}:{cursor.location.column}\n")
                            elif cursor.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
                                log_file.write(f"发现未解析表达式: {cursor.spelling} 在 {cursor.location.file}:{cursor.location.line}:{cursor.location.column}\n")
                            
                            # 检查引用但未定义的符号
                            if cursor.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                                referenced = cursor.referenced
                                if referenced and referenced.kind == clang.cindex.CursorKind.UNEXPOSED_DECL:
                                    log_file.write(f"引用未解析的符号: {cursor.spelling} 在 {cursor.location.file}:{cursor.location.line}:{cursor.location.column}\n")
                                    log_file.write(f"  引用指向: {referenced.spelling} 类型: {referenced.kind}\n")
                            
                            # 递归检查子节点
                            for child in cursor.get_children():
                                check_unresolved_symbols(child, log_file)
                        
                        # 对翻译单元的根游标执行检查
                        check_unresolved_symbols(tu.cursor, log_f)
                    
                    # 生成AST调试文件
                    ast_debug_file = os.path.join(temp_dir, f'{os.path.basename(file_path)}.ast.debug')
                    with open(ast_debug_file, 'w', encoding='utf-8') as f:
                        self._dump_ast(tu.cursor, f)
                    
                    print(f"{tu.cursor.spelling} AST generated at {ast_debug_file}")   
                    
                    self._parse_code_elements(tu.cursor)
                    self._build_cfg_dfg(tu.cursor)
                else:
                    error_msg = f"Warning: Failed to parse {file_path}"
                    print(error_msg)
                    with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                        log_f.write(f"{error_msg}\n")
            except Exception as e:
                error_msg = f"Error parsing {file_path}: {e}"
                print(error_msg)
                
                # 记录详细的异常信息 - 使用独立的with块
                with open(parse_log_file, 'a', encoding='utf-8') as log_f:
                    log_f.write(f"{error_msg}\n")
                    # 记录异常堆栈
                    import traceback
                    log_f.write("异常堆栈:\n")
                    log_f.write(traceback.format_exc())
                    log_f.write("\n")
                    
                    # 尝试获取更多关于错误的上下文信息
                    log_f.write("错误上下文信息:\n")
                    log_f.write(f"错误类型: {type(e).__name__}\n")
                    log_f.write(f"错误字符串表示: {str(e)}\n")
                    log_f.write(f"错误repr表示: {repr(e)}\n")
                    
                    # 特别处理'timer'相关错误
                    if 'timer' in str(e).lower():
                        log_f.write("\n[发现timer相关错误!]\n")
                        log_f.write("进行深入分析...\n")
                        
                        # 检查文件内容
                        log_f.write("检查文件内容:\n")
                        try:
                            with open(file_path, 'r', encoding='utf-8') as src_f:
                                content = src_f.read()
                                log_f.write(f"文件大小: {len(content)} 字节\n")
                                
                                # 检查关键结构体定义
                                if 'TimerSystem' in content:
                                    log_f.write("找到TimerSystem结构体引用\n")
                                    # 提取结构体定义上下文
                                    idx = content.find('TimerSystem')
                                    start = max(0, idx - 100)
                                    end = min(len(content), idx + 100)
                                    log_f.write(f"上下文: ...{content[start:end]}...\n")
                                else:
                                    log_f.write("未找到TimerSystem结构体引用\n")
                                
                                # 检查include语句
                                includes = [line for line in content.split('\n') if '#include' in line]
                                log_f.write(f"Include语句: {includes}\n")
                                
                                # 检查是否正确包含timer.h
                                timer_h_included = any('timer.h' in inc for inc in includes)
                                log_f.write(f"是否包含timer.h: {timer_h_included}\n")
                        except Exception as read_err:
                            log_f.write(f"读取文件失败: {read_err}\n")
                        
                        # 检查include路径
                        log_f.write("\n检查include路径:\n")
                        log_f.write(f"编译参数: {args}\n")
                        
                        # 检查timer.h文件是否存在于include路径中
                        for inc_path in args:
                            if inc_path.startswith('-I'):
                                path = inc_path[2:]
                                timer_h_path = os.path.join(path, 'timer.h')
                                log_f.write(f"检查路径: {timer_h_path}, 存在: {os.path.exists(timer_h_path)}\n")
                                
                                # 如果存在，检查文件内容
                                if os.path.exists(timer_h_path):
                                    try:
                                        with open(timer_h_path, 'r', encoding='utf-8') as h_f:
                                            h_content = h_f.read()
                                            log_f.write(f"timer.h大小: {len(h_content)} 字节\n")
                                            if 'TimerSystem' in h_content:
                                                log_f.write("timer.h中找到TimerSystem结构体定义\n")
                                            else:
                                                log_f.write("timer.h中未找到TimerSystem结构体定义\n")
                                    except Exception as h_err:
                                        log_f.write(f"读取timer.h失败: {h_err}\n")
                        
                        # 检查相对路径include
                        file_dir = os.path.dirname(file_path)
                        rel_timer_h = os.path.join(file_dir, '../include/timer.h')
                        log_f.write(f"检查相对路径: {rel_timer_h}, 存在: {os.path.exists(rel_timer_h)}\n")
                        
                        # 提供可能的解决方案
                        log_f.write("\n可能的解决方案:\n")
                        log_f.write("1. 确保timer.h文件在正确的include路径中\n")
                        log_f.write("2. 检查TimerSystem结构体是否在timer.h中正确定义\n")
                        log_f.write("3. 检查include语句是否使用了正确的相对路径\n")
                        log_f.write("4. 尝试使用绝对路径而不是相对路径\n")
                        log_f.write("5. 检查timer.h和timer.c中的结构体定义是否一致\n")
                continue
                
        self._track_heap_variables()
        self._build_business_logic()
        return self
    
    def _dump_ast(self, cursor, file, level=0):
        """将AST节点信息输出到文件,不进行相关分析"""
        # 输出当前节点信息
        indent = '  ' * level
        file.write(f"{indent}Node: {cursor.kind.name}\n")
        file.write(f"{indent}Spelling: {cursor.spelling}\n")
        
        # 添加更详细的位置信息
        location_info = "未知位置"
        if cursor.location.file:
            location_info = f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}"
        file.write(f"{indent}Location: {location_info}\n")
        
        # 添加类型信息和更多详细信息
        file.write(f"{indent}Type: {cursor.type.spelling}\n")
        file.write(f"{indent}Type Kind: {cursor.type.kind}\n")
        file.write(f"{indent}Canonical Type: {cursor.type.get_canonical().spelling}\n")
        
        # 如果是函数定义，输出更多详细信息
        if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            file.write(f"{indent}Is Definition: {cursor.is_definition()}\n")
            file.write(f"{indent}Return Type: {cursor.result_type.spelling}\n")
            file.write(f"{indent}Parameters:\n")
            for param in cursor.get_arguments():
                file.write(f"{indent}  - {param.spelling}: {param.type.spelling}\n")
            
            # 添加函数体信息
            has_body = False
            for child in cursor.get_children():
                if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                    has_body = True
                    break
            file.write(f"{indent}Has Body: {has_body}\n")
        
        # 如果是包含指令，输出更多详细信息
        elif cursor.kind == clang.cindex.CursorKind.INCLUSION_DIRECTIVE:
            try:
                included_file = cursor.get_included_file()
                if included_file:
                    file.write(f"{indent}Included File: {included_file}\n")
                else:
                    file.write(f"{indent}Included File: 未找到 (可能是标准库或路径问题)\n")
            except Exception as e:
                file.write(f"{indent}Included File: 获取失败 ({str(e)})\n")
            file.write(f"{indent}Include Path: {cursor.displayname}\n")
        
        # 如果是变量声明，输出更多详细信息
        elif cursor.kind == clang.cindex.CursorKind.VAR_DECL:
            file.write(f"{indent}Storage Class: {cursor.storage_class}\n")
            file.write(f"{indent}Is Global: {cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT}\n")
        
        file.write("\n")
        
        # 递归处理子节点
        for child in cursor.get_children():
            self._dump_ast(child, file, level + 1)
    
    def _parse_code_elements(self, cursor, parent_func=None):
        """递归查找所有代码元素，包括函数声明、变量声明和函数调用"""
        # 创建函数定义调试文件
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp')
        func_debug_file = os.path.join(temp_dir, 'function_definitions.debug')
        var_debug_file = os.path.join(temp_dir, 'variable_analysis.debug')
        call_debug_file = os.path.join(temp_dir, 'function_calls.debug')
        
        if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            self._process_function_declaration(cursor, func_debug_file, parent_func)
        elif cursor.kind == clang.cindex.CursorKind.VAR_DECL:
            self._process_variable_declaration(cursor, var_debug_file, parent_func)
        elif cursor.kind == clang.cindex.CursorKind.CALL_EXPR and parent_func:
            self._process_function_call(cursor, call_debug_file, parent_func)
        elif cursor.kind == clang.cindex.CursorKind.BINARY_OPERATOR and parent_func:
            self._process_data_flow(cursor, parent_func)
        
        # 递归处理子节点
        for child in cursor.get_children():
            self._parse_code_elements(child, parent_func)
            
    def _process_function_declaration(self, cursor, debug_file, parent_func=None):
        """处理函数声明和定义"""
        func_name = cursor.spelling
        
        # 记录函数定义信息到调试文件
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(f"\nFunction: {func_name}\n")
            f.write(f"Is Definition: {cursor.is_definition()}\n")
            f.write(f"Location: {cursor.location.file}:{cursor.location.line}:{cursor.location.column}\n")
            f.write(f"Return Type: {cursor.result_type.spelling}\n")
            f.write(f"Parameters:\n")
            for param in cursor.get_arguments():
                f.write(f"  - {param.spelling}: {param.type.spelling}\n")
            f.write(f"Extent: {cursor.extent.start.line}-{cursor.extent.end.line}\n")
            f.write("---\n")
        
        # 处理函数定义和声明
        self.functions = getattr(self, 'functions', {})
        
        # 检查是否是函数定义
        is_def = cursor.is_definition()
        
        # 检查是否有函数体
        has_body = self._check_function_has_body(cursor)
        
        # 如果是函数定义且有函数体
        if is_def and has_body:
            self._process_function_definition(cursor, func_name)
            
            # 添加函数节点到控制流图
            self.cfg.add_node(func_name, type='function', id=func_name, location=f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}")
            
            # 处理函数参数，添加到数据流图
            for param in cursor.get_arguments():
                param_name = param.spelling
                param_type = param.type.spelling
                if param_name not in self.variables:
                    self.variables[param_name] = {
                        'type': param_type,
                        'storage': 'StorageClass.NONE',
                        'location': f"{param.location.file}:{param.location.line}:{param.location.column}",
                        'is_pointer': '*' in param_type,
                        'references': [],
                        'is_global': False,
                        'is_static': False,
                        'is_heap': False,
                        'parent_function': func_name
                    }
                # 添加参数到数据流图
                self.dfg.add_node(param_name, type='parameter')
                self.dfg.add_edge(param_name, func_name, type='parameter')
        else:
            self._process_function_declaration_only(cursor, func_name)
    
    def _check_function_has_body(self, cursor):
        """检查函数是否有函数体"""
        has_body = False
        # 调试特定函数
        is_timer_pause = cursor.spelling == "timer_pause"
        
        if cursor.is_definition():
            # 如果是timer_pause函数,打印调试信息

            # 遍历所有子节点查找函数体相关节点
            for child in cursor.get_children():
                # 检查复合语句(标准函数体)
                if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                    has_body = True
                    if is_timer_pause:
                        print("Found COMPOUND_STMT body")
                    break
                # 检查内联函数体
                elif child.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
                    for subchild in child.get_children():
                        if is_timer_pause:
                            print(f"  Subnode kind: {subchild.kind}")
                        if subchild.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                            has_body = True
                            if is_timer_pause:
                                print("Found inline function body")
                            break
                # 检查宏展开的函数体
                elif child.kind == clang.cindex.CursorKind.MACRO_INSTANTIATION:
                    has_body = True
                    if is_timer_pause:
                        print("Found macro body")
                    break
                if has_body:
                    break

            if is_timer_pause:
                print(f"Has body: {has_body}\n")
                
        return has_body
    
    def _process_function_definition(self, cursor, func_name):
        """处理函数定义"""
        # 记录函数信息，如果已存在声明则更新为定义
        func_info = {
            'name': func_name,
            'start_line': cursor.extent.start.line,
            'end_line': cursor.extent.end.line,
            'return_type': cursor.result_type.spelling,
            'parameters': [],
            'local_variables': [],
            'calls': [],
            'location': f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}",
            'is_declaration': False,
            'has_body': True
        }
        
        # 如果已存在函数信息，保留某些字段
        if func_name in self.functions:
            existing_func = self.functions[func_name]
            if existing_func.get('calls'):
                func_info['calls'] = existing_func['calls']
            if existing_func.get('local_variables'):
                func_info['local_variables'] = existing_func['local_variables']
        
        self.functions[func_name] = func_info
        
        # 处理函数参数
        for param in cursor.get_arguments():
            param_info = {
                'name': param.spelling,
                'type': param.type.spelling,
                'location': f"{param.location.file}:{param.location.line}:{param.location.column}"
            }
            self.functions[func_name]['parameters'].append(param_info)
        
        # 递归处理函数体
        for child in cursor.get_children():
            self._parse_code_elements(child, func_name)
    
    def _process_function_declaration_only(self, cursor, func_name):
        """处理函数声明（非定义）"""
        # 处理函数声明，但不覆盖已有的函数定义
        if func_name not in self.functions or self.functions[func_name].get('is_declaration', False):
            self.functions[func_name] = {
                'name': func_name,
                'is_declaration': True,
                'return_type': cursor.result_type.spelling,
                'parameters': [],
                'location': f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}",
                'has_body': False
            }
            # 处理函数参数
            for param in cursor.get_arguments():
                param_info = {
                    'name': param.spelling,
                    'type': param.type.spelling,
                    'location': f"{param.location.file}:{param.location.line}:{param.location.column}"
                }
                self.functions[func_name]['parameters'].append(param_info)
                
    def _process_function_call(self, cursor, debug_file, parent_func):
        """处理函数调用表达式"""
        called_func = cursor.spelling
        
        if not called_func or not parent_func:
            return
            
        # 记录函数调用信息到调试文件
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(f"\nFunction Call: {called_func}\n")
            f.write(f"Called from: {parent_func}\n")
            f.write(f"Location: {cursor.location.file}:{cursor.location.line}:{cursor.location.column}\n")
            f.write(f"Arguments:\n")
            for arg in cursor.get_arguments():
                f.write(f"  - {arg.spelling}\n")
            f.write("---\n")
        
        # 添加函数调用边到控制流图
        self.cfg.add_edge(parent_func, called_func)
        
        # 记录函数调用信息
        call_info = {
            'function': called_func,
            'caller': parent_func,
            'location': f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}",
            'arguments': []
        }
        
        # 分析函数调用参数
        args = list(cursor.get_arguments())
        for arg in args:
            if arg.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
                # 处理字面量参数
                for child in arg.get_children():
                    if child.kind == clang.cindex.CursorKind.STRING_LITERAL:
                        call_info['arguments'].append(child.spelling)
                    elif child.kind == clang.cindex.CursorKind.INTEGER_LITERAL:
                        call_info['arguments'].append(str(child.spelling))
            elif arg.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                # 处理变量参数
                var_name = arg.spelling
                call_info['arguments'].append(var_name)
                if var_name in self.variables:
                    # 添加到数据流图
                    self.dfg.add_edge(var_name, called_func, type='argument')
                    
                    # 记录变量引用
                    self.variables[var_name]['references'].append({
                        'function': called_func,
                        'as_argument': True,
                        'location': f"{arg.location.file}:{arg.location.line}:{arg.location.column}"
                    })
        
        # 记录返回值
        parent = cursor.semantic_parent
        while parent:
            if parent.kind == clang.cindex.CursorKind.VAR_DECL:
                call_info['return_value'] = parent.spelling
                # 如果返回值赋给了变量，添加到数据流图
                if 'return_value' in call_info and call_info['return_value'] in self.variables:
                    self.dfg.add_edge(called_func, call_info['return_value'], type='return')
                break
            parent = parent.semantic_parent
        
        # 添加到函数调用列表
        self.function_calls.append(call_info)
        
        # 更新调用者函数的calls列表
        if parent_func in self.functions:
            if 'calls' not in self.functions[parent_func]:
                self.functions[parent_func]['calls'] = []
            self.functions[parent_func]['calls'].append({
                'function': called_func,
                'location': call_info['location'],
                'arguments': call_info['arguments']
            })
            
        # 检查是否是内存分配函数
        memory_alloc_patterns = ['malloc', 'calloc', 'realloc', 'aligned_alloc', 'valloc', 'pvalloc', 'alloc', 'new', 'create', 'dup', 'clone', 'copy']
        is_memory_alloc = False
        
        # 检查是否是标准内存分配函数
        if called_func in ['malloc', 'calloc', 'realloc', 'aligned_alloc', 'valloc', 'pvalloc']:
            is_memory_alloc = True
        else:
            # 检查是否是自定义内存分配函数
            called_func_lower = called_func.lower()
            for pattern in memory_alloc_patterns:
                if pattern in called_func_lower:
                    is_memory_alloc = True
                    break
                    
        if is_memory_alloc and 'return_value' in call_info:
            var_name = call_info['return_value']
            if var_name in self.variables:
                self.heap_vars.add(var_name)
                self.variables[var_name]['is_heap'] = True
                
    def _process_data_flow(self, cursor, parent_func):
        """处理数据流相关的表达式，如赋值操作"""
        # 处理赋值等二元操作
        lhs = None
        rhs = None
        
        for child in cursor.get_children():
            if not lhs:
                lhs = child
            else:
                rhs = child
                break
        
        if lhs and rhs:
            if lhs.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                lhs_name = lhs.spelling
                
                # 记录变量赋值信息
                if lhs_name in self.variables:
                    # 检查右侧是否是变量引用
                    if rhs.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                        rhs_name = rhs.spelling
                        if rhs_name in self.variables:
                            # 添加到数据流图
                            self.dfg.add_edge(rhs_name, lhs_name, type='assignment')
                            
                            # 记录变量引用
                            self.variables[rhs_name]['references'].append({
                                'assigned_to': lhs_name,
                                'location': f"{rhs.location.file}:{rhs.location.line}:{rhs.location.column}",
                                'in_function': parent_func
                            })
                    
                    # 检查右侧是否是函数调用
                    elif rhs.kind == clang.cindex.CursorKind.CALL_EXPR or self._find_call_expr(rhs):
                        # 函数调用的返回值赋给变量，在_process_function_call中处理
                        pass
                    
                    # 检查右侧是否是内存分配
                    elif self._check_heap_allocation(rhs):
                        self.heap_vars.add(lhs_name)
                        self.variables[lhs_name]['is_heap'] = True
                        
    def _find_call_expr(self, node):
        """递归查找节点中的函数调用表达式"""
        if node.kind == clang.cindex.CursorKind.CALL_EXPR:
            return True
            
        for child in node.get_children():
            if self._find_call_expr(child):
                return True
                
        return False
    
    def _process_variable_declaration(self, cursor, debug_file, parent_func=None):
        """处理变量声明"""
        var_name = cursor.spelling
        var_type = cursor.type.spelling
        storage_class = cursor.storage_class
        
        # 记录变量分析信息到调试文件
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(f"\nVariable: {var_name}\n")
            f.write(f"Type: {var_type}\n")
            f.write(f"Storage Class: {storage_class}\n")
            f.write(f"Location: {cursor.location.file}:{cursor.location.line}:{cursor.location.column}\n")
            f.write(f"Parent Function: {parent_func}\n")
            f.write(f"Is Global: {cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT}\n")
            f.write(f"Is Static: {storage_class == clang.cindex.StorageClass.STATIC}\n")
            f.write("---\n")
        
        # 记录变量信息
        var_info = {
            'type': var_type,
            'storage': storage_class,
            'location': f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}",
            'is_pointer': '*' in var_type,
            'references': [],
            'is_global': cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT,
            'is_static': storage_class == clang.cindex.StorageClass.STATIC,
            'is_heap': False,
            'parent_function': parent_func
        }
        
        # 只有全局变量和静态变量才添加到variables集合中
        if cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT or \
           storage_class == clang.cindex.StorageClass.STATIC:
            self.variables[var_name] = var_info
        
        # 如果是函数内的局部变量，添加到函数的局部变量列表
        if parent_func and parent_func in self.functions:
            self.functions[parent_func]['local_variables'].append({
                'name': var_name,
                'type': var_type,
                'location': var_info['location']
            })
        
        # 识别全局变量和静态变量
        if storage_class == clang.cindex.StorageClass.STATIC:
            self.static_vars.add(var_name)
            # 如果是文件作用域的静态变量，也将其添加到全局变量集合中
            if cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT:
                self.global_vars.add(var_name)
        elif cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT:
            self.global_vars.add(var_name)
        
        # 检查是否是堆分配变量
        if var_info['is_pointer']:
            self._check_heap_variable(cursor, var_name)
    
    def _check_heap_allocation(self, node):
        """检查节点是否表示堆内存分配"""
        if node is None:
            return False
            
        # 检查函数调用表达式
        if node.kind == clang.cindex.CursorKind.CALL_EXPR:
            # 获取函数名
            func_name = node.spelling.lower()
            
            # 检查标准内存分配函数
            if node.spelling in ['malloc', 'calloc', 'realloc', 'aligned_alloc', 'valloc', 'pvalloc']:
                return True
                
            # 检查自定义内存分配函数 - 更全面的模式匹配
            memory_alloc_patterns = ['alloc', 'new', 'create', 'dup', 'clone', 'copy']
            for pattern in memory_alloc_patterns:
                if pattern in func_name:
                    return True
                    
        # 检查类型转换表达式
        elif node.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR:
            # 递归检查类型转换表达式中的所有子节点
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        # 检查一元操作符 (如 *ptr)
        elif node.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        # 检查条件表达式 (三元运算符)
        elif node.kind == clang.cindex.CursorKind.CONDITIONAL_OPERATOR:
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        # 检查复合语句
        elif node.kind == clang.cindex.CursorKind.COMPOUND_STMT:
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        return False
    
    def _check_heap_variable(self, cursor, var_name):
        """检查变量是否是堆分配变量"""
        # 检查初始化表达式
        for child in cursor.get_children():
            # 检查类型转换表达式
            if child.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR:
                for subchild in child.get_children():
                    if self._check_heap_allocation(subchild):
                        self.heap_vars.add(var_name)
                        # 确保变量在字典中存在
                        if var_name in self.variables:
                            self.variables[var_name]['is_heap'] = True
                        break
            # 直接检查内存分配函数调用
            elif self._check_heap_allocation(child):
                self.heap_vars.add(var_name)
                # 确保变量在字典中存在
                if var_name in self.variables:
                    self.variables[var_name]['is_heap'] = True
                break
            # 检查赋值表达式
            elif child.kind == clang.cindex.CursorKind.BINARY_OPERATOR:
                for subchild in child.get_children():
                    if self._check_heap_allocation(subchild):
                        self.heap_vars.add(var_name)
                        # 确保变量在字典中存在
                        if var_name in self.variables:
                            self.variables[var_name]['is_heap'] = True
                        break
            # 检查函数调用中的内存分配
            elif child.kind == clang.cindex.CursorKind.CALL_EXPR:
                if self._check_heap_allocation(child):
                    self.heap_vars.add(var_name)
                    # 确保变量在字典中存在
                    if var_name in self.variables:
                        self.variables[var_name]['is_heap'] = True
                    break
        
        return False
    
    def _check_heap_allocation_extended(self, node):
        """扩展的堆内存分配检查函数"""
        if node is None:
            return False
            
        # 检查括号表达式
        if node.kind == clang.cindex.CursorKind.PAREN_EXPR:
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        # 检查一元操作符 (如 *ptr)
        elif node.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        # 检查条件表达式 (三元运算符)
        elif node.kind == clang.cindex.CursorKind.CONDITIONAL_OPERATOR:
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        # 检查复合语句
        elif node.kind == clang.cindex.CursorKind.COMPOUND_STMT:
            for child in node.get_children():
                if self._check_heap_allocation(child):
                    return True
                    
        return False
    
    def _check_heap_variable(self, cursor, var_name):
        """检查变量是否是堆分配变量"""
        # 检查初始化表达式
        for child in cursor.get_children():
            # 检查类型转换表达式
            if child.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR:
                for subchild in child.get_children():
                    if self._check_heap_allocation(subchild):
                        self.heap_vars.add(var_name)
                        # 确保变量在字典中存在
                        if var_name in self.variables:
                            self.variables[var_name]['is_heap'] = True
                        break
            # 直接检查内存分配函数调用
            elif self._check_heap_allocation(child):
                self.heap_vars.add(var_name)
                # 确保变量在字典中存在
                if var_name in self.variables:
                    self.variables[var_name]['is_heap'] = True
                break
            # 检查赋值表达式
            elif child.kind == clang.cindex.CursorKind.BINARY_OPERATOR:
                for subchild in child.get_children():
                    if self._check_heap_allocation(subchild):
                        self.heap_vars.add(var_name)
                        # 确保变量在字典中存在
                        if var_name in self.variables:
                            self.variables[var_name]['is_heap'] = True
                        break
            # 检查函数调用中的内存分配
            elif child.kind == clang.cindex.CursorKind.CALL_EXPR:
                if self._check_heap_allocation(child):
                    self.heap_vars.add(var_name)
                    # 确保变量在字典中存在
                    if var_name in self.variables:
                        self.variables[var_name]['is_heap'] = True
                    break
    
    def _build_cfg_dfg(self, cursor, parent_func=None):
        """构建控制流图和数据流图"""
        if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            func_name = cursor.spelling
            
            # 检查是否是函数定义
            is_def = cursor.is_definition()
            
            # 检查是否有函数体
            has_body = False
            for child in cursor.get_children():
                # 检查复合语句(标准函数体)
                if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                    has_body = True
                    break
                # 检查内联函数体
                elif child.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
                    for subchild in child.get_children():
                        if subchild.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                            has_body = True
                            break
                # 检查宏展开的函数体
                elif child.kind == clang.cindex.CursorKind.MACRO_INSTANTIATION:
                    has_body = True
                    break
                if has_body:
                    break
            
            # 只处理函数定义，跳过纯声明
            if not is_def or not has_body:
                return
                
            # 添加函数节点到控制流图
            self.cfg.add_node(func_name, type='function', id=func_name, location=f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}")
            
            # 处理函数参数
            for param in cursor.get_arguments():
                param_name = param.spelling
                param_type = param.type.spelling
                if param_name not in self.variables:
                    self.variables[param_name] = {
                        'type': param_type,
                        'storage': 'StorageClass.NONE',
                        'location': f"{param.location.file}:{param.location.line}:{param.location.column}",
                        'is_pointer': '*' in param_type,
                        'references': [],
                        'is_global': False,
                        'is_static': False,
                        'is_heap': False
                    }
                # 添加参数到数据流图
                self.dfg.add_node(param_name, type='parameter')
                self.dfg.add_edge(param_name, func_name, type='parameter')
            
            # 处理函数内部
            for child in cursor.get_children():
                self._build_cfg_dfg(child, func_name)
                
        elif cursor.kind == clang.cindex.CursorKind.CALL_EXPR:
            # 记录函数调用
            called_func = cursor.spelling
            if parent_func and called_func:
                # 添加函数调用边到控制流图
                self.cfg.add_edge(parent_func, called_func)
                # 记录函数调用信息
                call_info = {
                    'function': called_func,
                    'location': f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}",
                    'arguments': []
                }
                
                # 分析函数调用参数
                args = list(cursor.get_arguments())
                for arg in args:
                    if arg.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
                        # 处理字面量参数
                        for child in arg.get_children():
                            if child.kind == clang.cindex.CursorKind.STRING_LITERAL:
                                call_info['arguments'].append(child.spelling)
                            elif child.kind == clang.cindex.CursorKind.INTEGER_LITERAL:
                                call_info['arguments'].append(str(child.spelling))
                    elif arg.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                        # 处理变量参数
                        var_name = arg.spelling
                        call_info['arguments'].append(var_name)
                        if var_name in self.variables:
                            # 添加到数据流图
                            self.dfg.add_edge(var_name, called_func, type='argument')
                
                # 记录返回值
                parent = cursor.semantic_parent
                while parent:
                    if parent.kind == clang.cindex.CursorKind.VAR_DECL:
                        call_info['return_value'] = parent.spelling
                        break
                    parent = parent.semantic_parent
                
                self.function_calls.append(call_info)
                
                # 检查是否是内存分配函数
                memory_alloc_patterns = ['malloc', 'calloc', 'realloc', 'aligned_alloc', 'valloc', 'pvalloc', 'alloc', 'new', 'create', 'dup', 'clone', 'copy']
                is_memory_alloc = False
                
                # 检查是否是标准内存分配函数
                if called_func in ['malloc', 'calloc', 'realloc', 'aligned_alloc', 'valloc', 'pvalloc']:
                    is_memory_alloc = True
                else:
                    # 检查是否是自定义内存分配函数
                    called_func_lower = called_func.lower()
                    for pattern in memory_alloc_patterns:
                        if pattern in called_func_lower:
                            is_memory_alloc = True
                            break
                            
                if is_memory_alloc:
                    # 查找赋值目标变量
                    parent = cursor.semantic_parent
                    while parent:
                        if parent.kind == clang.cindex.CursorKind.VAR_DECL:
                            var_name = parent.spelling
                            if var_name in self.variables:
                                self.heap_vars.add(var_name)
                                self.variables[var_name]['is_heap'] = True
                            break
                        parent = parent.semantic_parent
                
                # 分析参数传递
                args = list(cursor.get_arguments())
                for i, arg in enumerate(args):
                    if arg.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                        var_name = arg.spelling
                        if var_name in self.variables:
                            # 记录变量引用
                            self.variables[var_name]['references'].append({
                                'function': called_func,
                                'as_argument': i,
                                'location': f"{arg.location.file}:{arg.location.line}:{arg.location.column}"
                            })
                            
                            # 添加到数据流图
                            self.dfg.add_edge(var_name, called_func, type='argument')
        
        elif cursor.kind == clang.cindex.CursorKind.BINARY_OPERATOR:
            # 处理赋值等二元操作
            lhs = None
            rhs = None
            
            for child in cursor.get_children():
                if not lhs:
                    lhs = child
                else:
                    rhs = child
                    break
            
            if lhs and rhs:
                if lhs.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                    lhs_name = lhs.spelling
                    if lhs_name in self.variables:
                        # 检查右侧是否是内存分配
                        def is_heap_allocation(node):
                            if node is None:
                                return False
                                
                            if node.kind == clang.cindex.CursorKind.CALL_EXPR:
                                # 检查标准内存分配函数
                                if node.spelling in ['malloc', 'calloc', 'realloc', 'aligned_alloc', 'valloc', 'pvalloc']:
                                    return True
                                    
                                # 检查自定义内存分配函数
                                func_name = node.spelling.lower()
                                memory_alloc_patterns = ['alloc', 'new', 'create', 'dup', 'clone', 'copy']
                                for pattern in memory_alloc_patterns:
                                    if pattern in func_name:
                                        return True
                            
                            # 检查类型转换表达式
                            elif node.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR:
                                for child in node.get_children():
                                    if is_heap_allocation(child):
                                        return True
                                        
                            # 检查括号表达式
                            elif node.kind == clang.cindex.CursorKind.PAREN_EXPR:
                                for child in node.get_children():
                                    if is_heap_allocation(child):
                                        return True
                                        
                            return False
                            
                        if is_heap_allocation(rhs):
                                self.heap_vars.add(lhs_name)
                                self.variables[lhs_name]['is_heap'] = True
                        
                        # 添加到数据流图
                        if rhs.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                            rhs_name = rhs.spelling
                            if rhs_name in self.variables:
                                self.dfg.add_edge(rhs_name, lhs_name, type='assignment')
        
        # 递归处理其他子节点
        for child in cursor.get_children():
            if child.kind != clang.cindex.CursorKind.FUNCTION_DECL:  # 避免重复处理函数
                self._build_cfg_dfg(child, parent_func)
    

    def _track_heap_variables(self):
        """跟踪指向堆内存的指针变量"""
        # 第一轮：标记直接指向堆内存的指针变量
        for var_name in self.heap_vars:
            var_info = self.variables.get(var_name)
            if not var_info:
                continue
                
            # 分析该指针变量的所有引用
            for ref in var_info['references']:
                func = ref['function']
                # 在数据流图中添加指向堆内存的特殊标记
                self.dfg.add_edge(var_name, func, type='heap_reference')
        
        # 第二轮：跟踪指向堆内存的指针传递
        # 查找数据流图中的赋值关系，如果源变量指向堆内存，则目标变量也指向堆内存
        heap_propagated = True
        while heap_propagated:
            heap_propagated = False
            for src, dst, data in self.dfg.edges(data=True):
                if data.get('type') == 'assignment' and src in self.heap_vars and dst not in self.heap_vars:
                    if dst in self.variables and self.variables[dst]['is_pointer']:
                        self.heap_vars.add(dst)
                        self.variables[dst]['is_heap'] = True
                        heap_propagated = True
                        
        # 第三轮：检查结构体成员指针
        # 分析结构体成员是否指向堆内存
        for var_name, var_info in self.variables.items():
            # 检查是否是结构体指针且指向堆内存
            if var_info['is_pointer'] and ('struct' in var_info['type'].lower() or 'union' in var_info['type'].lower()):
                # 查找所有引用这个结构体的成员
                for ref_var, ref_info in self.variables.items():
                    if ref_var != var_name and ref_info['is_pointer']:
                        # 检查是否是通过结构体成员访问
                        for ref in ref_info.get('references', []):
                            if var_name in str(ref):
                                # 标记结构体成员指针指向堆内存
                                self.heap_vars.add(ref_var)
                                self.variables[ref_var]['is_heap'] = True
    
    def _build_business_logic(self):
        """基于控制流图和数据流图构建业务逻辑框图"""
        # 定义业务模块
        business_modules = {
            'timer_system_initialization': ['timer_system_init'],
            'timer_creation': ['timer_create'],
            'timer_management': ['timer_start', 'timer_pause', 'timer_cancel'],
            'timer_execution': ['timer_update', 'find_timer'],
            'timer_cleanup': ['timer_system_destroy'],
            'timer_utility': ['timer_count']
        }
        
        # 确保所有函数都被识别
        for func_name in self.functions:
            found = False
            for module_funcs in business_modules.values():
                if func_name in module_funcs:
                    found = True
                    break
            if not found:
                # 根据函数名称特征分类未识别的函数
                if 'timer' in func_name.lower():
                    if 'init' in func_name.lower():
                        business_modules['timer_system_initialization'].append(func_name)
                    elif 'create' in func_name.lower():
                        business_modules['timer_creation'].append(func_name)
                    elif any(op in func_name.lower() for op in ['start', 'pause', 'cancel', 'stop']):
                        business_modules['timer_management'].append(func_name)
                    elif 'update' in func_name.lower() or 'find' in func_name.lower():
                        business_modules['timer_execution'].append(func_name)
                    elif 'destroy' in func_name.lower() or 'clean' in func_name.lower():
                        business_modules['timer_cleanup'].append(func_name)
                    else:
                        business_modules['timer_utility'].append(func_name)
        
        # 添加业务模块节点
        for module_name, functions in business_modules.items():
            self.business_logic.add_node(module_name, type='module', id=module_name)
            # 将函数与业务模块关联
            for func in functions:
                if func in self.cfg.nodes():
                    self.business_logic.add_node(func, type='function', id=func)
                    self.business_logic.add_edge(module_name, func, type='contains')
        
        # 根据函数调用关系建立业务模块之间的关联
        for call_info in self.function_calls:
            caller = None
            callee = call_info['function']
            
            # 查找调用者所属的业务模块
            for module_name, functions in business_modules.items():
                if any(func in functions for func in self.cfg.predecessors(callee)):
                    caller = module_name
                    break
            
            # 查找被调用者所属的业务模块
            callee_module = None
            for module_name, functions in business_modules.items():
                if callee in functions:
                    callee_module = module_name
                    break
            
            # 添加业务模块之间的关联
            if caller and callee_module and caller != callee_module:
                self.business_logic.add_edge(caller, callee_module, type='depends_on')
        
        # 添加关键数据流
        for var_name in self.global_vars:
            if var_name in self.variables:
                # 查找使用该全局变量的函数
                for ref in self.variables[var_name].get('references', []):
                    func_name = ref.get('function')
                    if func_name:
                        # 查找函数所属的业务模块
                        for module_name, functions in business_modules.items():
                            if func_name in functions:
                                self.business_logic.add_node(var_name, type='variable', id=var_name)
                                self.business_logic.add_edge(module_name, var_name, type='uses')
                                break
    
    def visualize_cfg(self, output_file='control_flow_graph.png'):
        """可视化控制流图"""
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.cfg)
        nx.draw(self.cfg, pos, with_labels=True, node_color='lightblue', 
                node_size=2000, arrows=True, font_size=10)
        plt.title("Control Flow Graph")
        plt.savefig(output_file)
        plt.close()
    
    def visualize_dfg(self, output_file='data_flow_graph.png'):
        """可视化数据流图"""
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.dfg)
        
        # 绘制不同类型的节点
        global_nodes = [n for n in self.dfg.nodes() if n in self.global_vars]
        static_nodes = [n for n in self.dfg.nodes() if n in self.static_vars]
        heap_nodes = [n for n in self.dfg.nodes() if n in self.heap_vars]
        other_nodes = [n for n in self.dfg.nodes() if n not in global_nodes + static_nodes + heap_nodes]
        
        nx.draw_networkx_nodes(self.dfg, pos, nodelist=global_nodes, node_color='red', node_size=1500, label='Global Variables')
        nx.draw_networkx_nodes(self.dfg, pos, nodelist=static_nodes, node_color='green', node_size=1500, label='Static Variables')
        nx.draw_networkx_nodes(self.dfg, pos, nodelist=heap_nodes, node_color='orange', node_size=1500, label='Heap Variables')
        nx.draw_networkx_nodes(self.dfg, pos, nodelist=other_nodes, node_color='lightblue', node_size=1500)
        
        # 绘制边和标签
        nx.draw_networkx_edges(self.dfg, pos, arrows=True)
        nx.draw_networkx_labels(self.dfg, pos, font_size=10)
        
        plt.title("Data Flow Graph")
        plt.legend()
        plt.savefig(output_file)
        plt.close()
    
    def export_to_json(self, output_file):
        """将分析结果导出为JSON格式
        Args:
            output_file: JSON文件的输出路径
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 准备可序列化的数据结构
            def serialize_graph(graph):
                return {
                    'nodes': [
                        {'id': str(node), 'data': data}
                        for node, data in graph.nodes(data=True)
                    ],
                    'edges': [
                        {
                            'source': str(src),
                            'target': str(dst),
                            'data': data
                        }
                        for src, dst, data in graph.edges(data=True)
                    ]
                }
            
            # 处理函数信息，确保定义优先于声明
            processed_functions = {}
            # 先处理所有函数定义
            for name, func_info in self.functions.items():
                if not func_info.get('is_declaration', True) and func_info.get('has_body', False):
                    processed_functions[name] = func_info
            
            # 再处理函数声明（只处理没有定义的函数）
            for name, func_info in self.functions.items():
                if name not in processed_functions:
                    processed_functions[name] = func_info
            
            result = {
                'files': self.files,
                'variables': {
                    name: {
                        **{k: (v if isinstance(v, (bool, int, float, str, type(None))) else 
                             (v if k == 'references' and isinstance(v, list) else str(v)))
                           for k, v in info.items()},
                        # 确保is_heap属性被正确设置，表示该指针是否指向堆内存
                        'is_heap': name in self.heap_vars and info['is_pointer']
                    }
                    for name, info in self.variables.items()
                },
                'function_calls': [
                    {'caller': str(call_info['caller']), 'callee': str(call_info['function'])}
                    for call_info in self.function_calls
                ],
                'control_flow': serialize_graph(self.cfg),
                'data_flow': serialize_graph(self.dfg),
                'business_logic': serialize_graph(self.business_logic),
                'functions': processed_functions
            }
            
            # 写入JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    def visualize_business_logic(self, output_file='business_logic.png'):
        """可视化业务逻辑框图"""
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.business_logic)
        nx.draw(self.business_logic, pos, with_labels=True, node_color='lightgreen', 
                node_size=2000, arrows=True, font_size=10)
        plt.title("Business Logic Diagram")
        plt.savefig(output_file)
        plt.close()