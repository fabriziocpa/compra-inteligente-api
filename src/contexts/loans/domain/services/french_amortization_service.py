"""Método francés «vencido ordinario» (Unidad 3 — Planes de pago).

Procedimiento de la metodología
===============================
El préstamo ``C`` se paga en ``n`` cuotas vencidas iguales ``R``. Con la tasa
efectiva del período ``i`` (TEP), la cuota sale de igualar el valor presente
de la anualidad al principal::

    R = C * [ i(1+i)^n ] / [ (1+i)^n - 1 ]        (equivale a  R = C / a(n,i))

Cada período se descompone así (meses de 30 días, año de 360):

1. Interés del período:      I_k = SI_k * TEP      (SI = saldo inicial)
2. Amortización de capital:  A_k = R - I_k
3. Saldo final:              SF_k = SI_k + A_k     (con signos, A_k es negativo)

Períodos de gracia
------------------
* ``T`` (total):   no se paga nada. El interés se CAPITALIZA al saldo:
                   ``SF = SI * (1 + TEP)``; cuota y amortización son 0.
* ``P`` (parcial): se paga SOLO el interés (``cuota = interés``); no se
                   amortiza capital, así que ``SF = SI``.
* ``S`` (normal):  cuota francesa completa.

Recálculo de la cuota
---------------------
La cuota deja de ser válida cuando cambia la TEP (tasa variable) o cuando el
período anterior fue de gracia (el saldo ya no siguió la trayectoria prevista).
En ese caso se recalcula sobre el saldo vigente y los períodos que faltan::

    R = SI * [ TEP(1+TEP)^(n-k+1) ] / [ (1+TEP)^(n-k+1) - 1 ]

donde ``k`` es el período actual (quedan ``n-k+1`` cuotas por pagar).

Convención de signos: interés, cuota y amortización son NEGATIVOS
(egresos del deudor), igual que en la separata del curso.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

GraceType = Literal["T", "P", "S"]


@dataclass(frozen=True, slots=True)
class SchedulePeriodInput:
    """Datos de entrada de un período: número, TEP vigente y tipo de gracia."""

    period_number: int
    tep: Decimal
    grace_type: GraceType


@dataclass(frozen=True, slots=True)
class ScheduleRow:
    """Fila calculada del plan de pagos (saldos, interés, cuota, amortización)."""

    period: int
    grace_type: str
    initial_balance: Decimal
    interest: Decimal
    payment: Decimal
    amortization: Decimal
    final_balance: Decimal


def _french_payment(balance: Decimal, tep: Decimal, periods_remaining: int) -> Decimal:
    """Cuota francesa (negativa) para ``periods_remaining`` períodos.

    Implementa R = saldo / a(n, i), donde a(n, i) = [(1+i)^n - 1] / [i(1+i)^n]
    es el factor de actualización de la serie uniforme.
    """
    one_plus_tep = Decimal(1) + tep
    factor = one_plus_tep**periods_remaining
    annuity = (factor - Decimal(1)) / (tep * factor)
    return -(balance / annuity)


class FrenchAmortizationService:
    """Servicio de dominio puro: sin I/O ni base de datos.

    La abstracción recibe el principal y la lista de períodos ya resuelta
    (cada uno con su TEP y su tipo de gracia) y devuelve el plan fila por
    fila. Las conversiones de tasa y la política de gracia se resuelven
    antes, en ``InterestRateSpec`` y ``GracePeriodPolicy``.
    """

    @staticmethod
    def build_schedule(
        principal: Decimal,
        periods: list[SchedulePeriodInput],
    ) -> list[ScheduleRow]:
        if principal <= Decimal(0):
            raise ValueError("principal must be positive")
        if not periods:
            raise ValueError("periods must not be empty")

        n = len(periods)
        rows: list[ScheduleRow] = []
        si = principal
        current_r: Decimal | None = None
        prev_tep: Decimal | None = None
        prev_grace: GraceType | None = None

        for idx, p in enumerate(periods, start=1):
            # La cuota se (re)calcula al inicio, si cambió la TEP o si el
            # período anterior fue de gracia (el saldo se desvió del plan).
            recompute = (
                current_r is None
                or (prev_tep is not None and p.tep != prev_tep)
                or prev_grace in ("T", "P")
            )

            if p.grace_type == "S" and recompute:
                remaining = n - idx + 1
                current_r = _french_payment(si, p.tep, remaining)

            interest = -(si * p.tep)

            if p.grace_type == "T":
                # Gracia total: el interés se capitaliza al saldo.
                payment = Decimal(0)
                amortization = Decimal(0)
                sf = si * (Decimal(1) + p.tep)
            elif p.grace_type == "P":
                # Gracia parcial: se paga solo el interés; el saldo no baja.
                payment = interest
                amortization = Decimal(0)
                sf = si
            elif p.grace_type == "S":
                assert current_r is not None
                payment = current_r
                amortization = payment - interest
                sf = si + amortization
            else:
                raise ValueError(f"Unknown grace_type: {p.grace_type}")

            rows.append(
                ScheduleRow(
                    period=p.period_number,
                    grace_type=p.grace_type,
                    initial_balance=si,
                    interest=interest,
                    payment=payment,
                    amortization=amortization,
                    final_balance=sf,
                )
            )

            si = sf
            prev_tep = p.tep
            prev_grace = p.grace_type

        return rows
