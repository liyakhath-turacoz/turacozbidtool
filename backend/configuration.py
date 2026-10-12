"""Load private local settings while preserving explicit environment overrides."""
import os
from pathlib import Path
import re


def load_local_environment():
    path=Path(__file__).resolve().parent.parent / '.env'
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        key, separator, value=line.strip().partition('=')
        if not separator or not re.fullmatch(r'(?:TURACOZ|ICECAT)_[A-Z0-9_]+',key):
            continue
        value=value.strip()
        if len(value)>=2 and value[0]==value[-1] and value[0] in {'"',"'"}:
            value=value[1:-1]
        os.environ.setdefault(key,value)


load_local_environment()
