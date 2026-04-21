# audit/services/policy_reasoner.py

import json
import re
import requests
from typing import Any, Dict, List, Optional

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "deepseek-r1:7b"

# 控制每条规则喂给模型的文本长度，避免太长导致慢/不稳定
MAX_TEXT_CHARS = 3500

PROMPT_TEMPLATE = """
你是申报文件智能审核系统中的专业审核助手。
你的任务不是裁定违法，而是依据给定政策关注点识别“疑似不充分/不合理/可能冲突之处”，并给出需要人工核实的问题。

【政策主题】
{theme}

【政策依据】
{policy_basis}

【审核关注点】
{focus}

【项目文本】
{text}

请严格只输出 JSON（不要任何其它文字），格式如下：
{{
  "has_issue": true/false,
  "issue_type": "合规风险/内容缺失/专业不合理/逻辑矛盾/表述模糊",
  "risk_level": "高/中/低",
  "reason": "用1-3句话说明依据与原因，尽量引用项目文本的关键点",
  "evidence": "从项目文本中摘取最关键的一句或一段作为证据（没有则留空）",
  "visit_question": "一句话现场核实问题"
}}
"""

def _call_ollama(prompt: str, timeout_sec: int = 180) -> str:
    r = requests.post(
        OLLAMA_URL,
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
        timeout=timeout_sec,
    )
    r.raise_for_status()
    return (r.json().get("response") or "").strip()

def _safe_json_loads(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # 兜底：截取第一个 {...}
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

def build_prompt(text: str, rule: Dict[str, str]) -> str:
    clipped = text[:MAX_TEXT_CHARS]
    return PROMPT_TEMPLATE.format(
        theme=rule["theme"],
        policy_basis=rule["policy_basis"],
        focus=rule["focus"],
        text=clipped,
    )

def reason_with_policy_kb(text: str, rules: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    遍历判定库规则，让模型逐条推理，输出多条疑似问题（结构化）
    """
    issues: List[Dict[str, Any]] = []

    for rule in rules:
        prompt = build_prompt(text, rule)
        raw = _call_ollama(prompt)
        data = _safe_json_loads(raw) or {}

        if data.get("has_issue") is True:
            issues.append({
                "rule_id": rule["id"],
                "theme": rule["theme"],
                "policy_basis": rule["policy_basis"],
                "focus": rule["focus"],
                "issue_type": data.get("issue_type", "合规风险"),
                "risk_level": data.get("risk_level", rule.get("risk_level", "中")),
                "reason": data.get("reason", ""),
                "evidence": data.get("evidence", ""),
                "visit_question": data.get("visit_question", ""),
            })

    # 风险排序：高 > 中 > 低
    rank = {"高": 3, "中": 2, "低": 1}
    issues.sort(key=lambda x: rank.get(x.get("risk_level", "中"), 2), reverse=True)

    return issues


def stream_ollama(prompt: str, timeout_sec: int = 180):
    """
    流式读取 Ollama 输出（逐 token / 逐片段）
    """
    with requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": True,
        },
        stream=True,
        timeout=timeout_sec,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            chunk = obj.get("response", "")
            if chunk:
                yield chunk

            if obj.get("done") is True:
                break
