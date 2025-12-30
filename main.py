#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
域名分析系统 - 主程序
整合数据爬取和模型分析两个步骤
"""
import sys
from datetime import datetime
from crawler_aliyun import run as run_aliyun
from crawler_tencent import run as run_tencent
from playwright.sync_api import sync_playwright
from llm_aliyun import process_domains_batch as process_aliyun_domains
from llm_tencent import process_domains_batch as process_tencent_domains
from domain_processor import get_csv_filename
import sys
sys.stdout.reconfigure(encoding='utf-8')

def step1_crawl_data(date_str: str = None):
    """
    第一步：数据爬取
    从阿里云域名交易平台爬取数据，保存到 日期_aliyun.csv
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    
    Returns:
        str: CSV文件路径
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    import os
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    csv_file = os.path.join(logs_dir, f"{date_str}_aliyun.csv")
    
    print("=" * 60)
    print("步骤1: 数据爬取")
    print("=" * 60)
    print(f"目标文件: {csv_file}")
    print("开始爬取数据...\n")
    
    try:
        with sync_playwright() as playwright:
            actual_file = run_aliyun(playwright, date_str)
        
        # 使用实际生成的文件名
        if actual_file != csv_file:
            print(f"[提示] 实际生成的文件: {actual_file}")
            csv_file = actual_file
        
        print(f"\n[完成] 数据爬取完成，数据已保存到: {csv_file}")
        return csv_file
    
    except Exception as e:
        print(f"\n[错误] 数据爬取失败: {e}")
        raise


def step2_analyze_domains(date_str: str = None):
    """
    第二步：调用大模型分析域名（阿里云）
    从 日期_aliyun.csv 读取数据，调用大模型分析，得到最终推荐的域名
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    print("\n" + "=" * 60)
    print("步骤2: 模型分析（阿里云）")
    print("=" * 60)
    print(f"分析日期: {date_str}\n")
    
    try:
        process_aliyun_domains(date_str)
        print(f"\n[完成] 阿里云模型分析完成")
    
    except Exception as e:
        print(f"\n[错误] 阿里云模型分析失败: {e}")
        raise


def step3_crawl_tencent_data(date_str: str = None):
    """
    第三步：数据爬取（腾讯云）
    从腾讯云域名交易平台爬取数据，保存到 日期_tencent.csv
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    
    Returns:
        str: CSV文件路径
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    import os
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    csv_file = os.path.join(logs_dir, f"{date_str}_tencent.csv")
    
    print("\n" + "=" * 60)
    print("步骤3: 数据爬取（腾讯云）")
    print("=" * 60)
    print(f"目标文件: {csv_file}")
    print("开始爬取数据...\n")
    
    try:
        with sync_playwright() as playwright:
            actual_file = run_tencent(playwright, date_str)
        
        # 使用实际生成的文件名
        if actual_file != csv_file:
            print(f"[提示] 实际生成的文件: {actual_file}")
            csv_file = actual_file
        
        # 验证文件是否存在
        import os
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"爬取完成后未找到文件: {csv_file}")
        
        print(f"\n[完成] 腾讯云数据爬取完成，数据已保存到: {csv_file}")
        return csv_file
    
    except Exception as e:
        print(f"\n[错误] 腾讯云数据爬取失败: {e}")
        raise


def step4_analyze_tencent_domains(date_str: str = None):
    """
    第四步：调用大模型分析域名（腾讯云）
    从 日期_tencent.csv 读取数据，调用大模型分析，得到最终推荐的域名
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    print("\n" + "=" * 60)
    print("步骤4: 模型分析（腾讯云）")
    print("=" * 60)
    print(f"分析日期: {date_str}\n")
    
    try:
        process_tencent_domains(date_str)
        print(f"\n[完成] 腾讯云模型分析完成")
    
    except Exception as e:
        print(f"\n[错误] 腾讯云模型分析失败: {e}")
        raise


def main(date_str: str = None):
    """
    主函数：执行完整流程
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print("域名分析系统 - 完整流程")
    print("=" * 60)
    print(f"处理日期: {date_str}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 第一步：阿里云数据爬取
        aliyun_csv_file = step1_crawl_data(date_str)
        
        # 验证文件是否存在
        import os
        if not os.path.exists(aliyun_csv_file):
            raise FileNotFoundError(f"爬取完成后未找到文件: {aliyun_csv_file}")
        
        # 第二步：阿里云模型分析
        step2_analyze_domains(date_str)
        
        # 第三步：腾讯云数据爬取
        tencent_csv_file = step3_crawl_tencent_data(date_str)
        
        # 验证文件是否存在
        if not os.path.exists(tencent_csv_file):
            raise FileNotFoundError(f"爬取完成后未找到文件: {tencent_csv_file}")
        
        # 第四步：腾讯云模型分析
        step4_analyze_tencent_domains(date_str)
        
        print("\n" + "=" * 60)
        print("完整流程执行成功！")
        print("=" * 60)
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        import os
        logs_dir = "logs"
        print(f"阿里云结果文件: {os.path.join(logs_dir, date_str + '_aliyun_result.csv')}")
        print(f"腾讯云结果文件: {os.path.join(logs_dir, date_str + '_tencent_result.csv')}")
        print("=" * 60)
    
    except KeyboardInterrupt:
        print("\n\n[中断] 用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 60)
        print("流程执行失败！")
        print("=" * 60)
        print(f"错误信息: {e}")
        import traceback
        print(f"\n完整错误堆栈:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='域名分析系统 - 完整流程')
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='处理日期，格式: YYYY-MM-DD (例如: 2025-12-25)，默认为当前日期'
    )
    
    args = parser.parse_args()
    
    # 执行主流程
    main(args.date)

