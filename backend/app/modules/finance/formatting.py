from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import escape

from app.modules.finance.schemas import PeriodValue, TransactionValue


def idr(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    formatted = f"{abs(amount):,}".replace(",", ".")
    return f"{sign}Rp{formatted}"


def summary_text(period: PeriodValue, *, today: date) -> str:
    lines = [
        "<b>Ringkasan Budget</b>",
        f"Periode #{period.sequence}: {period.start_date:%d-%m-%Y} – {period.end_date:%d-%m-%Y}",
        f"ID periode: <code>{period.id}</code>",
    ]
    if period.effective_budget is None:
        lines.extend(
            (
                "Budget efektif: <b>menunggu keputusan rollover</b>",
                f"Budget dasar: {idr(period.base_budget)}",
                f"Saldo periode lalu: {idr(period.previous_balance or 0)}",
                f"Realisasi sementara: {idr(period.realization)}",
                "Pilih rollover agar jatah harian dapat dihitung.",
                "Atau gunakan <code>/budget 1jt</code> untuk nilai custom.",
            )
        )
        return "\n".join(lines)
    balance = period.effective_budget - period.realization
    status = _status(period.effective_budget, period.realization)
    suffix = " (sementara)" if today <= period.end_date else ""
    days = (period.end_date - period.start_date).days + 1
    remaining_days = max((period.end_date - today).days + 1, 1)
    lines.extend(
        (
            f"Budget: {idr(period.effective_budget)}",
            f"Realisasi: {idr(period.realization)}",
            f"Saldo: {idr(balance)}",
            f"Status: <b>{status}{suffix}</b>",
            "",
            f"Patokan per hari: {idr(_divide(period.effective_budget, days))}",
            f"Sisa per hari: {idr(_divide(balance, remaining_days))}",
        )
    )
    return "\n".join(lines)


def history_text(periods: list[PeriodValue], *, today: date) -> str:
    if not periods:
        return "Belum ada histori budget."
    lines = ["<b>Histori Budget</b>"]
    for period in periods:
        budget = (
            "pending" if period.effective_budget is None else idr(period.effective_budget)
        )
        status = (
            "Pending"
            if period.effective_budget is None
            else _status(period.effective_budget, period.realization)
        )
        lines.append(
            f"#{period.sequence} · {period.start_date:%d-%m}–{period.end_date:%d-%m-%Y}\n"
            f"  ID {period.id} · Budget {budget} · Realisasi {idr(period.realization)} · {status}"
        )
    return "\n".join(lines)


def transactions_text(
    period: PeriodValue, transactions: list[TransactionValue]
) -> str:
    lines = [
        f"<b>Transaksi Periode #{period.sequence}</b>",
        f"{period.start_date:%d-%m-%Y} – {period.end_date:%d-%m-%Y}",
    ]
    if not transactions:
        lines.append("Belum ada transaksi.")
        return "\n".join(lines)
    daily: dict[date, int] = defaultdict(int)
    for transaction in transactions:
        daily[transaction.spent_on] += transaction.amount
    lines.append("\n<b>Total Harian</b>")
    for spent_on, total in sorted(daily.items()):
        lines.append(f"{spent_on:%d-%m-%Y}: {idr(total)}")
    lines.append("\n<b>Rincian</b>")
    for transaction in transactions:
        lines.append(
            f"#{transaction.id} · {transaction.spent_on:%d-%m} · "
            f"{idr(transaction.amount)}\n  {escape(transaction.purpose)}"
        )
    lines.append(f"\nTotal: {idr(period.realization)}")
    return "\n".join(lines)


def rollover_markup(period: PeriodValue) -> dict[str, object]:
    carry_result = period.base_budget + (period.previous_balance or 0)
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"Bawa saldo ({idr(carry_result)})",
                    "callback_data": f"fin:roll:{period.id}:carry",
                }
            ],
            [
                {
                    "text": f"Reset dasar ({idr(period.base_budget)})",
                    "callback_data": f"fin:roll:{period.id}:base",
                },
                {
                    "text": "Mulai Rp0",
                    "callback_data": f"fin:roll:{period.id}:zero",
                },
            ],
        ]
    }


def help_text() -> str:
    return "\n".join(
        (
            "<b>Finance Bot</b>",
            "Kelola budget periodik dan catat realisasi pengeluaran.",
            "",
            "<b>Setup dan budget</b>",
            "/setup 1jt first=14d repeat=7d",
            "/budget 1,2jt",
            "",
            "<b>Pengeluaran</b>",
            "/spend 50rb makan siang",
            "50rb makan siang",
            "/transactions · /edit · /delete",
            "",
            "<b>Laporan</b>",
            "/summary · /history",
            "",
            "<b>Alert</b>",
            "/alert on|off|HH:MM|here",
            "/timezone Asia/Jakarta",
        )
    )


def _status(budget: int, realization: int) -> str:
    if realization < budget:
        return "Di bawah"
    if realization == budget:
        return "Pas"
    return "Melebihi"


def _divide(amount: int, divisor: int) -> int:
    return int((Decimal(amount) / divisor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
