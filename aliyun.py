import csv
import datetime
import random
import time
import os
from playwright.sync_api import Playwright, sync_playwright

def load_config_key(file_path="config.txt", target_key="api_key", default=None):
    """从配置文件中读取配置项"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == target_key:
                        return value.strip()
        return default
    except:
        return default

def check_and_handle_login(page):
    """检测并处理登录跳转"""
    current_url = page.url
    if 'login' in current_url.lower() or 'account.aliyun.com' in current_url:
        print("\n" + "=" * 60)
        print("[警告] 检测到反爬虫机制，页面跳转到登录页")
        print("=" * 60)
        print("请在浏览器中手动完成以下操作：")
        print("1. 完成登录验证")
        print("2. 返回域名交易页面 (https://mi.aliyun.com)")
        print("3. 重新执行筛选操作")
        print("=" * 60)
        input("完成后按回车继续...")
        
        # 检查是否已返回正确页面
        page.wait_for_load_state('networkidle')
        if 'mi.aliyun.com' not in page.url:
            raise Exception("未正确返回域名交易页面，请检查")
        return True
    return False

def run(playwright: Playwright, date_str: str = None) -> str:
    """
    爬取阿里云域名数据
    
    Args:
        playwright: Playwright实例
        date_str: 日期字符串，格式为 "YYYY-MM-DD"（如 "2025-12-25"）
                 如果为None，使用当前日期
    
    Returns:
        str: 生成的CSV文件路径
    """
    # 从配置文件读取爬虫参数
    slow_mo_min = int(load_config_key("config.txt", "crawler.slow_mo_min", "300"))
    slow_mo_max = int(load_config_key("config.txt", "crawler.slow_mo_max", "800"))
    page_delay_min = float(load_config_key("config.txt", "crawler.page_delay_min", "2"))
    page_delay_max = float(load_config_key("config.txt", "crawler.page_delay_max", "4"))
    action_delay_min = float(load_config_key("config.txt", "crawler.action_delay_min", "0.5"))
    action_delay_max = float(load_config_key("config.txt", "crawler.action_delay_max", "1.5"))
    auth_state_file = load_config_key("config.txt", "crawler.auth_state_file", "aliyun_auth.json")
    
    # 方案一：增强浏览器真实性
    slow_mo = random.randint(slow_mo_min, slow_mo_max)
    browser = playwright.chromium.launch(
        headless=False, 
        slow_mo=slow_mo,
        args=[
            '--disable-blink-features=AutomationControlled',  # 隐藏自动化特征
            '--disable-dev-shm-usage',
            '--no-sandbox'
        ]
    )
    
    # 方案四：使用持久化上下文保存登录状态
    storage_state = None
    if os.path.exists(auth_state_file):
        storage_state = auth_state_file
        print(f"[信息] 检测到已保存的登录状态: {auth_state_file}")
    
    # 创建更真实的浏览器上下文
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        permissions=['geolocation'],
        geolocation={'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
        color_scheme='light',
        storage_state=storage_state,  # 加载已保存的登录状态
        extra_http_headers={
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
    )
    
    # 注入脚本隐藏webdriver特征
    page = context.new_page()
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.navigator.chrome = {
            runtime: {}
        };
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
    """)

    # 1. 初始化访问
    url = "https://mi.aliyun.com/?quickSearch=%5B%22%22%5D&originReleaseDate=all&dataType=all&tab=all"
    page.goto(url, wait_until='networkidle', timeout=30000)
    
    # 检测并处理登录跳转
    if check_and_handle_login(page):
        # 如果检测到登录，保存登录状态
        context.storage_state(path=auth_state_file)
        print(f"[信息] 已保存登录状态到: {auth_state_file}")
        # 重新导航到目标页面
        page.goto(url, wait_until='networkidle', timeout=30000)
    
    # 添加随机延迟，模拟人类行为
    time.sleep(random.uniform(page_delay_min, page_delay_max))
    
    # --- 执行筛选操作 - 每个操作之间添加随机延迟 ---
    page.locator(".ant-select-selection-item").first.click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_text(".com", exact=True).click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_role("button", name="确 定").click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_title("不限", exact=True).first.click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_text("纯字母").click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.locator("ul:nth-child(2) > li > .ant-cascader-menu-item-content").first.click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.locator("#main-app").get_by_text("不限", exact=True).nth(1).click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_text("所有待释放（可预定）").click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_text("默认").click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_text("域名长度").click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_text("由短到长").click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_role("button", name="搜 索").click()
    time.sleep(random.uniform(page_delay_min, page_delay_max))
    
    # 设置 200 条/页
    page.wait_for_load_state("networkidle")
    page.get_by_text("条/页").click()
    time.sleep(random.uniform(action_delay_min, action_delay_max))
    
    page.get_by_text("200 条/页").click()
    time.sleep(random.uniform(page_delay_min, page_delay_max))  # 给表格留出重新渲染的时间

    # 准备 CSV 文件
    if date_str is None:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    file_name = f"{date_str}_aliyun.csv"
    headers = ["序号", "域名", "最低价格", "长度", "注册日期", "预定结束时间"]
    
    index_counter = 1  # 初始化自定义序号

    with open(file_name, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        page_num = 1
        while True:
            print(f"正在爬取第 {page_num} 页...")
            # 确保表格数据已加载，增加等待时间和重试机制
            try:
                page.wait_for_selector(".ant-table-tbody tr", timeout=15000)
            except Exception as e:
                print(f"等待表格加载超时，尝试等待更长时间...")
                page.wait_for_timeout(3000)
                # 再次尝试
                try:
                    page.wait_for_selector(".ant-table-tbody tr", timeout=10000)
                except:
                    print(f"第 {page_num} 页加载失败，跳过...")
                    # 尝试翻页继续
                    next_button = page.locator("li.ant-pagination-next")
                    is_disabled = next_button.get_attribute("aria-disabled") == "true"
                    if is_disabled:
                        print("已到达最后一页，结束爬取。")
                        break
                    next_button.click()
                    page_num += 1
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                    continue
            
            # 获取当前页所有行
            rows = page.locator(".ant-table-tbody tr").all()
            
            for row in rows:
                cols = row.locator("td").all()
                # 过滤掉空行或加载行
                if len(cols) < 6:
                    continue
                
                try:
                    # 阿里云表格结构参考：
                    # 实际表格结构：
                    # cols[0]: 勾选框（空）
                    # cols[1]: 域名
                    # cols[2]: 最低价格
                    # cols[3]: 域名简介
                    # cols[4]: 长度
                    # cols[5]: 注册日期
                    # cols[6]: 空列
                    # cols[7]: 空列
                    # cols[8]: 空列
                    # cols[9]: 预定结束时间
                    # cols[10]: 空列
                    # cols[11]: 操作
                    domain = cols[1].inner_text().split('\n')[0] # 只取域名，去掉“待释放”等标签
                    price = cols[2].inner_text().replace("¥", "").strip()
                    length = cols[4].inner_text()
                    reg_date = cols[5].inner_text()
                    end_time = cols[9].inner_text()

                    writer.writerow([index_counter, domain, price, length, reg_date, end_time])
                    index_counter += 1 # 序号递增
                except Exception as e:
                    print(f"提取行失败: {e}")

            # --- 翻页逻辑 ---
            next_button = page.locator("li.ant-pagination-next")
            
            # 判断“下一页”按钮是否失效（aria-disabled="true" 或包含特定 class）
            is_disabled = next_button.get_attribute("aria-disabled") == "true"
            
            if is_disabled:
                print("已成功爬取所有页面。")
                break
            
            next_button.click()
            page_num += 1
            # 翻页后等待网络闲置，确保数据更新（增加等待时间）
            page.wait_for_load_state("networkidle")
            
            # 检测是否在翻页时触发登录跳转
            if check_and_handle_login(page):
                # 如果检测到登录，保存登录状态并重新导航
                context.storage_state(path=auth_state_file)
                print(f"[信息] 已保存登录状态到: {auth_state_file}")
                # 重新导航到目标页面
                url = "https://mi.aliyun.com/?quickSearch=%5B%22%22%5D&originReleaseDate=all&dataType=all&tab=all"
                page.goto(url, wait_until='networkidle', timeout=30000)
                # 重新执行筛选操作（这里可以优化，但为了简单起见先这样）
                print("[警告] 需要重新执行筛选操作，请手动完成筛选后按回车继续...")
                input("完成后按回车继续...")
            
            # 翻页后使用更长的随机延迟
            time.sleep(random.uniform(page_delay_min + 1, page_delay_max + 2)) 

    print(f"任务完成！共采集 {index_counter - 1} 条数据，保存至: {file_name}")
    
    # 保存登录状态（方案四）
    try:
        context.storage_state(path=auth_state_file)
        print(f"[信息] 已保存登录状态到: {auth_state_file}")
    except Exception as e:
        print(f"[警告] 保存登录状态失败: {e}")
    
    context.close()
    browser.close()
    
    return file_name

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)