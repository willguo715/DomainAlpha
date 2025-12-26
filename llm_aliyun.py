import httpx
import csv
import re
import traceback
from openai import OpenAI
from datetime import datetime
from domain_processor import load_and_batch_domains, format_batch_for_model, get_csv_filename, get_batch_info
from email_sender import send_email_simple

# ==========================================
# 1. 提示词加载函数 - 从文件读取
# ==========================================
def load_prompts(prompt_file="prompt.txt"):
    """
    从文件中加载系统提示词和用户提示词模板
    
    Args:
        prompt_file: 提示词文件路径
    
    Returns:
        tuple: (system_prompt, user_prompt_template)
    """
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 分割系统提示词和用户提示词
        system_prompt = ""
        user_prompt_template = ""
        
        if "[SYSTEM_PROMPT]" in content:
            parts = content.split("[SYSTEM_PROMPT]", 1)
            if len(parts) > 1:
                remaining = parts[1]
                if "[USER_PROMPT_TEMPLATE]" in remaining:
                    system_prompt = remaining.split("[USER_PROMPT_TEMPLATE]", 1)[0].strip()
                    user_prompt_template = remaining.split("[USER_PROMPT_TEMPLATE]", 1)[1].strip()
                else:
                    system_prompt = remaining.strip()
                    user_prompt_template = "请对以下内容进行分析：\n\n{text}"
        else:
            # 如果没有标记，使用默认值
            system_prompt = "你是一个专业的助手。"
            user_prompt_template = "请对以下内容进行分析：\n\n{text}"
        
        return system_prompt, user_prompt_template
    
    except FileNotFoundError:
        print(f"[警告] 提示词文件 {prompt_file} 不存在，使用默认提示词")
        return "你是一个专业的助手。", "请对以下内容进行分析：\n\n{text}"
    except Exception as e:
        print(f"[错误] 读取提示词文件失败: {e}，使用默认提示词")
        return "你是一个专业的助手。", "请对以下内容进行分析：\n\n{text}"

# ==========================================
# 2. 配置提取 - 处理 a=b 格式
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
                    key, value = line.split("=", 1) # 只分割第一个等号
                    if key.strip() == target_key:
                        return value.strip()
        # 如果找不到，返回默认值
        if default is not None:
            return default
        raise ValueError(f"在文件中未找到键名: {target_key}")
    except FileNotFoundError:
        print(f"[错误] 配置文件 {file_path} 不存在")
        return default
    except Exception as e:
        print(f"[错误] 读取配置失败: {e}")
        return default

# ==========================================
# 3. 超长文本处理函数
# ==========================================
def call_deepseek_v3_long_task(long_text):
    # 1. 从配置文件读取所有配置项
    api_key = load_config_key("config.txt", "api_key")
    if not api_key:
        return "[错误] 未找到 API 密钥配置", None
    
    base_url = load_config_key("config.txt", "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = load_config_key("config.txt", "model", "deepseek-v3")
    timeout = float(load_config_key("config.txt", "timeout", "600"))
    temperature = float(load_config_key("config.txt", "temperature", "0.3"))
    max_tokens = int(load_config_key("config.txt", "max_tokens", "8192"))

    # 2. 针对长文本设置超长超时时间
    # 长文本推理时间较长，必须增加 timeout，否则会触发 ReadTimeout 错误
    http_client = httpx.Client(
        timeout=httpx.Timeout(timeout, connect=5.0)
    )

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=http_client
    )

    try:
        # 3. 加载提示词
        system_prompt, user_prompt_template = load_prompts()
        
        # 4. 发起请求
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_template.format(text=long_text)}
            ],
            temperature=temperature,   # 从配置文件读取
            max_tokens=max_tokens,     # 从配置文件读取
            stream=False               # 明确不使用流式
        )

        # 检查是否完整
        if response.choices[0].finish_reason == "length":
            print("[警告] 提示：模型回复因达到长度限制而截断。")

        # 提取token使用信息
        usage_info = None
        if hasattr(response, 'usage') and response.usage:
            usage_info = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }

        return response.choices[0].message.content, usage_info

    except Exception as e:
        return f"[错误] 调用模型失败: {str(e)}", None


