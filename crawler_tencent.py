import csv
import time
import datetime
from playwright.sync_api import Playwright, sync_playwright

def run(playwright: Playwright, date_str: str = None) -> str:
    # 启动浏览器，headless=False 方便观察滚动情况
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # 1. 访问并执行筛选逻辑
    print("正在初始化页面...")
    page.goto("https://buy.cloud.tencent.com/mi/reserve")
    
    # 执行筛选操作
    page.get_by_text("纯字母").click()
    page.locator(".tea-form__controls > .tea-dropdown > .tea-dropdown__header").click()
    page.get_by_text(".com", exact=True).click()
    page.get_by_role("button", name="确定").click()
    page.get_by_role("button", name="搜索", exact=True).click()

    # 等待第一批数据渲染出来
    try:
        page.wait_for_selector("tbody tr", timeout=15000)
    except:
        print("未发现数据行，请检查筛选条件或网络。")
        return

    # 2. 定位内部滚动容器
    # 腾讯云表格内容通常在这个 div 中，它负责产生内部滚动条
    container_selector = ".tea-table__body"
    
    print("开始执行内部局部滚动...")
    
    all_results = {}  # 使用字典以域名为Key，实现自动去重
    last_len = 0
    no_change_count = 0

    while True:
        # 提取当前可见的所有行数据
        rows = page.locator("tbody tr").all()
        for row in rows:
            cells = row.locator("td").all_inner_texts()
            if len(cells) > 1:
                # 假设第一列是域名，作为 Key 去重
                domain = cells[0].strip()
                all_results[domain] = [c.strip() for c in cells]

        current_len = len(all_results)
        print(f"已抓取不重复数据: {current_len} 条...")

        # 执行滚动操作：将容器滚动条向下移动
        # 我们每次移动 800 像素，模拟人类翻页效果，触发加载
        page.evaluate(f"""
            const el = document.querySelector('{container_selector}');
            if (el) {{
                el.scrollTop += 800; 
            }}
        """)

        # 给网络请求和 DOM 渲染预留时间
        time.sleep(1.5)

        # 判断是否停止：如果连续多次滚动后数据总量不再增加，则认为到底，或者已抓取1000条
        if current_len >= 1000:
            print(f"已抓取 {current_len} 条数据，达到上限1000条，停止抓取。")
            break
        
        if current_len == last_len:
            no_change_count += 1
            # 这里的 5 次是为了防止网络瞬间波动导致的加载延迟
            if no_change_count >= 5: 
                print("数据量不再增长，判定已加载全部。")
                break
        else:
            last_len = current_len
            no_change_count = 0

    # 3. 保存结果
    if all_results:
        if date_str is None:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        file_name = save_data(all_results.values(), date_str)
    else:
        if date_str is None:
            date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        # 确保logs目录存在
        import os
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        file_name = os.path.join(logs_dir, f"{date_str}_tencent.csv")
    
    context.close()
    browser.close()
    
    return file_name

def save_data(data_rows, date_str=None):
    if date_str is None:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 确保logs目录存在
    import os
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    filename = os.path.join(logs_dir, f'{date_str}_tencent.csv')
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['域名', '预订倒计时', '注册时间', '删除时间', '当前人数', '当前价格', '操作'])
        writer.writerows(data_rows)
    print(f"✅ 任务完成！共保存 {len(data_rows)} 条数据到 {filename}")
    return filename

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)