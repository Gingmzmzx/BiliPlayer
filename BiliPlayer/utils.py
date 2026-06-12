from .config import DEBUG_FLG

def prt(*args, **kwargs):
    if not DEBUG_FLG:
        return
    print(*args, **kwargs)
