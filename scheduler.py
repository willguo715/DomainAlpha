#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
域名分析系统 - 定时任务调度器
每天9点自动执行域名分析任务
"""
import schedule
import time
import subprocess
import sys
from datetime import datetime
import os
import traceback

def run_domain_analysis():
    """执行域名分析任务"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行域名分析任务...")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "main.py")
    
    # 创建日志目录
    log_dir = os.path.join(script_dir, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"domain_analysis_{timestamp}.log")
    
    # 执行主程序
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"========================================\n")
            f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"========================================\n\n")
            
            result = subprocess.run(
                [sys.executable, main_script],
                cwd=script_dir,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            
            f.write(f"\n========================================\n")
            f.write(f"执行结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            if result.returncode == 0:
                f.write(f"[成功] 任务执行完成，退出代码: {result.returncode}\n")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 任务执行成功")
            else:
                f.write(f"[错误] 任务执行失败，退出代码: {result.returncode}\n")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 任务执行失败，退出代码: {result.returncode}")
                print(f"详细日志请查看: {log_file}")
            
            f.write(f"========================================\n")
        
    except Exception as e:
        error_msg = f"执行任务时发生异常: {e}\n{traceback.format_exc()}"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ {error_msg}")
        
        # 记录错误到日志
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[异常] {error_msg}\n")
        except:
            pass

# 每天9点执行
schedule.every().day.at("09:00").do(run_domain_analysis)

print("=" * 60)
print("域名分析系统 - 定时任务调度器")
print("=" * 60)
print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"执行计划: 每天 09:00 自动执行")
print(f"下次执行: {schedule.next_run().strftime('%Y-%m-%d %H:%M:%S') if schedule.next_run() else '未设置'}")
print("=" * 60)

# 启动时立即执行一次
print("\n[信息] 启动时立即执行一次任务...")
print("=" * 60)
run_domain_analysis()
print("=" * 60)
print(f"[信息] 初始执行完成，等待下次定时执行（每天 09:00）")
print("按 Ctrl+C 退出调度器")
print("=" * 60)

# 保持程序运行（优化版：动态调整检查间隔）
try:
    while True:
        schedule.run_pending()
        
        # 计算距离下次执行的时间
        next_run = schedule.next_run()
        if next_run:
            wait_seconds = (next_run - datetime.now()).total_seconds()
            
            # 如果距离下次执行超过1小时，每小时检查一次
            if wait_seconds > 3600:
                sleep_time = 3600  # 每小时检查一次
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 距离下次执行（{next_run_str}）还有 {int(wait_seconds/3600)} 小时，进入节能模式（每小时检查一次）")
            # 如果距离下次执行超过10分钟，每10分钟检查一次
            elif wait_seconds > 600:
                sleep_time = 600   # 每10分钟检查一次
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 距离下次执行（{next_run_str}）还有 {int(wait_seconds/60)} 分钟，每10分钟检查一次")
            # 否则每分钟检查一次
            else:
                sleep_time = 60    # 每分钟检查一次
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 距离下次执行（{next_run_str}）还有 {int(wait_seconds)} 秒，每分钟检查一次")
        else:
            sleep_time = 60
        
        time.sleep(sleep_time)
            
except KeyboardInterrupt:
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 调度器已停止")
    sys.exit(0)
except Exception as e:
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 调度器发生异常: {e}")
    print(traceback.format_exc())
    sys.exit(1)

