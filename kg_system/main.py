#!/usr/bin/env python3
"""
知识图谱构建系统 - CLI 主入口
融合 Hyper-Extract 的三层架构

用法:
    python main.py extract --input document.txt --template fire_emergency --output result.json
    python main.py visualize --input result.json --format mermaid --output graph.mmd
    python main.py feed --input base.json --new new_doc.txt --output updated.json
    python main.py merge --inputs file1.json file2.json --output merged.json
"""

import argparse
import json
import sys
from pathlib import Path

# 添加当前目录到路径
_script_dir = Path(__file__).parent
sys.path.insert(0, str(_script_dir))

from evolver import IncrementalEvolver, merge_knowledge_graphs
from llm_client import create_llm_client, load_from_env, LLMConfig, LLMProvider
import types as kg_types
from methods import get_extractor, list_methods
from visualizer import compile_knowledge_graph
from templates import get_template, list_templates


class KGBuilder:
    """知识图谱构建器"""
    
    def __init__(self, template_name: str = None, method: str = 'graphrag', llm_client=None):
        self.template = get_template(template_name) if template_name else None
        self.method = method
        self.llm_client = llm_client
        self.extractor = get_extractor(method, llm_client)
    
    def extract(self, text: str, graph_type: str = 'AutoGraph'):
        schema = self.template.to_dict().get('schema', {}) if self.template else None
        result = self.extractor.extract(text, schema)
        return self._build_graph(result, graph_type)
    
    def _build_graph(self, result, graph_type: str):
        from evolver import IncrementalEvolver
        if graph_type == 'AutoGraph':
            kg = kg_types.AutoGraph(id='kg_001', name='Knowledge Graph')
            for e in result.entities:
                kg.add_node(kg_types.GraphNode(id=e.get('id', e.get('name', '')), label=e.get('name', ''), type=e.get('type', 'concept')))
            for r in result.relations:
                kg.add_edge(kg_types.GraphEdge(id=r.get('id', f"edge_{len(kg.edges)}"), source=r.get('source', ''), target=r.get('target', ''), relation=r.get('relation', '')))
            return kg
        
        elif graph_type == 'AutoHypergraph':
            kg = kg_types.AutoHypergraph(id='kg_001', name='Hyper Knowledge Graph')
            for e in result.entities:
                kg.add_node(kg_types.GraphNode(id=e.get('id', e.get('name', '')), label=e.get('name', ''), type=e.get('type', 'concept')))
            for he in result.hyperedges:
                kg.add_hyperedge(kg_types.HyperEdge(id=he.get('id', f"he_{len(kg.hyperedges)}"), label=he.get('label', ''), entities=he.get('entities', []), relation_type=he.get('relation_type', 'hyperedge')))
            for r in result.relations:
                kg.edges.append(kg_types.GraphEdge(id=r.get('id', f"edge_{len(kg.edges)}"), source=r.get('source', ''), target=r.get('target', ''), relation=r.get('relation', '')))
            return kg
        
        elif graph_type == 'AutoTemporalGraph':
            kg = kg_types.AutoTemporalGraph(id='kg_001', name='Temporal Knowledge Graph')
            for e in result.entities:
                kg.add_node(kg_types.GraphNode(id=e.get('id', e.get('name', '')), label=e.get('name', ''), type=e.get('type', 'concept')))
            for t in result.temporal:
                kg.events.append(kg_types.EventNode(id=t.get('id', ''), label=t.get('event', ''), type='event', time=t.get('time')))
            return kg
        
        elif graph_type == 'AutoSpatioTemporalGraph':
            kg = kg_types.AutoSpatioTemporalGraph(id='kg_001', name='Spatio-Temporal Knowledge Graph')
            for st in result.temporal + result.spatial:
                if st.get('location') or st.get('time'):
                    node = kg_types.SpatioTemporalNode(id=st.get('id', st.get('event', '')), label=st.get('event', st.get('name', '')), type='spatio_temporal', time=st.get('time'), location=st.get('location'))
                    kg.add_spatio_temporal_node(node)
            for traj in result.trajectories:
                kg.add_trajectory(kg_types.Trajectory(id=traj.get('id', ''), entity_id=traj.get('entity_id', ''), points=traj.get('points', [])))
            for he in result.hyperedges:
                kg.add_hyperedge(kg_types.HyperEdge(id=he.get('id', f"he_{len(kg.hyperedges)}"), label=he.get('label', ''), entities=he.get('entities', [])))
            return kg
        
        else:
            raise ValueError(f"Unknown graph type: {graph_type}")


