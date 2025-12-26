import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
import os


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
# 邮件发送类
# ==========================================
class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config_file="config.txt"):
        """
        初始化邮件发送器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.smtp_server = load_config_key(config_file, "email.smtp_server", "")
        self.smtp_port = int(load_config_key(config_file, "email.smtp_port", "587"))
        self.sender_email = load_config_key(config_file, "email.sender_email", "")
        self.sender_password = load_config_key(config_file, "email.sender_password", "")
        self.use_tls = load_config_key(config_file, "email.use_tls", "True").lower() in ('true', '1', 'yes', 'on')
        self.sender_name = load_config_key(config_file, "email.sender_name", "")
        
        # 读取默认收件人（支持多个，用逗号分隔）
        recipient_emails_str = load_config_key(config_file, "email.recipient_emails", "")
        if recipient_emails_str:
            self.default_recipients = [email.strip() for email in recipient_emails_str.split(',') if email.strip()]
        else:
            self.default_recipients = []
        
        # 验证必要配置
        if not all([self.smtp_server, self.sender_email, self.sender_password]):
            raise ValueError("邮件配置不完整，请检查config.txt中的email相关配置")
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        content: str,
        content_type: str = "plain",
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            content: 邮件内容
            content_type: 内容类型，"plain" 或 "html"
            cc_emails: 抄送邮箱列表（可选）
            bcc_emails: 密送邮箱列表（可选）
            attachments: 附件文件路径列表（可选）
        
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            
            # 设置发件人
            if self.sender_name:
                msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            else:
                msg['From'] = self.sender_email
            
            # 设置收件人
            msg['To'] = ", ".join(to_emails)
            
            # 设置主题
            msg['Subject'] = subject
            
            # 添加抄送
            if cc_emails:
                msg['Cc'] = ", ".join(cc_emails)
            
            # 添加邮件正文
            msg.attach(MIMEText(content, content_type, 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
                    else:
                        print(f"⚠️ 附件文件不存在: {file_path}")
            
            # 连接SMTP服务器并发送
            all_recipients = to_emails.copy()
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            # 根据端口判断使用SSL还是TLS
            if self.smtp_port == 465:
                # 使用SSL（端口465）
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg, to_addrs=all_recipients)
            else:
                # 使用TLS（端口587等）
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg, to_addrs=all_recipients)
            
            print(f"[成功] 邮件发送成功！收件人: {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            print(f"[错误] 邮件发送失败: {str(e)}")
            return False
    
    def send_text_email(
        self,
        to_emails: List[str],
        subject: str,
        text_content: str,
        **kwargs
    ) -> bool:
        """
        发送纯文本邮件（便捷方法）
        
        Args:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            text_content: 文本内容
            **kwargs: 其他参数（cc_emails, bcc_emails, attachments）
        
        Returns:
            bool: 发送成功返回True
        """
        return self.send_email(to_emails, subject, text_content, content_type="plain", **kwargs)
    
    def send_html_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        **kwargs
    ) -> bool:
        """
        发送HTML邮件（便捷方法）
        
        Args:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            html_content: HTML内容
            **kwargs: 其他参数（cc_emails, bcc_emails, attachments）
        
        Returns:
            bool: 发送成功返回True
        """
        return self.send_email(to_emails, subject, html_content, content_type="html", **kwargs)


# ==========================================
# 便捷函数接口（供其他程序调用）
# ==========================================
def send_email_simple(
    to_emails: Optional[List[str]] = None,
    subject: str = "",
    content: str = "",
    content_type: str = "plain",
    attachments: Optional[List[str]] = None,
    use_default_recipients: bool = False
) -> bool:
    """
    简单的邮件发送接口（供其他程序调用）
    
    Args:
        to_emails: 收件人邮箱列表（可选，如果为None且use_default_recipients=True，则使用配置文件中的收件人）
        subject: 邮件主题
        content: 邮件内容
        content_type: 内容类型，"plain" 或 "html"
        attachments: 附件文件路径列表（可选）
        use_default_recipients: 是否使用配置文件中的默认收件人（如果to_emails为None）
    
    Returns:
        bool: 发送成功返回True
    
    Example:
        # 使用指定的收件人
        send_email_simple(
            to_emails=["user@example.com"],
            subject="测试邮件",
            content="这是一封测试邮件",
            attachments=["report.csv"]
        )
        
        # 使用配置文件中的默认收件人
        send_email_simple(
            subject="测试邮件",
            content="这是一封测试邮件",
            use_default_recipients=True
        )
    """
    try:
        sender = EmailSender()
        
        # 如果to_emails为None且use_default_recipients为True，使用默认收件人
        if to_emails is None:
            if use_default_recipients and sender.default_recipients:
                to_emails = sender.default_recipients
            else:
                raise ValueError("必须指定to_emails或设置use_default_recipients=True且配置了默认收件人")
        
        return sender.send_email(
            to_emails=to_emails,
            subject=subject,
            content=content,
            content_type=content_type,
            attachments=attachments
        )
    except Exception as e:
        print(f"[错误] 邮件发送失败: {str(e)}")
        return False


# ==========================================
# 测试和示例
# ==========================================
if __name__ == "__main__":
    # 示例1: 使用类发送邮件
    try:
        sender = EmailSender()
        
        # 发送纯文本邮件
        sender.send_text_email(
            to_emails=["recipient@example.com"],
            subject="测试邮件 - 文本",
            text_content="这是一封测试邮件，内容为纯文本格式。"
        )
        
        # 发送HTML邮件
        html_content = """
        <html>
          <body>
            <h2>测试邮件 - HTML格式</h2>
            <p>这是一封<strong>HTML格式</strong>的测试邮件。</p>
            <p>支持<em>富文本</em>格式。</p>
          </body>
        </html>
        """
        sender.send_html_email(
            to_emails=["recipient@example.com"],
            subject="测试邮件 - HTML",
            html_content=html_content
        )
        
        # 发送带附件的邮件
        sender.send_email(
            to_emails=["recipient@example.com"],
            subject="测试邮件 - 带附件",
            content="这是一封带附件的测试邮件。",
            attachments=["example.csv"]  # 如果文件存在的话
        )
        
    except ValueError as e:
        print(f"配置错误: {e}")
        print("请检查config.txt文件，确保设置了正确的邮件配置")
    except Exception as e:
        print(f"发生错误: {e}")
    
    # 示例2: 使用便捷函数发送邮件
    # send_email_simple(
    #     to_emails=["user@example.com"],
    #     subject="简单测试",
    #     content="使用便捷函数发送的邮件"
    # )