# ==========================================
# 5. 解析模型返回的表格数据
# ==========================================
def parse_model_response(response_text: str) -> list:
    """
    从模型返回的Markdown表格中解析推荐数据
    
    Args:
        response_text: 模型返回的文本（包含Markdown表格）
    
    Returns:
        list: 解析后的数据列表，每个元素为字典
        [{
            '序号': '1',
            '域名': 'example.com',
            '当前价格': '¥500',
            '预计出手价格': '¥5000',
            '推荐理由': '理由...',
            '投资等级': 'S (极力推荐)'
        }, ...]
    """
    results = []
    
    # 尝试匹配Markdown表格
    # 匹配表格行：| 序号 | 域名 | ... |
    table_pattern = r'\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|'
    lines = response_text.split('\n')
    
    in_table = False
    header_found = False
    
    for line in lines:
        line = line.strip()
        
        # 跳过表头分隔行（如 | :--- | :--- |）
        # 注意：在字符类中，- 必须放在开头或结尾，或转义，否则会被解释为范围操作符
        if re.match(r'^\|[\s:\-]+\|', line):
            header_found = True
            continue
        
        # 匹配表格数据行
        if '|' in line and header_found:
            parts = [p.strip() for p in line.split('|')]
            # 过滤空字符串（因为split会在开头和结尾产生空字符串）
            parts = [p for p in parts if p]
            
            if len(parts) >= 6:
                try:
                    result = {
                        '序号': parts[0],
                        '域名': parts[1],
                        '当前价格': parts[2],
                        '预计出手价格': parts[3],
                        '推荐理由': parts[4],
                        '投资等级': parts[5] if len(parts) > 5 else ''
                    }
                    results.append(result)
                except Exception as e:
                    continue
    
    return results


# ==========================================
# 6. 保存结果到CSV文件
# ==========================================
def save_results_to_csv(results: list, output_file: str):
    """
    将推荐结果保存到CSV文件
    
    Args:
        results: 结果列表，每个元素为字典
        output_file: 输出文件路径
    """
    if not results:
        print("[警告] 没有结果可保存")
        return
    
    try:
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['序号', '域名', '当前价格', '预计出手价格', '推荐理由', '投资等级']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"[成功] 结果已保存到: {output_file}")
    except Exception as e:
        print(f"[错误] 保存结果失败: {e}")


# ==========================================
# 7. 格式化汇总数据
# ==========================================
def format_summary_for_final_selection(all_recommendations: list) -> str:
    """
    将汇总的推荐数据格式化为最终筛选的输入文本
    
    Args:
        all_recommendations: 所有批次的推荐结果列表
    
    Returns:
        str: 格式化后的文本
    """
    lines = ["已筛选的域名推荐列表（共{}个）：\n".format(len(all_recommendations))]
    lines.append("| 序号 | 域名 | 当前价格 | 预计出手价格 | 推荐理由 | 投资等级 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for idx, rec in enumerate(all_recommendations, 1):
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            rec.get('序号', idx),
            rec.get('域名', ''),
            rec.get('当前价格', ''),
            rec.get('预计出手价格', ''),
            rec.get('推荐理由', ''),
            rec.get('投资等级', '')
        ))
    
    return "\n".join(lines)