def cmd_extract(args):
    """提取命令"""
    llm_client = None
    if not args.no_llm:
        config = load_from_env()
        if config:
            llm_client = create_llm_client(config)
            print(f"LLM已配置: {config.provider.value} / {config.model}")
        else:
            print("未检测到LLM API Key，将使用占位符抽取")
    
    text = sys.stdin.read() if args.input == '-' else open(args.input, 'r', encoding='utf-8').read()
    
    builder = KGBuilder(template_name=args.template, method=args.method, llm_client=llm_client)
    kg = builder.extract(text, graph_type=args.graph_type)
    kg_data = kg.to_dict() if hasattr(kg, 'to_dict') else kg
    
    if args.output:
        kg_types.save_knowledge_graph(kg, args.output)
        print(f"已保存到: {args.output}")
    else:
        print(json.dumps(kg_data, ensure_ascii=False, indent=2))


def cmd_visualize(args):
    """可视化命令"""
    kg_data = json.load(open(args.input, 'r', encoding='utf-8'))
    code = compile_knowledge_graph(kg_data, format=args.format)
    
    if args.output:
        open(args.output, 'w', encoding='utf-8').write(code)
        print(f"已保存到: {args.output}")
    else:
        print(code)


def cmd_feed(args):
    """增量追加命令"""
    evolver = IncrementalEvolver()
    evolver.load(args.input)
    print(f"已加载基础图谱，实体数: {len(evolver.kg_data.get('nodes', []))}")
    
    text = sys.stdin.read() if args.new == '-' else open(args.new, 'r', encoding='utf-8').read()
    
    llm_client = None
    config = load_from_env()
    if config:
        llm_client = create_llm_client(config)
    
    builder = KGBuilder(template_name=args.template, method=args.method, llm_client=llm_client)
    new_kg = builder.extract(text, graph_type=args.graph_type)
    new_kg_data = new_kg.to_dict() if hasattr(new_kg, 'to_dict') else new_kg
    
    patch = evolver.feed(new_kg_data, source=args.new, conflict_strategy=args.strategy)
    
    print(f"增量追加完成:")
    print(f"  - 新增实体: {len(patch.added_entities)}")
    print(f"  - 新增关系: {len(patch.added_relations)}")
    print(f"  - 新增超边: {len(patch.added_hyperedges)}")
    
    evolver.save(args.output)
    print(f"已保存到: {args.output}")


def cmd_merge(args):
    """合并命令"""
    evolvers = []
    for path in args.inputs:
        ev = IncrementalEvolver()
        ev.load(path)
        evolvers.append(ev)
        print(f"已加载: {path}")
    
    result = evolvers[0]
    for ev in evolvers[1:]:
        result = result.merge(ev, strategy=args.strategy)
    
    print(f"\n合并完成 (策略: {args.strategy}):")
    stats = result.get_statistics()
    print(f"  - 实体数: {stats['entity_count']}")
    print(f"  - 关系数: {stats['relation_count']}")
    print(f"  - 超边数: {stats['hyperedge_count']}")
    
    result.save(args.output)
    print(f"已保存到: {args.output}")


