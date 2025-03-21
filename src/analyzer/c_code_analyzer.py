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
        for file_path in self.files:
            # 准备编译参数，包括包含路径
            args = []
            for include_path in self.include_paths:
                args.append(f'-I{include_path}')
            
            # 解析翻译单元
            try:
                tu = self.index.parse(file_path, args)
                if tu:
                    self._find_variables(tu.cursor)
                    self._build_cfg_dfg(tu.cursor)
                else:
                    print(f"Warning: Failed to parse {file_path}")
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                continue
                
        self._track_heap_variables()
        self._build_business_logic()
        return self
    
    def _find_variables(self, cursor):
        """递归查找所有变量声明"""
        if cursor.kind == clang.cindex.CursorKind.VAR_DECL:
            var_name = cursor.spelling
            var_type = cursor.type.spelling
            storage_class = cursor.storage_class
            
            # 记录变量信息
            self.variables[var_name] = {
                'type': var_type,
                'storage': storage_class,
                'location': f"{cursor.location.file}:{cursor.location.line}:{cursor.location.column}",
                'is_pointer': '*' in var_type,
                'references': [],
                'is_global': cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT,
                'is_static': storage_class == clang.cindex.StorageClass.STATIC,
                'is_heap': False
            }
            
            # 识别全局变量和静态变量
            if storage_class == clang.cindex.StorageClass.STATIC:
                self.static_vars.add(var_name)
            elif cursor.semantic_parent.kind == clang.cindex.CursorKind.TRANSLATION_UNIT:
                self.global_vars.add(var_name)
                
            # 检查是否是堆分配变量
            def check_heap_allocation(node):
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
                        if check_heap_allocation(child):
                            return True
                            
                # 检查括号表达式
                elif node.kind == clang.cindex.CursorKind.PAREN_EXPR:
                    for child in node.get_children():
                        if check_heap_allocation(child):
                            return True
                            
                # 检查一元操作符 (如 *ptr)
                elif node.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
                    for child in node.get_children():
                        if check_heap_allocation(child):
                            return True
                            
                # 检查条件表达式 (三元运算符)
                elif node.kind == clang.cindex.CursorKind.CONDITIONAL_OPERATOR:
                    for child in node.get_children():
                        if check_heap_allocation(child):
                            return True
                            
                # 检查复合语句
                elif node.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                    for child in node.get_children():
                        if check_heap_allocation(child):
                            return True
                            
                return False
            
            # 检查变量是否为指针类型
            is_pointer = '*' in var_type
            
            # 如果是指针类型，默认检查更严格
            if is_pointer:
                # 检查初始化表达式
                for child in cursor.get_children():
                    # 检查类型转换表达式
                    if child.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR:
                        for subchild in child.get_children():
                            if check_heap_allocation(subchild):
                                self.heap_vars.add(var_name)
                                self.variables[var_name]['is_heap'] = True
                                break
                    # 直接检查内存分配函数调用
                    elif check_heap_allocation(child):
                        self.heap_vars.add(var_name)
                        self.variables[var_name]['is_heap'] = True
                        break
                    # 检查赋值表达式
                    elif child.kind == clang.cindex.CursorKind.BINARY_OPERATOR:
                        for subchild in child.get_children():
                            if check_heap_allocation(subchild):
                                self.heap_vars.add(var_name)
                                self.variables[var_name]['is_heap'] = True
                                break
                    # 检查函数调用中的内存分配
                    elif child.kind == clang.cindex.CursorKind.CALL_EXPR:
                        if check_heap_allocation(child):
                            self.heap_vars.add(var_name)
                            self.variables[var_name]['is_heap'] = True
                            break
        
        # 递归处理子节点
        for child in cursor.get_children():
            self._find_variables(child)
    
    def _build_cfg_dfg(self, cursor, parent_func=None):
        """构建控制流图和数据流图"""
        if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            func_name = cursor.spelling
            self.cfg.add_node(func_name, type='function')
            
            # 处理函数内部
            for child in cursor.get_children():
                self._build_cfg_dfg(child, func_name)
                
        elif cursor.kind == clang.cindex.CursorKind.CALL_EXPR:
            # 记录函数调用
            called_func = cursor.spelling
            if parent_func and called_func:
                self.cfg.add_edge(parent_func, called_func)
                self.function_calls.append((parent_func, called_func))
                
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
        """跟踪堆变量的引用和传递"""
        # 第一轮：标记直接的堆变量
        for var_name in self.heap_vars:
            var_info = self.variables.get(var_name)
            if not var_info:
                continue
                
            # 分析该堆变量的所有引用
            for ref in var_info['references']:
                func = ref['function']
                # 在数据流图中添加堆变量的特殊标记
                self.dfg.add_edge(var_name, func, type='heap_reference')
        
        # 第二轮：跟踪堆变量的传递
        # 查找数据流图中的赋值关系，如果源变量是堆变量，则目标变量也应该是堆变量
        heap_propagated = True
        while heap_propagated:
            heap_propagated = False
            for src, dst, data in self.dfg.edges(data=True):
                if data.get('type') == 'assignment' and src in self.heap_vars and dst not in self.heap_vars:
                    if dst in self.variables:
                        self.heap_vars.add(dst)
                        self.variables[dst]['is_heap'] = True
                        heap_propagated = True
                        
        # 第三轮：检查结构体成员指针
        # 如果一个结构体变量是堆分配的，那么它的成员指针也应该被标记为堆变量
        for var_name, var_info in self.variables.items():
            if var_info['is_heap'] and var_info['is_pointer']:
                # 查找所有引用这个变量的地方
                for ref_var, ref_info in self.variables.items():
                    if ref_var != var_name and ref_info['is_pointer']:
                        # 检查是否是通过结构体成员访问
                        for ref in ref_info.get('references', []):
                            if var_name in str(ref):
                                self.heap_vars.add(ref_var)
                                self.variables[ref_var]['is_heap'] = True
    
    def _build_business_logic(self):
        """基于数据流图构建业务逻辑框图"""
        # 从数据流图中提取关键节点和边
        for node in self.dfg.nodes():
            if node in self.function_calls or node in self.global_vars:
                self.business_logic.add_node(node)
        
        # 添加关键数据流边
        for src, dst, data in self.dfg.edges(data=True):
            if src in self.business_logic.nodes() and dst in self.business_logic.nodes():
                self.business_logic.add_edge(src, dst, **data)
    
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
            
            result = {
                'files': self.files,
                'variables': {
                    name: {
                        **{k: str(v) if not isinstance(v, (bool, int, float, str, type(None)))
                           else v for k, v in info.items()},
                        'is_global': name in self.global_vars,
                        'is_static': name in self.static_vars,
                        'is_heap': name in self.heap_vars
                    }
                    for name, info in self.variables.items()
                },
                'function_calls': [
                    {'caller': str(caller), 'callee': str(callee)}
                    for caller, callee in self.function_calls
                ],
                'control_flow': serialize_graph(self.cfg),
                'data_flow': serialize_graph(self.dfg),
                'business_logic': serialize_graph(self.business_logic)
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