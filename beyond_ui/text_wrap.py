"""Measured paragraph wrapping shared by retained layout and painting.

Keeps Latin words together; CJK scripts may break between characters. Explicit
newlines survive and oversized tokens break only when they cannot fit a line.
"""
import re

_TOKENS = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\uf900-\ufaff]|[^\s\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\uf900-\ufaff]+|[^\S\n]+')


def wrap_text(text, width, measure):
    width=max(1,width)
    result=[]
    for paragraph in str(text).split('\n'):
        line=''
        for token in _TOKENS.findall(paragraph):
            if token.isspace():
                if line:line+=' '
                continue
            trial=line+token
            if line and measure(trial)>width:
                result.append(line.rstrip());line=''
            if measure(token)>width:
                for char in token:
                    if line and measure(line+char)>width:
                        result.append(line.rstrip());line=''
                    line+=char
            else:line+=token
        result.append(line.rstrip())
    return tuple(result)
