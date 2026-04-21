import traceback

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .models import Project, Document, Issue
from .services.file_parser import parse_file
from .services.green_kb import GREEN_DEV_KB
from .services.policy_reasoner import reason_with_policy_kb


def upload_page(request):
    # 只负责展示页面
    return render(request, "audit/upload_page.html")


@csrf_exempt
def upload_and_audit(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "no file"}, status=400)

    project = Project.objects.create(name="毕业设计示例项目")
    document = Document.objects.create(project=project, file=f)

    text = parse_file(f)
    if not text or not text.strip():
        return JsonResponse({"error": "empty text"}, status=400)

    # ✅ 改这里：判定库推理（输出 issues 列表）
    issues = reason_with_policy_kb(text, GREEN_DEV_KB)

    if not issues:
        return JsonResponse({
            "issue_type": "未发现明显问题",
            "risk_level": "低",
            "description": "基于绿色发展判定库推理，未发现需要重点核实的疑似问题。",
            "issues": []
        }, json_dumps_params={"ensure_ascii": False})

    # 入库：取前 5 条
    for it in issues[:5]:
        Issue.objects.create(
            document=document,
            issue_type=it.get("issue_type", "待核实"),
            risk_level=it.get("risk_level", "中"),
            description=(
                f"【规则】{it.get('rule_id')}\n"
                f"【主题】{it.get('theme')}\n"
                f"【关注点】{it.get('focus')}\n"
                f"【原因】{it.get('reason')}\n"
                f"【证据】{it.get('evidence')}\n"
                f"【走访问题】{it.get('visit_question')}"
            )
        )

    best = issues[0]
    return JsonResponse({
        "issue_type": best.get("issue_type", "合规风险"),
        "risk_level": best.get("risk_level", "中"),
        "description": best.get("reason", ""),
        "issues": issues[:5]
    }, json_dumps_params={"ensure_ascii": False})


from django.http import StreamingHttpResponse
from .services.policy_reasoner import stream_ollama, build_prompt
from .services.green_kb import GREEN_DEV_KB
from .services.file_parser import parse_file

import re

@csrf_exempt
def stream_reasoning(request):
    f = request.FILES.get("file")
    if not f:
        return StreamingHttpResponse(["data: 未选择文件\n\n"], content_type="text/event-stream")

    text = parse_file(f)
    if not text or not text.strip():
        return StreamingHttpResponse(["data: 文本为空\n\n"], content_type="text/event-stream")

    rules = GREEN_DEV_KB[:5]

    def clean_piece(s: str) -> str:
        # 去掉常见的 markdown 代码块标记
        s = s.replace("```json", "").replace("```", "")
        # 把非常离谱的空白压缩（保留中文可读性）
        s = re.sub(r"[ \t]{2,}", " ", s)
        return s

    def event_stream():
        for rule in rules:
            yield f"data: \n=== 正在审核规则 {rule['id']}：{rule['theme']} ===\n\n"

            prompt = build_prompt(text, rule)

            buf = []            # 缓冲碎片
            buf_len = 0

            for token in stream_ollama(prompt):
                if not token:
                    continue

                token = clean_piece(token)
                if not token:
                    continue

                buf.append(token)
                buf_len += len(token)

                # ✅ 触发输出条件：累计到一定长度 或 遇到换行/结束符
                if buf_len >= 80 or "\n" in token or "}" in token:
                    chunk = "".join(buf)
                    # 压缩连续空行（避免你现在那种大量空白）
                    chunk = re.sub(r"\n{3,}", "\n\n", chunk)
                    yield f"data: {chunk}\n\n"
                    buf.clear()
                    buf_len = 0

            # 把残余缓冲吐出来
            if buf:
                chunk = "".join(buf)
                chunk = re.sub(r"\n{3,}", "\n\n", chunk)
                yield f"data: {chunk}\n\n"

        yield "data: \n=== 流式推理结束 ===\n\n"

    resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    return resp
