import json
import os
from pathlib import Path

def merge_json_files():
    """合并所有JSON文件到papers.json，然后删除其他JSON文件"""
    
    # 获取当前目录
    current_dir = Path('.')
    
    # 目标文件
    target_file = 'papers.json'
    
    # 收集所有论文条目
    all_papers = []
    
    # 如果papers.json存在，先读取其中的内容
    if os.path.exists(target_file):
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                existing_papers = json.load(f)
                if isinstance(existing_papers, list):
                    all_papers.extend(existing_papers)
                    print(f"从 {target_file} 读取了 {len(existing_papers)} 篇论文")
                else:
                    print(f"警告: {target_file} 不是数组格式，将跳过")
        except Exception as e:
            print(f"读取 {target_file} 时出错: {e}")
    
    # 查找所有JSON文件（除了papers.json）
    json_files = [f for f in current_dir.glob('*.json') if f.name != target_file]
    
    if not json_files:
        print("没有找到需要合并的JSON文件")
        return
    
    print(f"\n找到 {len(json_files)} 个需要合并的JSON文件:")
    for json_file in json_files:
        print(f"  - {json_file.name}")
    
    # 读取并合并所有JSON文件
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                papers = json.load(f)
                if isinstance(papers, list):
                    all_papers.extend(papers)
                    print(f"从 {json_file.name} 添加了 {len(papers)} 篇论文")
                else:
                    print(f"警告: {json_file.name} 不是数组格式，将跳过")
        except Exception as e:
            print(f"读取 {json_file.name} 时出错: {e}")
            continue
    
    # 按年份从高到低排序（降序）
    def get_year(paper):
        """获取论文年份，用于排序"""
        year = paper.get('year')
        # 如果年份不存在或为None，返回0（排在最后）
        return year if year is not None else 0
    
    all_papers.sort(key=get_year, reverse=True)
    print(f"\n已按年份从高到低排序")
    
    # 保存合并后的结果到papers.json
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(all_papers, f, ensure_ascii=False, indent=2)
        print(f"成功将 {len(all_papers)} 篇论文保存到 {target_file}")
    except Exception as e:
        print(f"保存 {target_file} 时出错: {e}")
        return
    
    # 删除除papers.json之外的所有JSON文件
    deleted_count = 0
    for json_file in json_files:
        try:
            os.remove(json_file)
            print(f"已删除: {json_file.name}")
            deleted_count += 1
        except Exception as e:
            print(f"删除 {json_file.name} 时出错: {e}")
    
    print(f"\n完成! 共删除了 {deleted_count} 个JSON文件")
    print(f"最终 {target_file} 包含 {len(all_papers)} 篇论文")

if __name__ == "__main__":
    merge_json_files()
