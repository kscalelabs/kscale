"""Defines utilities for working with asyncio."""

import asyncio
import textwrap
from functools import wraps
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

import click

T = TypeVar("T")
P = ParamSpec("P")


def coro(f: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]:
    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def recursive_help(cmd: click.Command, parent: click.Context | None = None, indent: int = 0) -> str:
    ctx = click.core.Context(cmd, info_name=cmd.name, parent=parent)
    help_text = cmd.get_help(ctx)
    commands = getattr(cmd, "commands", {})
    for sub in commands.values():
        help_text += recursive_help(sub, ctx, indent + 2)
    return textwrap.indent(help_text, " " * indent)
