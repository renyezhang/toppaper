import json
import sys
import os
from typing import List, Dict

def delete_papers_by_source(source: str, year: int = None):
    """
    从 papers.json 中删除指定 source 和年份的论文
    
    Args:
        source: 论文来源（如 'CVPR', 'ICCV', 'ICLR', 'ICML', 'NeurIPS', 'ECCV'）
        year: 年份（可选），如果不提供则删除该 source 的所有年份
    """
    target_file = 'papers.json'
    
    # 检查文件是否存在
    if not os.path.exists(target_file):
        print(f"错误: {target_file} 文件不存在")
        return
    
    # 读取 papers.json
    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            all_papers = json.load(f)
        
        if not isinstance(all_papers, list):
            print(f"错误: {target_file} 格式不正确，应该是数组格式")
            return
        
        print(f"当前 papers.json 中有 {len(all_papers)} 篇论文")
        
    except Exception as e:
        print(f"读取 {target_file} 时出错: {e}")
        return
    
    # 备份原始数据
    original_count = len(all_papers)
    
    # 过滤出要保留的论文（即删除符合条件的论文）
    if year is not None:
        # 删除指定 source 和 year 的论文
        papers_to_keep = [
            paper for paper in all_papers
            if not (paper.get('source') == source and paper.get('year') == year)
        ]
        deleted_count = original_count - len(papers_to_keep)
        print(f"\n将删除 source='{source}' 且 year={year} 的论文")
    else:
        # 删除指定 source 的所有年份论文
        papers_to_keep = [
            paper for paper in all_papers
            if paper.get('source') != source
        ]
        deleted_count = original_count - len(papers_to_keep)
        print(f"\n将删除 source='{source}' 的所有年份的论文")
    
    # 检查是否有论文被删除
    if deleted_count == 0:
        if year is not None:
            print(f"未找到 source='{source}' 且 year={year} 的论文")
        else:
            print(f"未找到 source='{source}' 的论文")
        return
    
    # 确认删除
    print(f"找到 {deleted_count} 篇符合条件的论文")
    confirm = input(f"确认删除这 {deleted_count} 篇论文吗？(y/n): ").strip().lower()
    
    if confirm != 'y' and confirm != 'yes':
        print("取消删除操作")
        return
    
    # 保存更新后的论文列表
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(papers_to_keep, f, ensure_ascii=False, indent=2)
        
        print(f"\n成功删除 {deleted_count} 篇论文")
        print(f"papers.json 中剩余 {len(papers_to_keep)} 篇论文")
        
    except Exception as e:
        print(f"保存 {target_file} 时出错: {e}")


def main():
    """主函数"""
    source = None
    year = None
    
    # 从命令行参数获取
    if len(sys.argv) >= 2:
        source = sys.argv[1]
        if len(sys.argv) >= 3:
            try:
                year = int(sys.argv[2])
            except ValueError:
                print(f"错误: '{sys.argv[2]}' 不是有效的年份（应该是整数）")
                return
    else:
        # 交互式输入
        print("=" * 50)
        print("删除 papers.json 中的论文")
        print("=" * 50)
        source = input("\n请输入 source 名称（如 CVPR, ICCV, ICLR, ICML, NeurIPS, ECCV）: ").strip()
        
        if not source:
            print("错误: source 名称不能为空")
            return
        
        year_input = input("请输入年份（可选，直接回车则删除该 source 的所有年份）: ").strip()
        if year_input:
            try:
                year = int(year_input)
            except ValueError:
                print(f"错误: '{year_input}' 不是有效的年份（应该是整数）")
                return
    
    if not source:
        print("错误: source 名称不能为空")
        return
    
    # 执行删除
    delete_papers_by_source(source, year)


if __name__ == "__main__":
    main()
