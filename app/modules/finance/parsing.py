from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.modules.finance.schemas import SetupInput, SpendInput


class FinanceInputError(ValueError):
    pass


def parse_amount(raw: str, *, allow_zero: bool = False) -> int:
    value = raw.strip().lower().replace("rp", "").replace(" ", "")
    multipliers = {
        "ribu": 1_000,
        "rb": 1_000,
        "k": 1_000,
        "juta": 1_000_000,
        "jt": 1_000_000,
    }
    multiplier = 1
    for suffix in sorted(multipliers, key=len, reverse=True):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            multiplier = multipliers[suffix]
            break
    if multiplier == 1:
        value = value.replace(".", "").replace(",", "")
    else:
        if "," in value and "." in value:
            raise FinanceInputError("Format nominal tidak dikenali.")
        value = value.replace(",", ".")
    try:
        result = Decimal(value) * multiplier
    except InvalidOperation as error:
        raise FinanceInputError("Nominal tidak valid.") from error
    if not result.is_finite():
        raise FinanceInputError("Nominal tidak valid.")
    if result != result.to_integral_value():
        raise FinanceInputError("Nominal rupiah harus menghasilkan angka bulat.")
    amount = int(result)
    minimum = 0 if allow_zero else 1
    if amount < minimum or amount > 9_000_000_000_000_000:
        raise FinanceInputError("Nominal berada di luar batas yang didukung.")
    return amount


def parse_setup(arguments: str, *, today: date) -> SetupInput:
    tokens = arguments.split()
    if not tokens:
        raise FinanceInputError(
            "Gunakan /setup <nominal> [first=14d] [repeat=7d] "
            "[start=YYYY-MM-DD]."
        )
    amount = parse_amount(tokens[0])
    first_days = 7
    recurring_days = 7
    start_date = today
    for token in tokens[1:]:
        key, separator, raw_value = token.partition("=")
        if not separator:
            raise FinanceInputError(f"Opsi setup tidak dikenali: {token}")
        if key in ("first", "repeat"):
            days = _parse_days(raw_value)
            if key == "first":
                first_days = days
            else:
                recurring_days = days
        elif key == "start":
            start_date = _parse_date(raw_value)
        else:
            raise FinanceInputError(f"Opsi setup tidak dikenali: {key}")
    end_date = start_date + timedelta(days=first_days - 1)
    if start_date > today:
        raise FinanceInputError("Tanggal mulai tidak boleh di masa depan.")
    if end_date < today:
        raise FinanceInputError("Periode pertama tersebut sudah berakhir.")
    return SetupInput(amount, first_days, recurring_days, start_date)


def parse_spend(arguments: str) -> SpendInput:
    tokens = arguments.split()
    if len(tokens) < 2:
        raise FinanceInputError(
            "Gunakan /spend <nominal> <untuk apa> [date=YYYY-MM-DD]."
        )
    amount = parse_amount(tokens[0])
    spent_on: date | None = None
    purpose_tokens: list[str] = []
    for token in tokens[1:]:
        if token.startswith("date="):
            if spent_on is not None:
                raise FinanceInputError("Tanggal hanya boleh diberikan sekali.")
            spent_on = _parse_date(token.removeprefix("date="))
        else:
            purpose_tokens.append(token)
    purpose = " ".join(purpose_tokens).strip()
    if not purpose or len(purpose) > 255:
        raise FinanceInputError("Tujuan wajib diisi dan maksimal 255 karakter.")
    return SpendInput(amount, purpose, spent_on)


def parse_shorthand(text: str) -> SpendInput | None:
    first, separator, remainder = text.strip().partition(" ")
    if not separator or not remainder.strip():
        return None
    try:
        return parse_spend(f"{first} {remainder}")
    except FinanceInputError:
        return None


def _parse_days(raw: str) -> int:
    value = raw.lower().removesuffix("d")
    try:
        days = int(value)
    except ValueError as error:
        raise FinanceInputError("Durasi harus ditulis seperti 7d atau 14d.") from error
    if not 1 <= days <= 365:
        raise FinanceInputError("Durasi harus antara 1 dan 365 hari.")
    return days


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as error:
        raise FinanceInputError("Tanggal harus memakai format YYYY-MM-DD.") from error
