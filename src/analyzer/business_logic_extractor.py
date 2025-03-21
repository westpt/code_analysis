import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

class BusinessLogicExtractor:
    def __init__(self, analyzer):
        """初始化业务逻辑提取器"""
        self.analyzer = analyzer
        self.business_modules = defaultdict(list)
        self.module_dependencies = nx.DiGraph()
    
    def extract_modules(self):
        """从数据流图中提取业务模块"""
        # 基于函数调用关系聚类
        G = self.analyzer.cfg.copy()
        
        # 使用社区检测算法识别模块
        try:
            from community import community_louvain
            partition = community_louvain.best_partition(G)
            
            # 将节点按模块分组
            for node, module_id in partition.items():
                module_name = f"Module_{module_id}"
                self.business_modules[module_name].append(node)
        except ImportError:
            # 如果没有community库，使用简单的连通分量
            for i, component in enumerate(nx.weakly_connected_components(G)):
                module_name = f"Module_{i}"
                self.business_modules[module_name].extend(component)
        
        # 分析模块间依赖关系
        for src_module, src_nodes in self.business_modules.items():
            for dst_module, dst_nodes in self.business_modules.items():
                if src_module != dst_module:
                    # 检查模块间是否存在函数调用或数据流
                    for src_node in src_nodes:
                        for dst_node in dst_nodes:
                            if (self.analyzer.cfg.has_edge(src_node, dst_node) or
                                self.analyzer.dfg.has_edge(src_node, dst_node)):
                                self.module_dependencies.add_edge(src_module, dst_module)
                                break
        
        return self.business_modules, self.module_dependencies

    def analyze_module_complexity(self):
        """分析每个模块的复杂度"""
        complexity_metrics = {}
        
        for module_name, nodes in self.business_modules.items():
            metrics = {
                'node_count': len(nodes),
                'internal_edges': 0,
                'external_edges': 0,
                'global_vars': 0,
                'heap_vars': 0
            }
            
            # 计算内部边和外部边
            for node in nodes:
                # 检查与该节点相关的全局变量和堆变量
                if node in self.analyzer.global_vars:
                    metrics['global_vars'] += 1
                if node in self.analyzer.heap_vars:
                    metrics['heap_vars'] += 1
                
                # 统计边的数量
                for successor in self.analyzer.cfg.successors(node):
                    if successor in nodes:
                        metrics['internal_edges'] += 1
                    else:
                        metrics['external_edges'] += 1
            
            complexity_metrics[module_name] = metrics
        
        return complexity_metrics

    def generate_module_documentation(self):
        """生成模块文档"""
        documentation = {}
        
        for module_name, nodes in self.business_modules.items():
            module_doc = {
                'functions': [],
                'variables': [],
                'dependencies': [],
                'description': f"Business module: {module_name}"
            }
            
            # 收集函数信息
            for node in nodes:
                if node in self.analyzer.function_calls:
                    module_doc['functions'].append({
                        'name': node,
                        'calls': list(self.analyzer.cfg.successors(node))
                    })
                
                # 收集变量信息
                if node in self.analyzer.variables:
                    module_doc['variables'].append({
                        'name': node,
                        'type': self.analyzer.variables[node]['type'],
                        'storage': self.analyzer.variables[node]['storage']
                    })
            
            # 收集依赖信息
            module_doc['dependencies'] = list(self.module_dependencies.successors(module_name))
            
            documentation[module_name] = module_doc
        
        return documentation

    def visualize_modules(self, output_file='business_modules.png'):
        """可视化业务模块及其依赖关系"""
        plt.figure(figsize=(15, 10))
        pos = nx.spring_layout(self.module_dependencies)
        
        # 绘制节点
        node_sizes = [len(self.business_modules[node]) * 500 for node in self.module_dependencies.nodes()]
        nx.draw_networkx_nodes(self.module_dependencies, pos, 
                             node_color='lightblue',
                             node_size=node_sizes)
        
        # 绘制边
        nx.draw_networkx_edges(self.module_dependencies, pos, 
                             edge_color='gray',
                             arrows=True,
                             arrowsize=20)
        
        # 添加标签
        labels = {node: f"{node}\n({len(self.business_modules[node])} functions)"
                 for node in self.module_dependencies.nodes()}
        nx.draw_networkx_labels(self.module_dependencies, pos, labels,
                              font_size=8)
        
        plt.title("Business Module Dependencies")
        plt.axis('off')
        plt.savefig(output_file, bbox_inches='tight')
        plt.close()

    def export_module_graph(self, output_file='module_graph.dot'):
        """导出模块图到DOT格式"""
        try:
            import pydot
            graph = pydot.Dot(graph_type='digraph')
            
            # 添加节点
            for module_name, nodes in self.business_modules.items():
                node = pydot.Node(module_name, 
                                label=f"{module_name}\n({len(nodes)} functions)",
                                shape='box',
                                style='filled',
                                fillcolor='lightblue')
                graph.add_node(node)
            
            # 添加边
            for src, dst in self.module_dependencies.edges():
                edge = pydot.Edge(src, dst)
                graph.add_edge(edge)
            
            # 保存图
            graph.write_raw(output_file)
            
        except ImportError:
            print("Warning: pydot not installed. Cannot export module graph.")