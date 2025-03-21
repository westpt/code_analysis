#!/usr/bin/env python3
import os
import sys
import json
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analyzer.c_code_analyzer import CCodeAnalyzer

def main():
    parser = argparse.ArgumentParser(description='Analyze C code for data flow and business logic')
    parser.add_argument('path', help='Path to the C source file, directory containing C files, or JSON configuration file')
    parser.add_argument('--output-dir', '-o', default='output', help='Directory to save output files')
    parser.add_argument('--json', '-j', action='store_true', help='Export analysis results to JSON')
    args = parser.parse_args()
    
    # 检查路径是否存在
    if not os.path.exists(args.path):
        print(f"Error: Path {args.path} does not exist")
        return 1
    
    # 创建输出目录
    # 确保输出目录是一个有效的目录路径，而不是文件路径
    output_dir = args.output_dir
    if output_dir.endswith('.json'):
        # 如果用户指定了JSON文件作为输出，使用其父目录作为输出目录
        output_dir = os.path.dirname(output_dir)
        if not output_dir:  # 如果目录为空，使用当前目录
            output_dir = '.'
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # 检查是否是配置文件
        source_files = []
        include_paths = []
        base_dir = os.path.dirname(args.path)
        
        if args.path.endswith('.json'):
            try:
                with open(args.path, 'r') as f:
                    config = json.load(f)
                
                # 从配置文件中获取源文件和包含路径
                if 'source_files' in config:
                    source_files = [os.path.join(base_dir, src) for src in config['source_files']]
                if 'include_paths' in config:
                    include_paths = [os.path.join(base_dir, inc) for inc in config['include_paths']]
                
                print(f"Loaded configuration from {args.path}")
                print(f"Source files: {source_files}")
                print(f"Include paths: {include_paths}")
                
                if not source_files:
                    print("Error: No source files specified in configuration")
                    return 1
            except json.JSONDecodeError:
                print(f"Error: {args.path} is not a valid JSON file")
                return 1
        else:
            # 直接使用指定的路径
            source_files = [args.path]
        
        # 执行分析
        print(f"Analyzing source files...")
        analyzer = CCodeAnalyzer(source_files[0], include_paths).analyze()
        
        # 生成可视化结果
        cfg_output = os.path.join(output_dir, 'control_flow_graph.png')
        dfg_output = os.path.join(output_dir, 'data_flow_graph.png')
        logic_output = os.path.join(output_dir, 'business_logic.png')
        
        analyzer.visualize_cfg(cfg_output)
        analyzer.visualize_dfg(dfg_output)
        analyzer.visualize_business_logic(logic_output)
        
        # 如果需要导出JSON
        if args.json:
            json_output = os.path.join(output_dir, 'analysis_result.json')
            analyzer.export_to_json(json_output)
            print(f"- Analysis results (JSON): {json_output}")
        
        print(f"Analysis complete. Results saved to {output_dir}/")
        print(f"- Control Flow Graph: {cfg_output}")
        print(f"- Data Flow Graph: {dfg_output}")
        print(f"- Business Logic Diagram: {logic_output}")
        
        # 输出一些统计信息
        print("\nStatistics:")
        print(f"- Total variables: {len(analyzer.variables)}")
        print(f"- Global variables: {len(analyzer.global_vars)}")
        print(f"- Static variables: {len(analyzer.static_vars)}")
        print(f"- Heap variables: {len(analyzer.heap_vars)}")
        print(f"- Function calls: {len(analyzer.function_calls)}")
        print(f"- Analyzed files: {len(analyzer.files)}")
        
        return 0
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())