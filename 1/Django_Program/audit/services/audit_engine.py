import requests
import json
import re


def ai_audit(text: str) -> dict:
    prompt = f"""
你是申报文件智能审核系统中的专业审核助手，
你的任务是根据政策规划精神识别“疑似不合理或不充分之处”。
请严格以 JSON 格式返回审核结果。

格式：
{{
  "issue_type": "问题类型",
  "risk_level": "高/中/低",
  "description": "问题描述"
}}

文本：
{text}
"""

    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "deepseek-r1:7b",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    data = resp.json()
    raw = data.get("response", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())

    return {
        "issue_type": "解析失败",
        "risk_level": "低",
        "description": raw[:300]
    }
