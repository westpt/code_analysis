import os
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patches as mpatches

class DataFlowVisualizer:
    """数据流可视化工具，用于展示函数内部和函数间的数据流图"""
    
    def __init__(self, output_dir='output'):
        """初始化数据流可视化工具
        
        Args:
            output_dir: 输出目录路径
        """
        # 全局中文字体配置
        # 中文字体配置
        try:
            # 按优先级设置字体族
            font_paths = [
                'C:/Windows/Fonts/msyh.ttc',  # Microsoft YaHei
                'C:/Windows/Fonts/simhei.ttf',  # SimHei
                'C:/Windows/Fonts/simfang.ttf'  # 仿宋
            ]
            
            valid_fonts = []
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        font = plt.matplotlib.font_manager.FontProperties(fname=path)
                        valid_fonts.append(font.get_name())
                    except:
                        continue
            
            if valid_fonts:
                plt.rcParams['font.sans-serif'] = valid_fonts + ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
                plt.rcParams['font.family'] = 'sans-serif'
                plt.rcParams['axes.unicode_minus'] = False
            else:
                plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
        except Exception as e:
            print(f'字体加载失败: {e}\n请安装中文字体：1. 下载SimHei.ttf 2. 复制到C:\\Windows\\Fonts目录')
            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # 最后备用字体
            
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def visualize_function_data_flow(self, function_name, local_dfg, variables, global_vars, static_vars, heap_vars, output_file=None):
        """可视化函数内部数据流图
        
        Args:
            function_name: 函数名称
            local_dfg: 函数内部数据流图
            variables: 变量信息字典
            global_vars: 全局变量集合
            static_vars: 静态变量集合
            heap_vars: 堆变量集合
            output_file: 输出文件路径，默认为None，将使用函数名生成路径
        """
        if not output_file:
            output_file = os.path.join(self.output_dir, f"{function_name}_data_flow.png")
        
        plt.figure(figsize=(14, 10))
        
        # 使用分层布局，更清晰地展示数据流向
        pos = nx.nx_agraph.graphviz_layout(local_dfg, prog='dot') if nx.nx_agraph.graphviz_layout else nx.spring_layout(local_dfg)
        
        # 准备不同类型的节点
        input_nodes = [n for n in local_dfg.nodes() if isinstance(n, str) and n.startswith("INPUT:")]
        output_nodes = [n for n in local_dfg.nodes() if isinstance(n, str) and n.startswith("OUTPUT:")]
        call_nodes = [n for n in local_dfg.nodes() if isinstance(n, str) and n.startswith("CALL:")]
        
        # 变量节点分类
        global_nodes = [n for n in local_dfg.nodes() if n in global_vars]
        static_nodes = [n for n in local_dfg.nodes() if n in static_vars]
        heap_nodes = [n for n in local_dfg.nodes() if n in heap_vars]
        param_nodes = [n for n in local_dfg.nodes() if n not in input_nodes + output_nodes + call_nodes + global_nodes + static_nodes + heap_nodes and 
                      any(data.get('type') == 'parameter' for _, _, data in local_dfg.in_edges(n, data=True))]
        local_nodes = [n for n in local_dfg.nodes() if n not in input_nodes + output_nodes + call_nodes + global_nodes + static_nodes + heap_nodes + param_nodes]
        
        # 绘制不同类型的节点
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=input_nodes, node_color='lightgreen', node_size=1200, label='输入参数')
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=output_nodes, node_color='lightblue', node_size=1200, label='输出结果')
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=call_nodes, node_color='yellow', node_size=1200, label='函数调用')
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=global_nodes, node_color='red', node_size=1200, label='全局变量')
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=static_nodes, node_color='purple', node_size=1200, label='静态变量')
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=heap_nodes, node_color='orange', node_size=1200, label='堆变量')
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=param_nodes, node_color='cyan', node_size=1200, label='函数参数')
        nx.draw_networkx_nodes(local_dfg, pos, nodelist=local_nodes, node_color='gray', node_size=1200, label='局部变量')
        
        # 绘制边和标签
        edge_colors = []
        edge_labels = {}
        
        for u, v, data in local_dfg.edges(data=True):
            edge_type = data.get('type', 'unknown')
            if edge_type == 'assignment':
                edge_colors.append('blue')
                edge_labels[(u, v)] = '赋值'
            elif edge_type == 'parameter_input':
                edge_colors.append('green')
                edge_labels[(u, v)] = '参数输入'
            elif edge_type == 'return':
                edge_colors.append('red')
                edge_labels[(u, v)] = '返回值'
            elif edge_type == 'argument':
                edge_colors.append('purple')
                edge_labels[(u, v)] = '函数参数'
            else:
                edge_colors.append('black')
                edge_labels[(u, v)] = edge_type
        
        nx.draw_networkx_edges(local_dfg, pos, arrows=True, edge_color=edge_colors)
        nx.draw_networkx_edge_labels(local_dfg, pos, edge_labels=edge_labels, font_size=8)
        
        # 绘制节点标签，处理特殊前缀
        node_labels = {}
        for node in local_dfg.nodes():
            if isinstance(node, str):
                if node.startswith("INPUT:"):
                    node_labels[node] = node[6:]
                elif node.startswith("OUTPUT:"):
                    node_labels[node] = node[7:]
                elif node.startswith("CALL:"):
                    node_labels[node] = node[5:]
                else:
                    node_labels[node] = node
            else:
                node_labels[node] = str(node)
        
        nx.draw_networkx_labels(local_dfg, pos, labels=node_labels, font_size=10)
        
        # 添加图例和标题
        plt.title(f"函数 {function_name} 内部数据流图")
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        handles = [
            mpatches.Patch(color='lightgreen', label='输入参数'),
            mpatches.Patch(color='lightblue', label='输出结果'),
            mpatches.Patch(color='yellow', label='函数调用'),
            mpatches.Patch(color='red', label='全局变量'),
            mpatches.Patch(color='purple', label='静态变量'),
            mpatches.Patch(color='orange', label='堆变量'),
            mpatches.Patch(color='cyan', label='函数参数'),
            mpatches.Patch(color='gray', label='局部变量')
        ]
        plt.legend(handles=handles, labels=['输入参数', '输出结果', '函数调用', '全局变量', '静态变量', '堆变量', '函数参数', '局部变量'])
        plt.axis('off')
        
        # 保存图像
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def visualize_function_side_effects(self, function_name, side_effects, output_file=None):
        """可视化函数副作用
        
        Args:
            function_name: 函数名称
            side_effects: 函数副作用信息
            output_file: 输出文件路径，默认为None，将使用函数名生成路径
        """
        if not output_file:
            output_file = os.path.join(self.output_dir, f"{function_name}_side_effects.png")
        
        plt.figure(figsize=(10, 8))
        
        # 准备副作用数据
        global_reads = side_effects.get('global_vars_read', set())
        global_writes = side_effects.get('global_vars_write', set())
        file_ops = side_effects.get('file_operations', [])
        heap_ops = side_effects.get('heap_operations', [])
        network_ops = side_effects.get('network_operations', [])
        
        # 创建表格数据
        table_data = []
        table_data.append(['副作用类型', '详细信息'])
        
        if global_reads:
            table_data.append(['读取全局变量', ', '.join(global_reads)])
        if global_writes:
            table_data.append(['修改全局变量', ', '.join(global_writes)])
        if file_ops:
            file_op_details = [f"{op['operation']} {op.get('file', '')}" for op in file_ops]
            table_data.append(['文件操作', '\n'.join(file_op_details)])
        if heap_ops:
            heap_op_details = [f"{op['operation']} {op.get('variable', '')}" for op in heap_ops]
            table_data.append(['堆内存操作', '\n'.join(heap_op_details)])
        if network_ops:
            network_op_details = [f"{op['operation']} {op.get('target', '')}" for op in network_ops]
            table_data.append(['网络操作', '\n'.join(network_op_details)])
        
        if len(table_data) == 1:
            table_data.append(['无副作用', '该函数没有检测到副作用'])
        
        # 创建表格
        ax = plt.subplot(111)
        ax.axis('off')
        table = ax.table(cellText=table_data, loc='center', cellLoc='left')
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 1.5)
        
        # 设置标题
        plt.title(f"函数 {function_name} 副作用分析")
        
        # 保存图像
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def visualize_all_functions_data_flow(self, functions, variables, global_vars, static_vars, heap_vars):
        """可视化所有函数的内部数据流图
        
        Args:
            functions: 函数信息字典
            variables: 变量信息字典
            global_vars: 全局变量集合
            static_vars: 静态变量集合
            heap_vars: 堆变量集合
        """
        results = {}
        
        for func_name, func_info in functions.items():
            # 跳过没有函数体的函数声明
            if not func_info.get('has_body', False):
                continue
                
            # 获取函数内部数据流图
            local_dfg = func_info.get('local_dfg', nx.DiGraph())
            
            # 如果数据流图为空，跳过
            if len(local_dfg.nodes()) == 0:
                continue
                
            # 可视化函数内部数据流图
            output_file = self.visualize_function_data_flow(
                func_name, local_dfg, variables, global_vars, static_vars, heap_vars)
                
            # 可视化函数副作用
            side_effects_file = self.visualize_function_side_effects(
                func_name, func_info.get('side_effects', {}))
                
            results[func_name] = {
                'data_flow_graph': output_file,
                'side_effects': side_effects_file
            }
        
        return results
    
    def visualize_global_data_flow(self, global_dfg, global_vars, static_vars, heap_vars, output_file=None):
        """可视化全局数据流图（函数间数据流）
        
        Args:
            global_dfg: 全局数据流图
            global_vars: 全局变量集合
            static_vars: 静态变量集合
            heap_vars: 堆变量集合
            output_file: 输出文件路径
        """
        if not output_file:
            output_file = os.path.join(self.output_dir, "global_data_flow.png")
        
        plt.figure(figsize=(16, 12))
        
        # 使用分层布局
        pos = nx.nx_agraph.graphviz_layout(global_dfg, prog='dot') if nx.nx_agraph.graphviz_layout else nx.spring_layout(global_dfg)
        
        # 准备不同类型的节点
        function_nodes = [n for n in global_dfg.nodes() if n not in global_vars and n not in static_vars and n not in heap_vars]
        global_nodes = [n for n in global_dfg.nodes() if n in global_vars]
        static_nodes = [n for n in global_dfg.nodes() if n in static_vars]
        heap_nodes = [n for n in global_dfg.nodes() if n in heap_vars]
        
        # 绘制不同类型的节点
        nx.draw_networkx_nodes(global_dfg, pos, nodelist=function_nodes, node_color='lightblue', node_size=1500, label='函数')
        nx.draw_networkx_nodes(global_dfg, pos, nodelist=global_nodes, node_color='red', node_size=1500, label='全局变量')
        nx.draw_networkx_nodes(global_dfg, pos, nodelist=static_nodes, node_color='purple', node_size=1500, label='静态变量')
        nx.draw_networkx_nodes(global_dfg, pos, nodelist=heap_nodes, node_color='orange', node_size=1500, label='堆变量')
        
        # 绘制边和标签
        edge_colors = []
        edge_labels = {}
        
        for u, v, data in global_dfg.edges(data=True):
            edge_type = data.get('type', 'unknown')
            via_function = data.get('via_function', '')
            
            if edge_type == 'assignment':
                edge_colors.append('blue')
                edge_labels[(u, v)] = f'赋值 (via {via_function})' if via_function else '赋值'
            elif edge_type == 'parameter':
                edge_colors.append('green')
                edge_labels[(u, v)] = '参数'
            elif edge_type == 'return':
                edge_colors.append('red')
                edge_labels[(u, v)] = f'返回值 (via {via_function})' if via_function else '返回值'
            elif edge_type == 'argument':
                edge_colors.append('purple')
                edge_labels[(u, v)] = '函数参数'
            else:
                edge_colors.append('black')
                edge_labels[(u, v)] = edge_type
        
        nx.draw_networkx_edges(global_dfg, pos, arrows=True, edge_color=edge_colors)
        nx.draw_networkx_edge_labels(global_dfg, pos, edge_labels=edge_labels, font_size=8)
        nx.draw_networkx_labels(global_dfg, pos, font_size=10)
        
        # 添加图例和标题
        plt.title("全局数据流图（函数间数据流）")
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        handles = [
            mpatches.Patch(color='lightgreen', label='输入参数'),
            mpatches.Patch(color='lightblue', label='输出结果'),
            mpatches.Patch(color='yellow', label='函数调用'),
            mpatches.Patch(color='red', label='全局变量'),
            mpatches.Patch(color='purple', label='静态变量'),
            mpatches.Patch(color='orange', label='堆变量'),
            mpatches.Patch(color='cyan', label='函数参数'),
            mpatches.Patch(color='gray', label='局部变量')
        ]
        plt.legend(handles=handles)
        plt.axis('off')
        
        # 保存图像
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file