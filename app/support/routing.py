from enum import StrEnum


class Route(StrEnum):
    ANSWER = "answer"
    TICKET = "ticket"


SENSITIVE_PATTERNS: list[str] = [
    # password / credentials
    r"\breset\b.*\bpassword\b", r"\bchange\b.*\bpassword\b", r"\bforgot\b.*\bpassword\b",
    r"\bnew\b.*\bpassword\b", r"\bcredential\b",
    # permission / access escalation
    r"\bchange\b.*\bpermission\b", r"\bgrant\b.*\baccess\b", r"\bgrant\b.*\bme\b",
    r"\badmin\b.*\baccess\b", r"\blevel\s*[34]\b", r"\bproduction\b.*\baccess\b",
    r"\bproduction\b.*\bsystem\b", r"\bupgrade\b.*\baccess\b", r"\belevate\b.*\b(my|access)\b",
    r"\bescalat\w*\b.*\bprivilege\b", r"\broot\b.*\baccess\b", r"\bpromot\w*\b.*\baccess\b",
    # role / account changes
    r"\bchange\b.*\brole\b", r"\bdelete\b.*\baccount\b", r"\bdisable\b.*\bmfa\b",
    r"\bbypass\b.*\bapprov\w*\b", r"\boverride\b",
    # data privacy / security
    r"\bpersonal\b.*\bdata\b", r"\bleak\w*\b", r"\bdata\b.*\bbreach\b", r"\bPII\b",
    r"\bprivacy\b.*\bviolation\b", r"\bexpose\w*\b.*\bdata\b",
    # system / infra changes
    r"\bshut\s*down\b", r"\breboot\b.*\bserver\b", r"\brestart\b.*\bservice\b",
    r"\bdelete\b.*\bdatabase\b", r"\bdrop\b.*\btable\b",
    # Chinese password / permission / privacy / infrastructure actions
    r"重置.*密码", r"修改.*密码", r"忘记.*密码", r"找回.*密码",
    r"开通.*权限", r"授予.*权限", r"提升.*权限", r"升级.*权限",
    r"管理员权限", r"生产环境.*权限", r"四级.*权限",
    r"导出.*(个人信息|员工数据|数据)", r"(个人信息|员工数据).*(泄露|暴露)",
    r"关闭.*服务器", r"重启.*服务器", r"删除.*数据库", r"删除.*数据表",
    r"绕过.*审批", r"禁用.*多因素认证", r"关闭.*MFA",
]

import re


def calculate_risk_score(question: str) -> int:
    """计算问题中匹配的敏感模式数量（0 = 安全）。"""
    normalized = question.lower()
    matches = 0
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, normalized):
            matches += 1
    return matches


def decide_route(question: str, evidence_count: int) -> Route:
    """证据不足或问题敏感时路由到工单。"""
    if evidence_count == 0:
        return Route.TICKET
    if calculate_risk_score(question) > 0:
        return Route.TICKET
    return Route.ANSWER
