# -*- coding: utf-8 -*-
"""
Prompt 策略模板：Direct / RaR / 
"""

# ============================================================
# 策略1: Direct (直接回答)
# ============================================================
DIRECT_PROMPT = """

{question}"""

# ============================================================
# 策略2: RaR (Rephrase and Respond — 先重述再回答)
# ============================================================
RAR_PROMPT = """你的任务是先重新表述用户的问题，然后回答重新表述后的问题。



请按以下格式输出：
【重述问题】<重新表述后的问题>
【回答】<你的回答>

用户问题：{question}"""

# ============================================================
# English versions (for external datasets)
# ============================================================
DIRECT_PROMPT_EN = """Answer directly. Do not explain or show reasoning. Output the answer only.

{question}"""

RAR_PROMPT_EN = """Your task is to rephrase the user's question, then answer the rephrased question.

Steps:
1. Read the question carefully. Identify any ambiguity, vagueness, missing information, or hidden assumptions.
2. Rephrase it into a clearer, more specific version that eliminates possible misunderstandings.
3. Answer the rephrased question.

Output format:
[Rephrased Question] <your rephrased question>
[Answer] <your answer>

User question: {question}"""
