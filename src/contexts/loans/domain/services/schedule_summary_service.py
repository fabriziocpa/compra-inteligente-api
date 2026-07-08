"""Resumen «Resultados» del plan de pagos (bloque de resultados de la hoja).

Se calcula en el servidor con ``Decimal`` para que el frontend NO haga ningún
cálculo financiero: solo renderiza. Reproduce la estructura jerárquica de la
hoja del curso:

* **… del financiamiento**: TEA/TEP del primer tramo, cuotas por año y
  totales, cuota inicial (CI), cuota final (CF), monto del préstamo
  (Prestamo = PV − CI + costes financiados) y saldo a financiar con cuotas.
* **… de los costes/gastos periódicos**: % de desgravamen del período y el
  importe por período de cada cargo (en su primer período de aplicación).
* **… totales por concepto** (fórmulas de la hoja, en positivo):

    - Intereses = Σ|Cuota| − Σ|Amortización| − Σ|SegDes|  (el interés pagado
      DENTRO de las cuotas; el cuotón se netea porque su pago = ACF).
    - Amortización del capital = Σ|Amortización| + Σ|ACF|  (incluye el
      interés capitalizado en gracia total y en el cuotón).
    - Seguro de desgravamen = Σ|SegDes| del cronograma regular.
    - Un total por cada cargo adicional (GPS, portes, seguros…).

* **Pie de tabla**: la suma CON SIGNO de cada columna monetaria, para la
  fila «Totales» del cronograma.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.contexts.loans.domain.entities.loan import Loan
from src.contexts.loans.domain.services.rate_converter import (
    tea_from_tna_nominal,
    tep_from_tea,
)
from src.contexts.loans.domain.value_objects.initial_cost import cash_total
from src.shared.domain.exceptions import DomainError

_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class ChargeSummaryItem:
    """Cargo con su importe (positivo): por período o total, según contexto."""

    name: str
    kind: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ColumnTotals:
    """Suma con signo de cada columna monetaria (fila «Totales» de la tabla)."""

    interest: Decimal
    payment: Decimal
    amortization: Decimal
    insurance: Decimal
    balloon_amortization: Decimal
    charges: Decimal
    total_payment: Decimal


@dataclass(frozen=True, slots=True)
class ScheduleSummary:
    # … del financiamiento
    tea: Decimal
    tep: Decimal
    payments_per_year: int
    total_payments: int
    initial_payment: Decimal
    balloon: Decimal
    # Costos iniciales: financiados (dentro del préstamo) y al contado
    # (informativos: se pagan aparte en el desembolso).
    financed_costs: Decimal
    cash_costs: Decimal
    loan_principal: Decimal
    regular_principal: Decimal
    balloon_present_value: Decimal
    regular_payment: Decimal
    balloon_payment: Decimal
    has_balloon: bool
    # … de los costes/gastos periódicos
    desgravamen_pct_per_period: Decimal
    periodic_charges: list[ChargeSummaryItem]
    # … totales por concepto (positivos)
    total_interest: Decimal
    total_amortization: Decimal
    total_insurance: Decimal
    total_charges: list[ChargeSummaryItem]
    # pie de tabla (con signo)
    column_totals: ColumnTotals


class ScheduleSummaryService:
    @staticmethod
    def summarize(loan: Loan) -> ScheduleSummary:
        if not loan.schedule:
            raise DomainError("Loan has no schedule. Run /schedule first.")

        terms = loan.terms
        rows = loan.schedule

        # TEA/TEP del primer tramo (la hoja usa una sola tasa; con tasa
        # variable el resumen muestra el tramo 1).
        seg = loan.rate_spec.segments[0]
        if seg.rate_kind == "TNA":
            if seg.capitalizations_per_year is None:
                raise DomainError("TNA segment requires capitalizations_per_year")
            tea = tea_from_tna_nominal(seg.rate_value, seg.capitalizations_per_year)
        else:
            tea = seg.rate_value
        tep = tep_from_tea(tea, terms.frequency_days)

        initial_payment = terms.vehicle_price * terms.initial_payment_pct
        balloon = terms.vehicle_price * terms.balloon_pct
        balloon_present_value = rows[0].balloon_initial
        regular_principal = rows[0].initial_balance
        has_balloon = balloon_present_value != _ZERO

        # Cuota regular vigente: la del último período que amortiza (S); con
        # recálculo por fila es la cuota constante del tramo final del plan.
        regular_payment = next(
            (abs(r.payment) for r in reversed(rows) if r.grace_type == "S" and r.payment != _ZERO),
            _ZERO,
        )
        balloon_payment = abs(rows[-1].balloon_amortization) if has_balloon else _ZERO

        # Sumas de columnas (con signo, para el pie de tabla).
        col = ColumnTotals(
            interest=sum((r.interest for r in rows), _ZERO),
            payment=sum((r.payment for r in rows), _ZERO),
            amortization=sum((r.amortization for r in rows), _ZERO),
            insurance=sum((r.insurance for r in rows), _ZERO),
            balloon_amortization=sum((r.balloon_amortization for r in rows), _ZERO),
            charges=sum((r.charges_total for r in rows), _ZERO),
            total_payment=sum((r.total_payment for r in rows), _ZERO),
        )

        # Totales por concepto (fórmulas de la hoja, ver docstring del módulo).
        total_insurance = abs(col.insurance)
        total_interest = abs(col.payment) - abs(col.amortization) - total_insurance
        total_amortization = abs(col.amortization) + abs(col.balloon_amortization)

        # Cargos: importe del primer período en que aplica cada uno, y total
        # acumulado por nombre (en orden de aparición).
        periodic: dict[str, ChargeSummaryItem] = {}
        totals: dict[str, ChargeSummaryItem] = {}
        for r in rows:
            for c in r.charges:
                amount = abs(c.amount)
                if c.name not in periodic:
                    periodic[c.name] = ChargeSummaryItem(c.name, c.kind, amount)
                prev = totals.get(c.name)
                totals[c.name] = ChargeSummaryItem(
                    c.name, c.kind, (prev.amount if prev else _ZERO) + amount
                )

        return ScheduleSummary(
            tea=tea,
            tep=tep,
            payments_per_year=round(360 / terms.frequency_days),
            total_payments=terms.term_periods,
            initial_payment=initial_payment,
            balloon=balloon,
            financed_costs=terms.financed_costs,
            cash_costs=cash_total(loan.initial_costs),
            loan_principal=terms.loan_principal,
            regular_principal=regular_principal,
            balloon_present_value=balloon_present_value,
            regular_payment=regular_payment,
            balloon_payment=balloon_payment,
            has_balloon=has_balloon,
            desgravamen_pct_per_period=terms.desgravamen_pct_per_period,
            periodic_charges=list(periodic.values()),
            total_interest=total_interest,
            total_amortization=total_amortization,
            total_insurance=total_insurance,
            total_charges=list(totals.values()),
            column_totals=col,
        )
