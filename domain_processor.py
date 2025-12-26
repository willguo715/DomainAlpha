import csv
import random
import os
from datetime import datetime
from typing import List, Tuple, Optional, Generator


# ==========================================
# 配置读取函数
# ==========================================
def load_config_key(file_path="config.txt", target_key="api_key", default=None):
    """
    从 a=b 格式的文件中提取特定的 value
    
    Args:
        file_path: 配置文件路径
        target_key: 要查找的键名
        default: 如果找不到键时的默认值
    
    Returns:
        配置值，如果找不到则返回 default
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)  # 只分割第一个等号
                    if key.strip() == target_key:
                        return value.strip()
        # 如果找不到，返回默认值
        if default is not None:
            return default
        raise ValueError(f"在文件中未找到键名: {target_key}")
    except FileNotFoundError:
        print(f"❌ 配置文件 {file_path} 不存在")
        return default
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")
        return default


# ==========================================
# 数据加载和分批处理函数
# ==========================================
def load_and_batch_domains(
    csv_file_path: str,
    batch_size: Optional[int] = None,
    shuffle: Optional[bool] = None,
    random_seed: Optional[int] = None
) -> Generator[List[Tuple[str, str]], None, None]:
    """
    读取CSV文件，提取域名和价格，打乱后分批返回
    
    Args:
        csv_file_path: CSV文件路径（如 "2025-12-25_aliyun.csv"）
        batch_size: 每批返回的数量（如果为None，从配置文件读取）
        shuffle: 是否打乱顺序（None则从配置文件读取）
        random_seed: 随机种子（None则每次不同，或从配置文件读取）
    
    Yields:
        list: 每批数据，格式为 [(域名, 价格), ...]
    
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: CSV格式错误或缺少必需列
    """
    # 1. 读取配置
    if batch_size is None:
        batch_size = int(load_config_key("config.txt", "batch_size", "400"))
    
    if shuffle is None:
        shuffle_str = load_config_key("config.txt", "shuffle", "True")
        shuffle = shuffle_str.lower() in ('true', '1', 'yes', 'on')
    
    if random_seed is None:
        seed_str = load_config_key("config.txt", "random_seed", "None")
        if seed_str and seed_str.lower() != "none":
            try:
                random_seed = int(seed_str)
            except ValueError:
                random_seed = None
    
    # 2. 设置随机种子
    if random_seed is not None:
        random.seed(random_seed)
    
    # 3. 读取CSV文件
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV文件不存在: {csv_file_path}")
    
    domains_data = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # 验证必需的列是否存在
            if '域名' not in reader.fieldnames or '最低价格' not in reader.fieldnames:
                raise ValueError(f"CSV文件缺少必需的列。需要的列: 域名, 最低价格")
            
            # 读取数据
            for row_num, row in enumerate(reader, start=2):  # 从第2行开始（第1行是表头）
                domain = row.get('域名', '').strip()
                price = row.get('最低价格', '').strip()
                
                # 数据验证和清洗
                if not domain:
                    continue  # 跳过空域名
                
                # 价格清洗：去除¥符号，保留数字
                price_clean = price.replace('¥', '').replace(',', '').strip()
                if not price_clean or not price_clean.isdigit():
                    continue  # 跳过无效价格
                
                domains_data.append((domain, price_clean))
    
    except Exception as e:
        raise ValueError(f"读取CSV文件时出错: {e}")
    
    if not domains_data:
        raise ValueError("CSV文件中没有有效数据")
    
    # 4. 打乱数据
    if shuffle:
        random.shuffle(domains_data)
    
    # 5. 分批返回
    total_count = len(domains_data)
    for i in range(0, total_count, batch_size):
        batch = domains_data[i:i + batch_size]
        yield batch


# ==========================================
# 获取批次信息函数
# ==========================================
def get_batch_info(csv_file_path: str, batch_size: Optional[int] = None) -> dict:
    """
    获取数据统计信息
    
    Args:
        csv_file_path: CSV文件路径
        batch_size: 每批大小（None则从配置文件读取）
    
    Returns:
        dict: {
            'total_count': 总域名数,
            'batch_size': 每批大小,
            'total_batches': 总批次数
        }
    """
    if batch_size is None:
        batch_size = int(load_config_key("config.txt", "batch_size", "400"))
    
    # 快速统计总数（不加载全部数据）
    total_count = 0
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                domain = row.get('域名', '').strip()
                price = row.get('最低价格', '').strip()
                if domain and price:
                    price_clean = price.replace('¥', '').replace(',', '').strip()
                    if price_clean and price_clean.isdigit():
                        total_count += 1
    except Exception as e:
        return {
            'error': f"读取文件失败: {e}",
            'total_count': 0,
            'batch_size': batch_size,
            'total_batches': 0
        }
    
    total_batches = (total_count + batch_size - 1) // batch_size  # 向上取整
    
    return {
        'total_count': total_count,
        'batch_size': batch_size,
        'total_batches': total_batches
    }


# ==========================================
# 格式化批次数据为文本
# ==========================================
def format_batch_for_model(batch: List[Tuple[str, str]], batch_number: int = None) -> str:
    """
    将批次数据格式化为模型可理解的文本格式
    
    Args:
        batch: 批次数据，格式为 [(域名, 价格), ...]
        batch_number: 批次编号（可选）
    
    Returns:
        str: 格式化后的文本
    """
    lines = []
    if batch_number:
        lines.append(f"批次 {batch_number} 的域名列表：\n")
    else:
        lines.append("域名列表：\n")
    
    for idx, (domain, price) in enumerate(batch, 1):
        lines.append(f"{idx}. {domain} - ¥{price}")
    
    return "\n".join(lines)


# ==========================================
# 根据日期自动生成CSV文件名
# ==========================================
def get_csv_filename(date_str: Optional[str] = None) -> str:
    """
    根据日期生成CSV文件名
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    
    Returns:
        str: CSV文件名，格式为 "日期_aliyun.csv"
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    return f"{date_str}_aliyun.csv"


