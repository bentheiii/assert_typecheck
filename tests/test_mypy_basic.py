import re
from typing import TypeVar, overload, Iterator, Union, Tuple, Literal, Generic

from pytest import mark, raises, fixture

from assert_typecheck.assert_mypy import assert_mypy_typechecks, DMyPyRunner
from tests.util import REF


@fixture(scope='session')
def dmypy():
    with DMyPyRunner() as dmypy:
        yield dmypy


def gc0():
    pass


def gc1() -> int:
    x: int = 1
    return x


def gc2() -> int:
    x = 1
    y = 2
    return x + y


def gc3() -> int:
    T = TypeVar('T')

    def f(x: T) -> T:
        ...

    return f(1)


def gc4() -> Tuple[int, str]:
    @overload
    def f(x: int) -> int:
        ...

    @overload
    def f(x: str) -> str:
        ...

    def f(x):
        ...

    return f(1), f('a')


def gc5() -> int:
    from contextlib import contextmanager

    @contextmanager
    def cm() -> Iterator[int]:
        ...

    with cm() as x:
        t: int = x
    return t


def gc6() -> str:
    class A:
        def foo(self) -> str:
            ...

    a = A()
    return a.foo()


T = TypeVar('T')


class A(Generic[T]):
    def foo(self) -> T:
        ...


def comb(x: T, y: T) -> T:
    ...


def gc7(a: A[int], b: int) -> int:
    return comb(a.foo(), b)


good_code = [gc0, gc1, gc2, gc3, gc4, gc5, gc6, gc7]


@mark.parametrize('code', good_code)
def test_good_code(code, dmypy):
    dmypy.assert_mypy_typechecks(code)


def bc0() -> int:
    return 'a'

def bc1(a: A[int], b: int) -> str:
    return comb(a.foo(), b)

bad_code = [bc0, bc1]


@mark.parametrize('code', bad_code)
def test_bad_code(code, dmypy):
    with raises(AssertionError):
        dmypy.assert_mypy_typechecks(code)


def test_alias_good(dmypy):
    @dmypy.assert_mypy_typechecks(aliases={'T': int})
    def _() -> int:
        x: T = 1
        return x


def test_alias_good_tv(dmypy):
    T = TypeVar('T')

    @dmypy.assert_mypy_typechecks(aliases={T: int})
    def _() -> int:
        x: T = 1
        return x


def test_alias_bad(dmypy):
    with raises(AssertionError,
                match=re.escape(f'{REF(4)}: error:')):
        @dmypy.assert_mypy_typechecks(aliases={'T': str})
        def _() -> int:
            x: T = 1
            return x


def test_alias_bad_tv(dmypy):
    T = TypeVar('T')

    with raises(AssertionError,
                match=re.escape(f'{REF(4)}: error:')):
        @dmypy.assert_mypy_typechecks(aliases={'T': str})
        def _() -> int:
            x: T = 1
            return x


def test_python_version_old_good():
    @assert_mypy_typechecks(python_version='3.6')
    def _() -> int:
        import sys
        if sys.version_info > (3, 7):
            return 'a'
        else:
            return 15


def test_python_version_old_bad():
    with raises(AssertionError,
                match=re.escape(f'{REF(7)}: error: Incompatible return value type (got "str", expected "int")')):
        @assert_mypy_typechecks(python_version='3.6')
        def _() -> int:
            import sys
            if sys.version_info > (3, 7):
                return 15
            else:
                return 'a'


def test_python_version_new_good():
    @assert_mypy_typechecks(python_version='3.10')
    def _() -> int:
        import sys
        if sys.version_info > (3, 7):
            return 15
        else:
            return 'a'


def test_python_version_new_bad():
    with raises(AssertionError,
                match=re.escape(f'{REF(5)}: error: Incompatible return value type (got "str", expected "int")')):
        @assert_mypy_typechecks(python_version='3.10')
        def _() -> int:
            import sys
            if sys.version_info > (3, 7):
                return 'a'
            else:
                return 15


def test_platform_good():
    @assert_mypy_typechecks(platform='linux')
    def _() -> int:
        import sys
        if sys.platform == 'win32':
            return 'a'
        else:
            return 15


def test_platform_bad():
    with raises(AssertionError,
                match=re.escape(f'{REF(5)}: error: Incompatible return value type (got "str", expected "int")')):
        @assert_mypy_typechecks(platform='win32')
        def _() -> int:
            import sys
            if sys.platform == 'win32':
                return 'a'
            else:
                return 15
