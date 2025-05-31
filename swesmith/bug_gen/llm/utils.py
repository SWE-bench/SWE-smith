import re


PROMPT_KEYS = ["system", "demonstration", "instance"]


def extract_code_block(text: str) -> str:
    pattern = r"```(?:\w+)?\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""