# ==========================================
# 8. 将CSV结果转换为HTML表格
# ==========================================
def csv_to_html_table(csv_file: str) -> str:
    """
    将CSV文件转换为HTML表格格式
    
    Args:
        csv_file: CSV文件路径
    
    Returns:
        str: HTML表格字符串
    """
    try:
        html = ['<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">']
        
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            if not fieldnames:
                return "<p>CSV文件为空</p>"
            
            # 表头
            html.append('<thead><tr style="background-color: #f2f2f2;">')
            for field in fieldnames:
                html.append(f'<th style="text-align: left; padding: 8px;">{field}</th>')
            html.append('</tr></thead>')
            
            # 表体
            html.append('<tbody>')
            for row in reader:
                html.append('<tr>')
                for field in fieldnames:
                    value = row.get(field, '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html.append(f'<td style="padding: 8px;">{value}</td>')
                html.append('</tr>')
            html.append('</tbody>')
        
        html.append('</table>')
        return '\n'.join(html)
    
    except Exception as e:
        return f"<p>转换HTML表格时出错: {str(e)}</p>"


# ==========================================
# 9. 发送结果邮件
# ==========================================
def send_result_email(csv_file: str, date_str: str, total_token_stats: dict):
    """
    发送分析结果邮件
    
    Args:
        csv_file: 结果CSV文件路径
        date_str: 日期字符串
        total_token_stats: Token使用统计
    """
    try:
        # 读取CSV数据
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            results = list(reader)
        
        # 生成HTML内容
        html_table = csv_to_html_table(csv_file)
        
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                h2 {{ color: #333; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .token-stats {{ background-color: #e8f4f8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                table {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h2>域名分析报告 - {date_str}</h2>
            
            <div class="summary">
                <h3>分析摘要</h3>
                <p><strong>分析日期：</strong>{date_str}</p>
                <p><strong>推荐域名数量：</strong>{len(results)} 个</p>
            </div>
            
            <div class="token-stats">
                <h3>Token 使用统计</h3>
                <p><strong>总输入Token：</strong>{total_token_stats['prompt_tokens']:,}</p>
                <p><strong>总输出Token：</strong>{total_token_stats['completion_tokens']:,}</p>
                <p><strong>总计Token：</strong>{total_token_stats['total_tokens']:,}</p>
            </div>
            
            <h3>推荐域名列表</h3>
            {html_table}
            
            <p style="margin-top: 30px; color: #666; font-size: 12px;">
                此邮件由域名分析系统自动发送，详细数据请查看附件CSV文件。
            </p>
        </body>
        </html>
        """
        
        # 发送邮件
        send_email_simple(
            subject=f"阿里云域名分析结果 - {date_str}",
            content=html_content,
            content_type="html",
            attachments=[csv_file],
            use_default_recipients=True
        )
        print(f"[邮件] 阿里云域名分析结果邮件已发送（包含附件: {csv_file}）")
    
    except Exception as e:
        print(f"[错误] 发送结果邮件失败: {e}")
        import traceback
        print(f"[错误详情] {traceback.format_exc()}")
        # 重新抛出异常，让调用者知道邮件发送失败
        raise


# ==========================================
# 10. 发送错误邮件
# ==========================================
def send_error_email(error_info: str, date_str: str = None):
    """
    发送错误信息邮件
    
    Args:
        error_info: 错误信息
        date_str: 日期字符串（可选）
    """
    try:
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                h2 {{ color: #d32f2f; }}
                .error-box {{ background-color: #ffebee; padding: 15px; margin: 20px 0; border-left: 4px solid #d32f2f; border-radius: 5px; }}
                pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
            </style>
        </head>
        <body>
            <h2>域名分析系统 - 错误报告</h2>
            
            <div class="error-box">
                <h3>错误信息</h3>
                <p><strong>发生时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>分析日期：</strong>{date_str}</p>
            </div>
            
            <h3>详细错误信息</h3>
            <pre>{error_info}</pre>
            
            <p style="margin-top: 30px; color: #666; font-size: 12px;">
                此邮件由域名分析系统自动发送，请及时处理错误。
            </p>
        </body>
        </html>
        """
        
        send_email_simple(
            subject=f"域名分析系统错误报告 - {date_str}",
            content=html_content,
            content_type="html",
            use_default_recipients=True
        )
        print(f"[邮件] 错误报告邮件已发送")
    
    except Exception as e:
        print(f"[错误] 发送错误邮件失败: {e}")


# ==========================================
# 11. 主业务逻辑
# ==========================================
def process_domains_batch(date_str: str = None):
    """
    完整的域名处理流程：
    1. 读取CSV文件，分批处理（每批400个，返回10个推荐）
    2. 汇总所有批次的推荐
    3. 最终筛选得到10个推荐
    4. 保存到结果CSV文件
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    """
    # 1. 获取CSV文件名
    csv_file = get_csv_filename(date_str)
    print(f"[文件] 读取文件: {csv_file}")
    
    # 2. 获取统计信息
    info = get_batch_info(csv_file)
    print(f"[统计] 总域名数: {info['total_count']}, 每批: {info['batch_size']}, 共 {info['total_batches']} 批\n")
    
    # 3. 读取配置
    result_per_batch = int(load_config_key("config.txt", "result_per_batch", "10"))
    final_result_count = int(load_config_key("config.txt", "final_result_count", "10"))
    
    # 初始化token统计
    total_token_stats = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0
    }
    
    # 4. 分批处理
    all_recommendations = []
    batch_count = 0
    
    print("=" * 60)
    print("阶段1: 分批处理域名")
    print("=" * 60)
    
    for batch_num, batch in enumerate(load_and_batch_domains(csv_file), 1):
        batch_count = batch_num
        print(f"\n[批次 {batch_num}/{info['total_batches']}] 处理中（共 {len(batch)} 个域名）...")
        
        # 格式化批次数据
        batch_text = format_batch_for_model(batch, batch_num)
        
        # 调用模型
        print("  [模型] 正在调用模型分析...")
        response, usage_info = call_deepseek_v3_long_task(batch_text)
        
        # 打印token使用量并累加
        if usage_info:
            print(f"  [Token] 输入: {usage_info['prompt_tokens']}, "
                  f"输出: {usage_info['completion_tokens']}, "
                  f"总计: {usage_info['total_tokens']}")
            # 累加token统计
            total_token_stats['prompt_tokens'] += usage_info['prompt_tokens']
            total_token_stats['completion_tokens'] += usage_info['completion_tokens']
            total_token_stats['total_tokens'] += usage_info['total_tokens']
        
        # 解析返回结果
        batch_results = parse_model_response(response)
        
        if batch_results:
            print(f"  [成功] 本批获得 {len(batch_results)} 个推荐")
            print(batch_results)
            print("--------------------------------")
            all_recommendations.extend(batch_results)
        else:
            print(f"  [警告] 本批未能解析出推荐结果")
            print(f"  模型返回（前500字符）: {response[:500]}")
    
    print(f"\n[完成] 阶段1完成！共处理 {batch_count} 批，汇总 {len(all_recommendations)} 个推荐")
    
    # 5. 最终筛选
    if len(all_recommendations) == 0:
        print("\n[错误] 没有获得任何推荐，无法进行最终筛选")
        # 打印token统计
        print("\n" + "=" * 60)
        print("Token 使用统计：")
        print("=" * 60)
        print(f"总输入Token: {total_token_stats['prompt_tokens']:,}")
        print(f"总输出Token: {total_token_stats['completion_tokens']:,}")
        print(f"总计Token: {total_token_stats['total_tokens']:,}")
        print("=" * 60)
        
        # 发送警告邮件
        error_info = f"域名分析处理完成，但未获得任何推荐结果。\n\n处理批次: {batch_count}\n总Token使用: {total_token_stats['total_tokens']:,}\n\n请检查模型返回结果或调整提示词。"
        send_error_email(error_info, date_str)
        return
    
    print("\n" + "=" * 60)
    print(f"阶段2: 最终筛选（从 {len(all_recommendations)} 个推荐中选出 {final_result_count} 个）")
    print("=" * 60)
    
    # 确定输出文件名
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    output_file = f"{date_str}_aliyun_result.csv"
    
    # 格式化汇总数据
    summary_text = format_summary_for_final_selection(all_recommendations)
    
    # 创建最终筛选的提示词
    final_prompt = f"""请从以下已筛选的 {len(all_recommendations)} 个域名推荐中，选出最值得投资的 {final_result_count} 个域名。

要求：
1. 严格按照投资回报率 (ROI) + 变现速度进行排序
2. 必须返回完整的表格格式，严格按照以下格式：
| 序号 | 域名 | 当前价格 | 预计出手价格 | 推荐理由 | 投资等级 |
| :--- | :--- | :--- | :--- | :--- | :--- |
3. 只返回 {final_result_count} 个，不要多也不要少
4. 严禁废话，只返回表格

已筛选的推荐列表：
{summary_text}"""
    
    print("[模型] 正在调用模型进行最终筛选...")
    # 使用自定义提示词，不使用系统提示词
    system_prompt, _ = load_prompts()
    final_system_prompt = f"{system_prompt}\n\n注意：本次任务是最终筛选，请严格按照要求只返回表格，不要添加任何额外说明。"
    
    # 直接调用模型，使用自定义系统提示词
    api_key = load_config_key("config.txt", "api_key")
    base_url = load_config_key("config.txt", "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = load_config_key("config.txt", "model", "deepseek-v3")
    timeout = float(load_config_key("config.txt", "timeout", "600"))
    temperature = float(load_config_key("config.txt", "temperature", "0.3"))
    max_tokens = int(load_config_key("config.txt", "max_tokens", "8192"))
    
    http_client = httpx.Client(timeout=httpx.Timeout(timeout, connect=5.0))
    client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
    
    try:
        final_response_obj = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": final_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )
        final_response = final_response_obj.choices[0].message.content
        
        # 打印token使用量并累加
        if hasattr(final_response_obj, 'usage') and final_response_obj.usage:
            usage = final_response_obj.usage
            print(f"[Token] 最终筛选 - 输入: {usage.prompt_tokens}, "
                  f"输出: {usage.completion_tokens}, "
                  f"总计: {usage.total_tokens}")
            # 累加token统计
            total_token_stats['prompt_tokens'] += usage.prompt_tokens
            total_token_stats['completion_tokens'] += usage.completion_tokens
            total_token_stats['total_tokens'] += usage.total_tokens
    except Exception as e:
        print(f"[错误] 最终筛选调用失败: {e}")
        # 降级方案：使用前N个
        final_results = all_recommendations[:final_result_count]
        for idx, rec in enumerate(final_results, 1):
            rec['序号'] = str(idx)
        save_results_to_csv(final_results, output_file)
        # 打印token统计
        print("\n" + "=" * 60)
        print("Token 使用统计：")
        print("=" * 60)
        print(f"总输入Token: {total_token_stats['prompt_tokens']:,}")
        print(f"总输出Token: {total_token_stats['completion_tokens']:,}")
        print(f"总计Token: {total_token_stats['total_tokens']:,}")
        print("=" * 60)
        
        # 发送错误邮件（使用降级方案的结果）
        error_info = f"最终筛选调用失败，已使用降级方案（取前{final_result_count}个推荐）。\n\n错误信息: {str(e)}\n\n已保存降级结果到: {output_file}\n总Token使用: {total_token_stats['total_tokens']:,}"
        send_error_email(error_info, date_str)
        
        # 即使出错，也尝试发送结果邮件（降级方案的结果）
        try:
            send_result_email(output_file, date_str, total_token_stats)
        except:
            pass
        
        return
    
    # 解析最终结果
    final_results = parse_model_response(final_response)
    
    if not final_results:
        print("[警告] 未能解析最终结果，尝试使用前10个推荐")
        final_results = all_recommendations[:final_result_count]
        # 重新编号
        for idx, rec in enumerate(final_results, 1):
            rec['序号'] = str(idx)
    
    # 确保只有10个
    final_results = final_results[:final_result_count]
    
    print(f"[完成] 最终筛选完成，获得 {len(final_results)} 个推荐")
    
    # 6. 保存结果
    save_results_to_csv(final_results, output_file)
    
    # 7. 显示结果摘要
    print("\n" + "=" * 60)
    print("最终推荐结果摘要：")
    print("=" * 60)
    for rec in final_results:
        print(f"{rec.get('序号', 'N/A')}. {rec.get('域名', 'N/A')} - "
              f"当前: {rec.get('当前价格', 'N/A')}, "
              f"预计: {rec.get('预计出手价格', 'N/A')}, "
              f"推荐理由: {rec.get('推荐理由', 'N/A')}, "
              f"等级: {rec.get('投资等级', 'N/A')}")
    
    # 8. 打印总token使用量
    print("\n" + "=" * 60)
    print("Token 使用统计：")
    print("=" * 60)
    print(f"总输入Token: {total_token_stats['prompt_tokens']:,}")
    print(f"总输出Token: {total_token_stats['completion_tokens']:,}")
    print(f"总计Token: {total_token_stats['total_tokens']:,}")
    print("=" * 60)
    
    # 9. 发送结果邮件
    print("\n[邮件] 正在发送结果邮件...")
    send_result_email(output_file, date_str, total_token_stats)


# ==========================================
# 12. 运行
# ==========================================
if __name__ == "__main__":
    date_str = "2025-12-25"
    try:
        # 处理指定日期的数据（None表示使用当前日期）
        process_domains_batch(date_str)
    except Exception as e:
        # 捕获所有异常，发送错误邮件
        error_traceback = traceback.format_exc()
        error_info = f"程序执行出错\n\n错误类型: {type(e).__name__}\n错误信息: {str(e)}\n\n完整错误堆栈:\n{error_traceback}"
        
        print("\n" + "=" * 60)
        print("程序执行出错，正在发送错误报告...")
        print("=" * 60)
        print(error_info)
        
        # 发送错误邮件
        try:
            send_error_email(error_info, date_str)
        except Exception as email_error:
            print(f"[错误] 发送错误邮件也失败了: {email_error}")
        
        # 重新抛出异常，让程序正常退出
        raise