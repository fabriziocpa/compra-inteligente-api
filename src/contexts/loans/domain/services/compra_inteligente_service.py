"""Cronograma «Compra Inteligente» estilo Interbank (crédito con cuota balón).

Procedimiento (hoja «06 - Planes de Pago - Ordinario - Compra Inteligente IB»)
==============================================================================
La modalidad combina tres pagos:

* Una *cuota inicial* CI = precio × %inicial, pagada en t=0.
* ``N`` cuotas francesas regulares al vencimiento de cada período.
* Una *cuota final* (balón o «cuotón») CF = precio × %final, pagada en un
  período EXTRA ``N+1``.

El monto del préstamo incluye los costes iniciales financiados::

    Prestamo = PV − CI + costes financiados

El cuotón se separa en su propio sub-cronograma: su saldo inicial es el valor
presente de CF descontado a la tasa del período MÁS el desgravamen::

    SICF₁ = CF / Π_{k=1..N+1} (1 + TEP_k + pSegDesPer)

Ese saldo capitaliza interés y desgravamen cada período (no se amortiza) y se
paga íntegro (= CF) en el período N+1. El resto del préstamo::

    Saldo = Prestamo − SICF₁

se amortiza con el método francés en N cuotas. El seguro de desgravamen va
DENTRO de la anualidad («Cuota inc Seg Des»)::

    Cuota_k = PMT(TEP_k + pSegDesPer, N−k+1, SI_k)
    Amortización_k = Cuota_k − Interés_k − SegDes_k

La cuota se recalcula cada fila sobre el saldo vigente, así que tras un
período de gracia o un cambio de tasa se ajusta sola.

Períodos de gracia (solo afectan al cronograma regular; el cuotón siempre
capitaliza):

* ``T`` (total):   cuota 0; capitaliza SOLO el interés (``SF = SI×(1+TEP)``);
                   el desgravamen del período se paga en efectivo.
* ``P`` (parcial): se paga el interés (cuota = interés) y el desgravamen en
                   efectivo; el saldo no baja.
* ``S`` (normal):  cuota francesa completa (incluye desgravamen).

Convención de signos de la metodología: interés, cuota, amortización y
desgravamen NEGATIVOS (egresos del deudor); saldos positivos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.contexts.loans.domain.services.french_amortization_service import (
    SchedulePeriodInput,
    ScheduleRow,
)
from src.shared.domain.exceptions import DomainError

_ZERO = Decimal(0)
_ONE = Decimal(1)
_CLOSE_TOL = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CompraInteligenteSchedule:
    """Resultado del plan: CI, balón, montos y filas del cronograma.

    * ``amount_financed`` — Prestamo = PV − CI + costes financiados.
    * ``balloon_present_value`` — SICF₁, saldo inicial del cuotón.
    * ``regular_principal`` — Saldo financiado con las cuotas regulares.
    * ``rows`` — N filas regulares, más la fila N+1 del cuotón si hay balón.
    """

    initial_payment: Decimal
    balloon: Decimal
    amount_financed: Decimal
    balloon_present_value: Decimal
    regular_principal: Decimal
    rows: list[ScheduleRow]


def _pmt(balance: Decimal, rate: Decimal, periods_remaining: int) -> Decimal:
    """Cuota francesa (negativa): PMT(tasa, n, saldo). Con tasa 0, saldo/n."""
    if rate == _ZERO:
        return -(balance / Decimal(periods_remaining))
    one_plus = _ONE + rate
    factor = one_plus**periods_remaining
    return -(balance * rate * factor / (factor - _ONE))


class CompraInteligenteService:
    @staticmethod
    def build_schedule(
        vehicle_price: Decimal,
        initial_payment_pct: Decimal,
        balloon_pct: Decimal,
        periods: list[SchedulePeriodInput],
        financed_costs: Decimal = _ZERO,
        desgravamen_pct_per_period: Decimal = _ZERO,
    ) -> CompraInteligenteSchedule:
        if vehicle_price <= _ZERO:
            raise DomainError("vehicle_price must be positive")
        if not (_ZERO <= initial_payment_pct < _ONE):
            raise DomainError("initial_payment_pct must be in [0, 1)")
        if not (_ZERO <= balloon_pct < _ONE):
            raise DomainError("balloon_pct must be in [0, 1)")
        if initial_payment_pct + balloon_pct >= _ONE:
            raise DomainError("initial_payment_pct + balloon_pct must be < 1")
        if not periods:
            raise DomainError("periods must not be empty")
        if financed_costs < _ZERO:
            raise DomainError("financed_costs must be >= 0")
        if not (_ZERO <= desgravamen_pct_per_period < _ONE):
            raise DomainError("desgravamen_pct_per_period must be in [0, 1)")

        n = len(periods)
        seg = desgravamen_pct_per_period
        ci = vehicle_price * initial_payment_pct
        cf = vehicle_price * balloon_pct
        prestamo = vehicle_price - ci + financed_costs

        has_balloon = cf > _ZERO
        if has_balloon and periods[-1].grace_type != "S":
            raise DomainError(
                "Final period must not be in grace for Compra Inteligente"
            )

        # VP del cuotón: N+1 factores (1 + TEP_k + pSegDesPer); el período
        # N+1 usa la TEP del último tramo.
        if has_balloon:
            discount = _ONE
            for p in periods:
                discount *= _ONE + p.tep + seg
            discount *= _ONE + periods[-1].tep + seg
            sicf = cf / discount
        else:
            sicf = _ZERO

        saldo = prestamo - sicf
        if saldo <= _ZERO:
            raise DomainError("Balloon too large relative to amount financed")

        # --- Cronograma regular (francés con desgravamen en la anualidad) ---
        rows: list[ScheduleRow] = []
        si = saldo
        cuoton = sicf
        for idx, p in enumerate(periods, start=1):
            interest = -(si * p.tep)
            insurance = -(si * seg)

            if p.grace_type == "T":
                payment = _ZERO
                amortization = _ZERO
                sf = si * (_ONE + p.tep)
            elif p.grace_type == "P":
                payment = interest
                amortization = _ZERO
                sf = si
            else:
                payment = _pmt(si, p.tep + seg, n - idx + 1)
                amortization = payment - interest - insurance
                sf = si + amortization

            # Sub-cronograma del cuotón: capitaliza interés + desgravamen.
            b_interest = -(cuoton * p.tep)
            b_insurance = -(cuoton * seg)
            b_final = cuoton - b_interest - b_insurance

            rows.append(
                ScheduleRow(
                    period=p.period_number,
                    grace_type=p.grace_type,
                    initial_balance=si,
                    interest=interest,
                    payment=payment,
                    amortization=amortization,
                    final_balance=sf,
                    insurance=insurance,
                    balloon_initial=cuoton,
                    balloon_interest=b_interest,
                    balloon_insurance=b_insurance,
                    balloon_amortization=_ZERO,
                    balloon_final=b_final,
                )
            )
            si = sf
            cuoton = b_final

        # Verificación de cierre del saldo regular (solo si el último período
        # amortiza; con gracia final el plan queda abierto a propósito).
        if periods[-1].grace_type == "S" and abs(si) > _CLOSE_TOL:
            raise DomainError(
                f"Regular balance does not close to zero: {si}"
            )

        # --- Período N+1: pago del cuotón (con los cargos del período) ---
        if has_balloon:
            tep_last = periods[-1].tep
            b_interest = -(cuoton * tep_last)
            b_insurance = -(cuoton * seg)
            # ACF = −(SICF + |ICF| + |SegDesCF|) = −CF exactamente.
            b_amort = -(cuoton - b_interest - b_insurance)
            rows.append(
                ScheduleRow(
                    period=n + 1,
                    grace_type="S",
                    initial_balance=_ZERO,
                    interest=_ZERO,
                    payment=_ZERO,
                    amortization=_ZERO,
                    final_balance=_ZERO,
                    insurance=_ZERO,
                    balloon_initial=cuoton,
                    balloon_interest=b_interest,
                    balloon_insurance=b_insurance,
                    balloon_amortization=b_amort,
                    balloon_final=cuoton - b_interest - b_insurance + b_amort,
                )
            )

        return CompraInteligenteSchedule(
            initial_payment=ci,
            balloon=cf,
            amount_financed=prestamo,
            balloon_present_value=sicf,
            regular_principal=saldo,
            rows=rows,
        )