# ==========================================
# 测试和示例
# ==========================================
if __name__ == "__main__":
    # 示例1: 获取统计信息
    print("=" * 50)
    print("示例1: 获取统计信息")
    print("=" * 50)
    
    csv_file = get_csv_filename("2025-12-25")
    if os.path.exists(csv_file):
        info = get_batch_info(csv_file)
        print(f"文件: {csv_file}")
        print(f"总域名数: {info['total_count']}")
        print(f"每批大小: {info['batch_size']}")
        print(f"总批次数: {info['total_batches']}")
        print()
    
    # 示例2: 分批处理
    print("=" * 50)
    print("示例2: 分批处理（显示前3批）")
    print("=" * 50)
    
    if os.path.exists(csv_file):
        batch_count = 0
        for batch in load_and_batch_domains(csv_file):
            batch_count += 1
            print(f"\n第 {batch_count} 批，共 {len(batch)} 个域名")
            print("前5个域名示例：")
            for domain, price in batch[:5]:
                print(f"  {domain}: Y{price}")  # 使用Y代替¥避免编码问题
            
            if batch_count >= 3:
                print("\n... (仅显示前3批)")
                break
    
    # 示例3: 格式化批次数据
    print("\n" + "=" * 50)
    print("示例3: 格式化批次数据")
    print("=" * 50)
    
    if os.path.exists(csv_file):
        for batch_num, batch in enumerate(load_and_batch_domains(csv_file), 1):
            formatted = format_batch_for_model(batch, batch_num)
            print(f"\n批次 {batch_num} 格式化结果（前10行）：")
            lines = formatted.split('\n')
            print('\n'.join(lines[:11]))  # 显示前10行
            if batch_num >= 1:
                break

