"""
PII masking for logs and the audit trail.

Masks the personal identifiers that appear in Pakistani legal work, keeping just enough to tell records
apart (first / last characters):

    CNIC            35202-1234567-1      -> 35202-*******-1
    mobile phone    0300-1234567 / +92 300 1234567 -> 0300-*****67 / +92 300 *****67
    e-mail          ayesha.khan@firm.pk  -> a***@firm.pk
    IBAN            PK36SCBL0000001123456702 -> PK36****************6702
    card number     4111 1111 1111 1111  -> **** **** **** 1111
    NTN             1234567-8            -> *******-8

`mask(text)` masks a string. `PiiFilter` is a logging filter: every record is formatted first (so
values passed as arguments are masked too) and then masked, before any handler writes it. It is
installed on the project's loggers by src/utils/logger.py and on the web server's loggers.

Regexes cannot recognise names or addresses; those are kept out of the logs by design (the logs
record actions and document ids, not document text).
"""

import logging
import re

_RULES = [
    # CNIC: 5-7-1 digits, with or without dashes
    (re.compile(r"\b(\d{5})-?(\d{7})-?(\d)\b"), lambda m: f"{m.group(1)}-*******-{m.group(3)}"),
    # IBAN (Pakistan): PK + 2 check digits + 4-letter bank code + 16 digits
    (re.compile(r"\bPK(\d{2})\s?([A-Z]{4})\s?((?:\d\s?){12})(\d{4})\b"), lambda m: f"PK{m.group(1)}{'*' * 16}{m.group(4)}"),
    # card numbers: 13-16 digits in groups
    (re.compile(r"\b(?:\d{4}[ -]?){3}(\d{1,4})\b"), lambda m: f"**** **** **** {m.group(1)}"),
    # mobile numbers: 03xx-xxxxxxx, +92 3xx xxxxxxx, 0092...
    (re.compile(r"(?<!\d)((?:\+92|0092)[\s-]?3\d{2}|03\d{2})[\s-]?(\d{5})(\d{2})(?!\d)"), lambda m: f"{m.group(1)}-*****{m.group(3)}"),
    # e-mail
    (re.compile(r"\b([A-Za-z0-9])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"), lambda m: f"{m.group(1)}***@{m.group(2)}"),
    # NTN: 7 digits - 1 digit
    (re.compile(r"(?<![\d-])(\d{7})-(\d)(?![\d-])"), lambda m: f"*******-{m.group(2)}"),
]


def mask(text: str) -> str:
    if not text:
        return text
    for pattern, repl in _RULES:
        text = pattern.sub(repl, text)
    return text


class PiiFilter(logging.Filter):
    """Masks the message and each argument in place. The arguments keep their structure, because some
    formatters (uvicorn's access log) read them by position."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(mask(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: mask(v) if isinstance(v, str) else v for k, v in record.args.items()}
        return True


_FILTER = PiiFilter()


def protect(logger: logging.Logger) -> logging.Logger:
    """Mask PII in everything this logger's handlers write (filters on a handler apply to all records it emits)."""
    for handler in logger.handlers:
        if _FILTER not in handler.filters:
            handler.addFilter(_FILTER)
    if _FILTER not in logger.filters:
        logger.addFilter(_FILTER)
    return logger
