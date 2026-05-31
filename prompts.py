# -*- coding: utf-8 -*-
"""
Prompt 策略模板：Direct / RaR (中英文)
"""

# ============================================================
# 中文 Direct — 不要求格式，保持原始"直接回答"
# ============================================================
DIRECT_PROMPT = """{question}"""

# ============================================================
# 中文 RaR — 结构化输出，最后一行答案
# ============================================================
RAR_PROMPT = """你的任务是先重新表述用户的问题，然后回答重新表述后的问题。

请按以下格式输出：
【重述问题】<重新表述后的问题>
【回答】<你的回答>

在最后一行以"答案：X"的格式输出最终答案。

用户问题：{question}"""

# ============================================================
# English Direct — bare
# ============================================================
DIRECT_PROMPT_EN = """{question}"""

# ============================================================
# English RaR — structured output
# ============================================================
RAR_PROMPT_EN = """Your task is to rephrase the user's question, then answer the rephrased question.

Output format:
[Rephrased Question] <your rephrased question>
[Answer] <your answer>

On the last line, output your answer as: Answer: X

User question: {question}"""
