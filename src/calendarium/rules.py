"""Parser and evaluator for the Calendarium rule DSL.

The original project described rules with an ANTLR grammar
(``CalendariumLexer.g4`` / ``CalendariumParser.g4``).  The grammar is small,
so this port uses a hand-written tokenizer and recursive-descent parser: no
code generation, no runtime dependency.

Date rules (``RuleDate``) are evaluated for a *calendar year* and return the
matching Gregorian dates::

    "12-25"                      the 25th day of the 12th month (period calendar)
    "[EASTER]"                   a named computed date (see the function registry)
    "([EASTER]) + 39"            39 days after Easter Sunday
    "((11-23) - 1) << WEDNESDAY" first Wednesday on/before 22 November
    "*MONDAY"                    every Monday of the year

Observed rules (``RuleObserved``) transform a single date::

    "? (SATURDAY | SUNDAY) : >> MONDAY"   shifted to next Monday when it
                                          falls on a weekend

Several clauses can be chained with ``;`` -- the first clause whose weekday
condition matches is applied (used by countries with asymmetric substitute
rules, e.g. the United States)::

    "? SATURDAY : << FRIDAY ; ? SUNDAY : >> MONDAY"

``>>`` / ``<<`` move to the next / previous given weekday and *stay in place*
when the date already falls on it (same semantics as the C# implementation).

The named computed dates are kept in an extensible registry; use
:func:`register_function` to add new ones.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import Callable, List, Union

from .calendars import CalendarBase, GregorianCalendar, get_calendar
from .easter import easter_date, orthodox_easter_date

GREGORIAN = GregorianCalendar()


class RuleSyntaxError(ValueError):
    """Raised when a rule string cannot be parsed."""

    def __init__(self, source: str, message: str):
        super().__init__(f"invalid rule {source!r}: {message}")
        self.source = source


# ---------------------------------------------------------------------------
# Registry of named computed dates ([EASTER], [PASSOVER], ...)
#
# Each function takes the (Gregorian) year and returns a list of dates.
# ---------------------------------------------------------------------------

def _passover(year: int) -> List[date]:
    """Pesach I: 15 Nisan of the Hebrew year overlapping the given spring."""
    return [get_calendar("Hebrew").to_gregorian(year + 3760, 1, 15)]


def _rosh_hashanah(year: int) -> List[date]:
    """1 Tishri of the Hebrew year beginning in the given Gregorian year."""
    return [get_calendar("Hebrew").to_gregorian(year + 3761, 7, 1)]


def _yom_kippur(year: int) -> List[date]:
    return [get_calendar("Hebrew").to_gregorian(year + 3761, 7, 10)]


def _hanukkah(year: int) -> List[date]:
    """First day of Hanukkah: 25 Kislev."""
    return [get_calendar("Hebrew").to_gregorian(year + 3761, 9, 25)]


_FUNCTIONS: dict[str, Callable[[int], List[date]]] = {
    "EASTER": lambda year: [easter_date(year)],
    "ORTHODOX_EASTER": lambda year: [orthodox_easter_date(year)],
    "PASSOVER": _passover,
    "ROSH_HASHANAH": _rosh_hashanah,
    "YOM_KIPPUR": _yom_kippur,
    "HANUKKAH": _hanukkah,
}


def register_function(name: str, fn: Callable[[int], List[date]]) -> None:
    """Register (or override) a named computed date usable as ``[NAME]``."""
    _FUNCTIONS[name.upper()] = fn


def registered_functions() -> tuple[str, ...]:
    return tuple(sorted(_FUNCTIONS))


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_WEEKDAYS = {
    # datetime.weekday() convention: Monday == 0 ... Sunday == 6
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}

_TOKEN_RE = re.compile(
    r"""\s+
      | (?P<number>[0-9]+)
      | (?P<ident>[A-Z][A-Z0-9_$\#]*)
      | (?P<symbol>>>|<<|\|\||[()\[\]:;?|+\-*])
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class _Token:
    kind: str  # 'number' | 'ident' | symbol text
    text: str


def _tokenize(source: str) -> List[_Token]:
    tokens: List[_Token] = []
    pos = 0
    text = source.upper()
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if m is None:
            raise RuleSyntaxError(source, f"unexpected character {text[pos]!r}")
        pos = m.end()
        if m.lastgroup == "number":
            tokens.append(_Token("number", m.group()))
        elif m.lastgroup == "ident":
            tokens.append(_Token("ident", m.group()))
        elif m.lastgroup == "symbol":
            symbol = "|" if m.group() == "||" else m.group()
            tokens.append(_Token(symbol, symbol))
    return tokens


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Mask:
    month: int
    day: int


@dataclass(frozen=True)
class _Func:
    name: str


@dataclass(frozen=True)
class _AllWeekdays:
    weekday: int


@dataclass(frozen=True)
class _Number:
    value: int


@dataclass(frozen=True)
class _Weekday:
    weekday: int


@dataclass(frozen=True)
class _BinOp:
    left: "_Node"
    op: str  # '+', '-', '>>', '<<'
    right: "_Node"


@dataclass(frozen=True)
class _Current:
    """The implicit input date of an observed rule."""


_Node = Union[_Mask, _Func, _AllWeekdays, _Number, _Weekday, _BinOp, _Current]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_OPERATORS = ("+", "-", ">>", "<<")


class _Parser:
    def __init__(self, source: str):
        self.source = source
        self.tokens = _tokenize(source)
        self.pos = 0

    # -- helpers ----------------------------------------------------------

    def peek(self) -> Union[_Token, None]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self) -> _Token:
        token = self.peek()
        if token is None:
            raise RuleSyntaxError(self.source, "unexpected end of rule")
        self.pos += 1
        return token

    def expect(self, kind: str) -> _Token:
        token = self.next()
        if token.kind != kind:
            raise RuleSyntaxError(self.source, f"expected {kind!r}, got {token.text!r}")
        return token

    def at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    # -- grammar ----------------------------------------------------------

    def parse_date_script(self) -> _Node:
        node = self.parse_expression(self.parse_primary())
        if not self.at_end():
            raise RuleSyntaxError(self.source, f"unexpected token {self.peek().text!r}")
        return node

    def parse_observed_script(self) -> List[tuple]:
        """Return ``[(condition, expression), ...]`` clauses.

        Each clause is a weekday condition (or ``None`` for unconditional)
        and an expression over the input date; clauses are separated by
        ``;`` and the first matching one applies.
        """
        clauses = [self.parse_observed_clause()]
        while (token := self.peek()) is not None and token.kind == ";":
            self.next()
            clauses.append(self.parse_observed_clause())
        if not self.at_end():
            raise RuleSyntaxError(self.source, f"unexpected token {self.peek().text!r}")
        return clauses

    def parse_observed_clause(self) -> tuple:
        condition = None
        token = self.peek()
        if token is not None and token.kind == "?":
            self.next()
            condition = self.parse_bool_expression()
            self.expect(":")
        node = self.parse_expression(_Current())
        return condition, node

    def parse_bool_expression(self) -> frozenset:
        token = self.peek()
        if token is not None and token.kind == "(":
            self.next()
            days = self.parse_bool_expression()
            self.expect(")")
            return days
        days = {self.parse_weekday()}
        while (token := self.peek()) is not None and token.kind == "|":
            self.next()
            days.add(self.parse_weekday())
        return frozenset(days)

    def parse_weekday(self) -> int:
        token = self.next()
        if token.kind != "ident" or token.text not in _WEEKDAYS:
            raise RuleSyntaxError(self.source, f"expected a weekday, got {token.text!r}")
        return _WEEKDAYS[token.text]

    def parse_expression(self, left: _Node) -> _Node:
        """Parse a left-associative chain of ``<op> <primary>`` applications."""
        while (token := self.peek()) is not None and token.kind in _OPERATORS:
            self.next()
            right = self.parse_primary()
            left = _BinOp(left, token.kind, right)
        return left

    def parse_primary(self) -> _Node:
        token = self.next()

        if token.kind == "(":
            inner = self.parse_expression(self.parse_primary())
            self.expect(")")
            return inner

        if token.kind == "[":
            name = self.expect("ident").text
            self.expect("]")
            if name not in _FUNCTIONS:
                raise RuleSyntaxError(
                    self.source,
                    f"unknown function [{name}]; known: {', '.join(registered_functions())}",
                )
            return _Func(name)

        if token.kind == "*":
            return _AllWeekdays(self.parse_weekday())

        if token.kind == "ident":
            if token.text in _WEEKDAYS:
                return _Weekday(_WEEKDAYS[token.text])
            raise RuleSyntaxError(self.source, f"unexpected identifier {token.text!r}")

        if token.kind == "number":
            # either a mask `month-day` or a plain number operand
            nxt = self.peek()
            if nxt is not None and nxt.kind == "-":
                after = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                if after is not None and after.kind == "number":
                    self.next()  # '-'
                    day = int(self.next().text)
                    return _Mask(int(token.text), day)
            return _Number(int(token.text))

        raise RuleSyntaxError(self.source, f"unexpected token {token.text!r}")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _next_weekday(d: date, weekday: int) -> date:
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d


def _previous_weekday(d: date, weekday: int) -> date:
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _eval(node: _Node, year: int, calendar: CalendarBase, current: Union[date, None]):
    if isinstance(node, _Mask):
        return [calendar.to_gregorian(year, node.month, node.day)]

    if isinstance(node, _Func):
        return list(_FUNCTIONS[node.name](year))

    if isinstance(node, _AllWeekdays):
        result = []
        d = calendar.to_gregorian(year, 1, 1)
        while calendar.year_of(d) == year:
            if d.weekday() == node.weekday:
                result.append(d)
            d += timedelta(days=1)
        return result

    if isinstance(node, _Number):
        return node.value

    if isinstance(node, _Weekday):
        return node.weekday

    if isinstance(node, _Current):
        return current

    if isinstance(node, _BinOp):
        left = _eval(node.left, year, calendar, current)
        right = _eval(node.right, year, calendar, current)

        single = isinstance(left, date)
        dates = [left] if single else left

        if node.op in ("+", "-"):
            if not isinstance(right, int) or isinstance(node.right, _Weekday):
                raise ValueError(f"operator {node.op!r} expects a number")
            delta = timedelta(days=right if node.op == "+" else -right)
            dates = [d + delta for d in dates]
        else:  # '>>' / '<<'
            if not isinstance(node.right, _Weekday):
                raise ValueError(f"operator {node.op!r} expects a weekday")
            move = _next_weekday if node.op == ">>" else _previous_weekday
            dates = [move(d, right) for d in dates]

        return dates[0] if single else dates

    raise TypeError(f"unknown node {node!r}")  # pragma: no cover


class DateRule:
    """A compiled ``RuleDate``: ``evaluate(year, calendar) -> list[date]``.

    ``year`` is expressed in ``calendar`` (e.g. the Hijri year when the
    period uses the Hijri calendar); the result is a list of Gregorian dates.
    """

    def __init__(self, source: str, ast: _Node):
        self.source = source
        self._ast = ast

    def evaluate(self, year: int, calendar: CalendarBase = GREGORIAN) -> List[date]:
        result = _eval(self._ast, year, calendar, None)
        if isinstance(result, date):
            return [result]
        if not isinstance(result, list):
            raise RuleSyntaxError(self.source, "rule does not produce dates")
        return result

    def __repr__(self) -> str:  # pragma: no cover
        return f"DateRule({self.source!r})"


class ObservedRule:
    """A compiled ``RuleObserved``: ``evaluate(date) -> date``.

    Each clause (``? (SATURDAY | SUNDAY) : >> MONDAY``) applies its
    expression when the input date falls on one of the listed weekdays; the
    first matching clause wins, and the date is returned unchanged when none
    matches.
    """

    def __init__(self, source: str, clauses: List[tuple]):
        self.source = source
        self._clauses = clauses

    def evaluate(self, d: date) -> date:
        for condition, ast in self._clauses:
            if condition is None or d.weekday() in condition:
                result = _eval(ast, d.year, GREGORIAN, d)
                if not isinstance(result, date):
                    raise RuleSyntaxError(
                        self.source, "observed rule does not produce a date"
                    )
                return result
        return d

    def __repr__(self) -> str:  # pragma: no cover
        return f"ObservedRule({self.source!r})"


@lru_cache(maxsize=None)
def parse_date_rule(source: str) -> DateRule:
    return DateRule(source, _Parser(source).parse_date_script())


@lru_cache(maxsize=None)
def parse_observed_rule(source: str) -> ObservedRule:
    return ObservedRule(source, _Parser(source).parse_observed_script())
