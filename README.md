# 域名分析系统

一个自动化的域名投资分析系统，支持从阿里云和腾讯云爬取域名数据，使用大语言模型进行智能分析，并自动发送推荐结果邮件。

## 功能特性

- 🔍 **数据爬取**：自动从阿里云和腾讯云域名交易平台爬取域名数据
- 🤖 **智能分析**：使用 DeepSeek-v3 大模型进行域名价值分析
- 📊 **批量处理**：支持大批量域名数据的智能分批处理
- 📧 **邮件通知**：自动发送分析结果邮件（支持HTML格式和附件）
- ⏰ **定时任务**：支持定时自动执行（每天9点）
- 🔐 **反爬虫处理**：内置反爬虫机制处理，支持登录状态保存

## 项目结构

```
DomainAlpha/
├── main.py                 # 主程序入口
├── aliyun.py              # 阿里云爬虫
├── tencent.py             # 腾讯云爬虫
├── llm_aliyun.py          # 阿里云域名分析
├── llm_tencent.py         # 腾讯云域名分析
├── domain_processor.py    # 数据处理模块
├── email_sender.py        # 邮件发送模块
├── scheduler.py           # 定时任务调度器
├── config.txt.example     # 配置文件模板
├── prompt.txt            # 大模型提示词
└── requirements.txt      # 依赖包列表
```

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd DomainAlpha
```

### 2. 安装依赖

```bash
# 使用国内源安装（推荐）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

# 安装 Playwright 浏览器驱动
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
playwright install chromium
```

### 3. 配置项目

```bash
# 复制配置文件模板
copy config.txt.example config.txt  # Windows
# 或
cp config.txt.example config.txt    # Linux/Mac
```

编辑 `config.txt`，填入以下配置：

- **API 密钥**：阿里云百炼 API Key
- **邮件配置**：SMTP 服务器、发件人邮箱、密码、收件人邮箱
- **其他参数**：可根据需要调整

## 使用方法

### 方式1：直接运行（完整流程）

```bash
python main.py
```

或指定日期：

```bash
python main.py --date 2025-12-26
```

### 方式2：分步执行

```python
# 只爬取阿里云数据
python aliyun.py

# 只分析阿里云域名
python llm_aliyun.py

# 只爬取腾讯云数据
python tencent.py

# 只分析腾讯云域名
python llm_tencent.py
```

### 方式3：定时任务（推荐）

**Windows：**
```bash
# 双击运行
start_scheduler.bat

# 或命令行运行
python scheduler.py
```

调度器会：
1. 启动时立即执行一次
2. 之后每天 09:00 自动执行

## 配置说明

### 主要配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `api_key` | 阿里云百炼 API 密钥 | - |
| `batch_size` | 每批处理的域名数量 | 400 |
| `result_per_batch` | 每批返回的推荐数量 | 10 |
| `final_result_count` | 最终推荐数量 | 10 |
| `email.sender_email` | 发件人邮箱 | - |
| `email.sender_password` | 发件人密码 | - |
| `email.recipient_emails` | 收件人邮箱（多个用逗号分隔） | - |

### 邮件配置

支持常见的 SMTP 服务商：
- 163 邮箱（推荐）
- QQ 邮箱
- Gmail
- 其他支持 SMTP 的邮箱

## 输出文件

- `日期_aliyun.csv` - 阿里云爬取的原始数据
- `日期_aliyun_result.csv` - 阿里云分析结果
- `日期_tencent.csv` - 腾讯云爬取的原始数据
- `日期_tencent_result.csv` - 腾讯云分析结果
- `logs/` - 执行日志目录

## 注意事项

1. **API 密钥安全**：不要将 `config.txt` 提交到代码仓库
2. **登录状态**：首次运行可能需要手动登录，登录状态会保存到 `aliyun_auth.json`
3. **网络要求**：需要能够访问阿里云和腾讯云网站
4. **浏览器驱动**：首次使用需要安装 Playwright 浏览器驱动

## 故障排查

### 问题1：爬虫被拦截
- 检查是否已登录
- 查看 `aliyun_auth.json` 是否存在
- 尝试手动登录后重新运行

### 问题2：邮件发送失败
- 检查 SMTP 配置是否正确
- 确认邮箱是否开启 SMTP 服务
- 检查网络连接

### 问题3：模型调用失败
- 检查 API 密钥是否正确
- 确认账户余额是否充足
- 查看错误日志

## 开发计划

- [ ] 支持更多域名交易平台
- [ ] 添加数据可视化
- [ ] 支持自定义分析规则
- [ ] 添加数据库存储

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

