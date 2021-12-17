import inspect
import re
from abc import ABC, abstractmethod
from functools import partial
from itertools import chain
from os import remove
from tempfile import NamedTemporaryFile
from typing import Mapping, Optional, Sequence, Tuple

from mypy.api import run, run_dmypy

from assert_typecheck.util import normalize_type


class BaseMypyRunner(ABC):
    @abstractmethod
    def run(self, args: Sequence[str], temp_file_name: str, target_name: str) -> Tuple[str, str, int]:
        ...

    def _assert_mypy_typechecks(self, obj, *, python_version: Optional[str] = None, platform: Optional[str] = None,
                                other_options: Sequence[str] = (), aliases: Optional[Mapping] = None, ):
        filename = inspect.getfile(obj)
        mod_source, source_start = inspect.findsource(obj)
        source_end = len(inspect.getblock(mod_source[source_start:])) + source_start

        mod_source = list(mod_source)
        for line_index in chain(range(source_start), range(source_end, len(mod_source))):
            mod_source[line_index] = mod_source[line_index].rstrip() + '# type: ignore\n'

        if aliases:
            aliases = {normalize_type(k): normalize_type(v) for k, v in aliases.items()}

            def repl(match):
                return aliases[match.group(0)]

            repl_pattern = re.compile(
                r'(?<![a-zA-Z_])' + '|'.join(re.escape(k) for k in aliases.keys()) + r'(?![a-zA-Z_])')

            for line_index in range(source_start, source_end):
                mod_source[line_index] = repl_pattern.sub(repl, mod_source[line_index])

        indent = re.match(r'\s*', mod_source[source_start])[0]  # type: ignore[index]
        mod_source.insert(source_end, f'{indent}import typing; __any: typing.Any = ...;{obj.__name__}(*__any)\n')

        args = [*other_options, '--show-error-context', '--show-error-codes', '--no-error-summary']

        if python_version:
            args.append('--python-version')
            args.append(python_version)

        if platform:
            args.append('--platform')
            args.append(platform)

        with NamedTemporaryFile(mode="w", delete=False) as file:
            file.writelines(mod_source)
        try:
            out, err, exit_code = self.run(args, file.name, filename)
        finally:
            remove(file.name)

        if exit_code == 0:
            return

        if err:
            raise RuntimeError(err)

        raise AssertionError(out)

    def assert_mypy_typechecks(self, obj=None, **kwargs):
        if obj is None:
            return partial(self._assert_mypy_typechecks, **kwargs)
        return self._assert_mypy_typechecks(obj, **kwargs)


class MypyRunner(BaseMypyRunner):
    def run(self, args: Sequence[str], temp_file_name: str, target_name: str) -> Tuple[str, str, int]:
        args = [*args, '--shadow-file', target_name, temp_file_name, target_name]
        return run(args)


_global_mypy_runner = MypyRunner()

assert_mypy_typechecks = _global_mypy_runner.assert_mypy_typechecks


class DMyPyRunner(BaseMypyRunner):
    def __init__(self, python_version: Optional[str] = None, platform: Optional[str] = None,
                 other_options: Sequence[str] = ()):
        self.python_version = python_version
        self.platform = platform
        self.other_options = other_options

    def _assert_mypy_typechecks(self, obj, *, python_version: Optional[str] = None, platform: Optional[str] = None,
                                other_options: Sequence[str] = (), aliases: Optional[Mapping] = None, ):
        other_options = tuple(other_options)
        if (python_version != self.python_version
                or platform != self.platform
                or other_options != self.other_options):
            return assert_mypy_typechecks(obj, python_version=python_version, platform=platform,
                                          other_options=other_options, aliases=aliases)
        return super()._assert_mypy_typechecks(obj, python_version=python_version, platform=platform,
                                               other_options=other_options, aliases=aliases)

    def run(self, args: Sequence[str], temp_file_name: str, target_name: str) -> Tuple[str, str, int]:
        args = ['run', '--', *args, temp_file_name]
        raw_results = run_dmypy(args)
        # because we don't shadow the file, we un-alias the target name ourselves
        out, err, exit_code = raw_results
        out = out.replace(temp_file_name, target_name)
        return out, err, exit_code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        run_dmypy(['stop'])
