def normalize_type(type_) -> str:
    if isinstance(type_, str):
        return type_
    if hasattr(type_, '__qualname__'):
        return type_.__qualname__
    if hasattr(type_, '__name__'):
        return type_.__name__
    return repr(type_)