def cmd_diff(args):
    """差异对比命令"""
    ev1 = IncrementalEvolver()
    ev1.load(args.kg1)
    
    ev2 = IncrementalEvolver()
    ev2.load(args.kg2)
    
    diff = ev1.diff(ev2)
    
    print("差异对比结果:")
    print(f"\n新增:")
    print(f"  - 实体: {len(diff.added.get('entities', []))}")
    print(f"  - 关系: {len(diff.added.get('relations', []))}")
    
    print(f"\n移除:")
    print(f"  - 实体: {len(diff.removed.get('entities', []))}")
    print(f"  - 关系: {len(diff.removed.get('relations', []))}")
    
    if args.output:
        json.dump(diff.to_dict(), open(args.output, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"\n差异已保存到: {args.output}")


def cmd_template(args):
    """模板命令"""
    if args.action == 'list':
        templates = list_templates()
        print("可用模板:")
        for t in templates:
            print(f"  - {t}")
    elif args.action == 'show':
        template = get_template(args.name)
        if template:
            print(template.to_prompt())
        else:
            print(f"模板 '{args.name}' 不存在")


def cmd_method(args):
    """方法命令"""
    if args.action == 'list':
        methods = list_methods()
        print("可用提取引擎:")
        for m in methods:
            print(f"  - {m}")


def cmd_stats(args):
    """统计命令"""
    evolver = IncrementalEvolver()
    evolver.load(args.input)
    stats = evolver.get_statistics()
    print("知识图谱统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description='知识图谱构建系统 v3.0')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # extract
    ep = subparsers.add_parser('extract', help='从文本提取知识图谱')
    ep.add_argument('--input', '-i', required=True, help='输入文件')
    ep.add_argument('--output', '-o', help='输出文件')
    ep.add_argument('--template', '-t', help='模板名称')
    ep.add_argument('--method', '-m', default='hypergraphrag', help='提取引擎')
    ep.add_argument('--graph-type', '-g', default='AutoSpatioTemporalGraph', choices=['AutoGraph', 'AutoHypergraph', 'AutoTemporalGraph', 'AutoSpatialGraph', 'AutoSpatioTemporalGraph'])
    ep.add_argument('--no-llm', action='store_true')
    ep.set_defaults(func=cmd_extract)
    
    # visualize
    vp = subparsers.add_parser('visualize', help='可视化知识图谱')
    vp.add_argument('--input', '-i', required=True)
    vp.add_argument('--output', '-o')
    vp.add_argument('--format', '-f', default='mermaid', choices=['mermaid', 'd3', 'geojson'])
    vp.set_defaults(func=cmd_visualize)
    
    # feed
    fp = subparsers.add_parser('feed', help='增量追加')
    fp.add_argument('--input', '-i', required=True)
    fp.add_argument('--new', '-n', required=True)
    fp.add_argument('--output', '-o', required=True)
    fp.add_argument('--template', '-t')
    fp.add_argument('--method', '-m', default='hypergraphrag')
    fp.add_argument('--graph-type', '-g', default='AutoSpatioTemporalGraph')
    fp.add_argument('--strategy', '-s', default='keep_existing', choices=['keep_existing', 'overwrite', 'merge'])
    fp.set_defaults(func=cmd_feed)
    
    # merge
    mp = subparsers.add_parser('merge', help='合并多个图谱')
    mp.add_argument('--inputs', '-i', nargs='+', required=True)
    mp.add_argument('--output', '-o', required=True)
    mp.add_argument('--strategy', '-s', default='union', choices=['union', 'intersection'])
    mp.set_defaults(func=cmd_merge)
    
    # diff
    dp = subparsers.add_parser('diff', help='对比差异')
    dp.add_argument('--kg1', required=True)
    dp.add_argument('--kg2', required=True)
    dp.add_argument('--output', '-o')
    dp.set_defaults(func=cmd_diff)
    
    # template
    tp = subparsers.add_parser('template', help='模板管理')
    tp.add_argument('action', choices=['list', 'show'])
    tp.add_argument('--name', '-n')
    tp.set_defaults(func=cmd_template)
    
    # method
    mp2 = subparsers.add_parser('method', help='提取引擎管理')
    mp2.add_argument('action', choices=['list'])
    mp2.set_defaults(func=cmd_method)
    
    # stats
    sp = subparsers.add_parser('stats', help='查看统计')
    sp.add_argument('--input', '-i', required=True)
    sp.set_defaults(func=cmd_stats)
    
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
