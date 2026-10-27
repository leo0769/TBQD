"""邮件通知 - 通过 SMTP 把签到结果发到邮箱

环境变量:
    MAIL_HOST      SMTP 服务器地址，如 smtp.qq.com / smtp.163.com
    MAIL_PORT      SMTP 端口，默认 465（SSL）；填 587 时自动走 STARTTLS
    MAIL_USER      登录账号（一般就是发件邮箱地址）
    MAIL_PASS      登录密码或授权码（QQ / 163 / 126 等必须用「授权码」）
    MAIL_TO        收件人，多个用英文逗号分隔；留空则发给自己
    MAIL_FROM      发件人地址，默认与 MAIL_USER 相同
    MAIL_SECURITY  可选，ssl / starttls / none，默认按端口推断
    MAIL_SUBJECT   可选，默认主题前缀

未配置 MAIL_HOST / MAIL_USER / MAIL_PASS 时 send_markdown 直接返回 False，
不会影响签到主流程。
"""

import html
import logging
import os
import re
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

logger = logging.getLogger(__name__)

DEFAULT_PORT = 465
DEFAULT_SUBJECT = "贴吧签到结果"
SMTP_TIMEOUT = 20

# 常见的 SMTP 端口推断
_SSL_PORTS = {465, 994}
_STARTTLS_PORTS = {587, 25, 2525}


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _parse_recipients(raw: str) -> list[str]:
    """支持逗号、分号、空白分隔的多个收件人。"""
    return [addr for addr in re.split(r"[,;\s]+", raw) if addr]


def get_config() -> dict | None:
    """读取并校验邮件配置；缺少必要项时返回 None。"""
    host = _env("MAIL_HOST")
    user = _env("MAIL_USER")
    password = _env("MAIL_PASS")
    if not (host and user and password):
        return None

    port_raw = _env("MAIL_PORT")
    try:
        port = int(port_raw) if port_raw else DEFAULT_PORT
    except ValueError:
        logger.warning(f"MAIL_PORT 配置非法（{port_raw}），回退到 {DEFAULT_PORT}")
        port = DEFAULT_PORT

    security = _env("MAIL_SECURITY").lower()
    if security not in ("ssl", "starttls", "none"):
        if port in _SSL_PORTS:
            security = "ssl"
        elif port in _STARTTLS_PORTS:
            security = "starttls"
        else:
            security = "starttls"

    recipients = _parse_recipients(_env("MAIL_TO")) or [user]

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender": _env("MAIL_FROM") or user,
        "recipients": recipients,
        "security": security,
    }


def _inline(text: str) -> str:
    """转义 HTML 并还原 **加粗**、`行内代码`。"""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def markdown_to_text(md: str) -> str:
    """把签到结果用的极简 markdown 转成纯文本（用于不支持 HTML 的客户端）。"""
    lines = []
    for line in md.splitlines():
        s = line.rstrip()
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"^>\s?", "", s)
        s = re.sub(r"^[-*]\s+", "· ", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"`(.+?)`", r"\1", s)
        lines.append(s)
    return "\n".join(lines).strip()


def markdown_to_html(md: str) -> str:
    """把签到结果用的极简 markdown 转成一段带样式的 HTML 正文。"""
    blocks: list[str] = []
    in_list = False

    for raw in md.splitlines():
        line = raw.strip()

        if line.startswith(("- ", "* ")):
            if not in_list:
                blocks.append('<ul style="margin:8px 0 16px;padding-left:22px;">')
                in_list = True
            blocks.append(f'<li style="margin:4px 0;">{_inline(line[2:])}</li>')
            continue

        if in_list:
            blocks.append("</ul>")
            in_list = False

        if not line:
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            level = min(len(heading.group(1)) + 1, 6)
            blocks.append(
                f'<h{level} style="margin:0 0 12px;font-size:{max(18, 26 - level * 2)}px;'
                f'color:#1f2328;">{_inline(heading.group(2))}</h{level}>'
            )
        elif line.startswith(">"):
            quote = line.lstrip(">").strip()
            blocks.append(
                '<blockquote style="margin:0 0 12px;padding:8px 12px;border-left:3px solid #d0d7de;'
                f'color:#57606a;background:#f6f8fa;">{_inline(quote)}</blockquote>'
            )
        else:
            blocks.append(f'<p style="margin:0 0 10px;line-height:1.7;">{_inline(line)}</p>')

    if in_list:
        blocks.append("</ul>")

    body = "\n".join(blocks)
    return (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\','
        "Roboto,'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif;"
        'font-size:14px;color:#1f2328;max-width:640px;">' + body + "</div>"
    )


def _build_message(cfg: dict, subject: str, content: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header("贴吧签到", "utf-8")), cfg["sender"]))
    msg["To"] = ", ".join(cfg["recipients"])
    msg["Date"] = formatdate(localtime=True)

    msg.attach(MIMEText(markdown_to_text(content), "plain", "utf-8"))
    msg.attach(MIMEText(markdown_to_html(content), "html", "utf-8"))
    return msg


def _connect(cfg: dict):
    context = ssl.create_default_context()
    if cfg["security"] == "ssl":
        server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=SMTP_TIMEOUT, context=context)
    else:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=SMTP_TIMEOUT)
        server.ehlo()
        if cfg["security"] == "starttls":
            server.starttls(context=context)
            server.ehlo()
    server.login(cfg["user"], cfg["password"])
    return server


def send_markdown(content: str, subject: str | None = None) -> bool:
    """发送一封 HTML 邮件。

    Args:
        content: markdown 文本，与推送到企业微信的内容保持一致。
        subject: 邮件主题；不传则使用 MAIL_SUBJECT 或默认值。

    Returns:
        是否发送成功。未配置邮箱或发送异常时返回 False。
    """
    cfg = get_config()
    if cfg is None:
        logger.info("未配置 MAIL_HOST/MAIL_USER/MAIL_PASS，跳过邮件推送")
        return False

    subject = (subject or _env("MAIL_SUBJECT") or DEFAULT_SUBJECT).strip()

    try:
        msg = _build_message(cfg, subject, content)
    except Exception as e:
        logger.error(f"邮件内容构建失败: {e}")
        return False

    for attempt in (1, 2):
        try:
            with _connect(cfg) as server:
                server.sendmail(cfg["sender"], cfg["recipients"], msg.as_string())
            logger.info(f"邮件推送成功 -> {', '.join(cfg['recipients'])}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            # 认证失败重试没有意义，直接给出排查提示
            logger.error(
                f"邮件推送失败: SMTP 认证被拒绝（{e.smtp_code} {e.smtp_error!r}）。"
                "QQ/163 等邮箱需使用「授权码」而非登录密码，并确认已开启 SMTP 服务"
            )
            return False
        except Exception as e:
            if attempt == 1:
                logger.warning(f"邮件推送异常（{e}），重试一次...")
            else:
                logger.error(f"邮件推送失败: {e}")
    return False
