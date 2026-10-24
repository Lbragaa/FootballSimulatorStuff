"""Incremental-signing payroll only, in integer cents; no invented base payroll."""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .state import ACCOUNT

POLICY_ID = "incremental_actual_days_month_end_v1"
POLICY = {
    "id": POLICY_ID,
    "coverage": "Only the five recorded Vasco signing contracts; untracked base-roster wages excluded",
    "proration": "Actual calendar days, inclusive contract start/end; round each obligation half-up to cents",
    "cash_timing": "Month-end due; August arrears paid at unchanged checkpoint date 2027-09-26",
    "accrual": "Through September 26 inclusive; no September cash before September 30",
    "legacy": "Preserve January-July aggregate cash debits, including simplified January; no retrospective reproration",
    "authority": "Annual commitments and approved transfer/wage budgets unchanged; emergency reserve untouched",
    "status": "proposed candidate policy, subject to commissioner acceptance",
}


def cents(value) -> int:
    return int((Decimal(str(value))*100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def prorate(monthly_cents: int, days: int, denominator: int) -> int:
    return int((Decimal(monthly_cents)*days/denominator).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def obligations(c, period: str, as_of: str) -> list[dict]:
    year, month = map(int, period.split("-"))
    first = date(year, month, 1)
    days = calendar.monthrange(year, month)[1]
    last = date(year, month, days)
    cutoff = date.fromisoformat(as_of[:10])
    rows = []
    for r in c.execute("""SELECT tc.* FROM transfer_contracts tc
        JOIN transfers t ON t.player_id=tc.player_id
        JOIN clubs cl ON cl.id=t.to_club
        WHERE cl.name='Vasco' AND t.status='completed' ORDER BY tc.player_id"""):
        start, end = max(first, date.fromisoformat(r["contract_start"])), min(last, date.fromisoformat(r["contract_end"]))
        if start > end:
            continue
        covered = (end-start).days+1
        accrued_days = max(0, (min(end, cutoff)-start).days+1)
        monthly = cents(r["wage_monthly_brl"])
        rows.append({"period": period, "player_id": r["player_id"], "covered_from": start.isoformat(),
                     "covered_to": end.isoformat(), "monthly_cents": monthly,
                     "due_cents": prorate(monthly, covered, days),
                     "accrued_cents": prorate(monthly, accrued_days, days)})
    return rows


def book_payroll(c, period: str, amount_cents: int, booked_on: str) -> tuple[int, bool]:
    """Idempotent cash posting inside caller's transaction on a scratch candidate.

    Period registration and cash are atomic. A raw duplicate legacy debit is
    rejected too, rather than being silently adopted as a second payment.
    """
    if not c.in_transaction:
        raise ValueError("Payroll booking requires an explicit candidate transaction")
    if amount_cents <= 0:
        raise ValueError("Payroll amount must be positive")
    old = c.execute("SELECT * FROM payroll_periods WHERE period=?", (period,)).fetchone()
    duplicate = c.execute("""SELECT l.id FROM finance_ledger l WHERE account=? AND category='incremental wage payroll'
        AND (substr(dated,1,7)=? OR description LIKE ?)
        AND NOT EXISTS(SELECT 1 FROM payroll_periods p WHERE p.ledger_id=l.id)""", (ACCOUNT, period, f"%{period}%")).fetchone()
    if duplicate:
        raise ValueError(f"Unregistered or duplicate payroll debit for {period}")
    if old and (old["account"] != ACCOUNT or old["policy_id"] != POLICY_ID):
        raise ValueError("Payroll obligation belongs to an incompatible account or policy")
    if old and old["ledger_id"] is not None:
        ledger = c.execute("SELECT * FROM finance_ledger WHERE id=?", (old["ledger_id"],)).fetchone()
        if (old["cash_cents"] != amount_cents or not ledger or cents(ledger["amount_brl"]) != -amount_cents
                or ledger["account"] != ACCOUNT or ledger["category"] != "incremental wage payroll"):
            raise ValueError(f"Conflicting payroll already recorded for {period}")
        return ledger["id"], False
    if old is None:
        raise ValueError("Register the contract-backed obligation before paying it")
    if old["amount_due_cents"] != amount_cents:
        raise ValueError("Payment differs from registered monthly obligation")
    year, month = map(int, period.split("-"))
    if date.fromisoformat(booked_on[:10]) < date(year, month, calendar.monthrange(year, month)[1]):
        raise ValueError("Payroll cash is due at month-end; cannot pay an unexpired period")
    cash = sum(cents(r[0]) for r in c.execute("SELECT amount_brl FROM finance_ledger WHERE account=?", (ACCOUNT,)))
    reserve = c.execute("SELECT amount_brl-spent_brl FROM finance_budget WHERE season=? AND category='Emergency reserve'", (year,)).fetchone()
    if reserve is None or cash-amount_cents < cents(reserve[0]):
        raise ValueError("Payment would consume the restricted emergency reserve")
    cur = c.execute("""INSERT INTO finance_ledger(dated,category,account,amount_brl,restricted_for,description,fictional)
        VALUES(?,?,?,?,?,?,1)""", (booked_on[:10], "incremental wage payroll", ACCOUNT, -amount_cents/100,
                                  "Incremental wages", f"{period}: arrears settled once; {POLICY_ID}; no annual-commitment cash duplication"))
    c.execute("UPDATE payroll_obligations SET accrued_cents=due_cents WHERE period=?", (period,))
    c.execute("UPDATE payroll_periods SET cash_cents=?,accrued_cents=amount_due_cents,ledger_id=?,status='paid' WHERE period=?",
              (amount_cents, cur.lastrowid, period))
    return cur.lastrowid, True


def financial_statement(c) -> dict:
    cash = sum(cents(r[0]) for r in c.execute("SELECT amount_brl FROM finance_ledger WHERE account=?", (ACCOUNT,)))
    annual = sum(cents(r[0]) for r in c.execute("SELECT annual_wage_commitment_brl FROM transfer_contracts"))
    periods = [dict(r) for r in c.execute("SELECT * FROM payroll_periods ORDER BY period")]
    liability = sum(r["accrued_cents"]-r["cash_cents"] for r in periods)
    return {"restricted_cash_cents": cash, "accrued_unpaid_cents": liability,
            "cash_less_recorded_incremental_liability_cents": cash-liability,
            "annual_incremental_commitments_cents": annual,
            "periods": periods, "policy": POLICY,
            "budgets": [dict(r, remaining_cents=cents(r["amount_brl"])-cents(r["spent_brl"]))
                        for r in c.execute("SELECT * FROM finance_budget ORDER BY id")]}
