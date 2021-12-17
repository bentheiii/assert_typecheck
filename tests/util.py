import os.path
from inspect import stack


def REF(offset):
    frame = stack()[1]
    filename = os.path.basename(frame.filename)
    return f'{filename}:{frame.lineno + offset}'
