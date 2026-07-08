"""Agregado Préstamo (simulación de crédito vehicular).

Ciclo de vida: ``draft`` (creado, sin cronograma) → ``scheduled`` (cronograma
calculado y persistido). Al editar los parámetros el cronograma queda obsoleto,
así que se descarta y el préstamo vuelve a ``draft`` hasta recalcular.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from src.contexts.loans.domain.entities.payment_schedule_entry import PaymentScheduleEntry
from src.contexts.loans.domain.events import LoanCreated, LoanUpdated, ScheduleGenerated
from src.contexts.loans.domain.value_objects.additional_charge import AdditionalCharge
from src.contexts.loans.domain.value_objects.grace_period_policy import GracePeriodPolicy
from src.contexts.loans.domain.value_objects.initial_cost import InitialCost
from src.contexts.loans.domain.value_objects.interest_rate_spec import InterestRateSpec
from src.contexts.loans.domain.value_objects.loan_terms import LoanTerms
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import DomainError

LoanStatus = Literal["draft", "scheduled", "active", "cancelled"]


def _validate_terms(terms: LoanTerms, rate_spec: InterestRateSpec) -> None:
    """Invariantes del préstamo (se aplican al crear y al editar)."""
    if terms.term_periods <= 0:
        raise DomainError("term_periods must be positive")
    if terms.frequency_days <= 0:
        raise DomainError("frequency_days must be positive")
    if not (Decimal(0) <= terms.initial_payment_pct < Decimal(1)):
        raise DomainError("initial_payment_pct out of range")
    if not (Decimal(0) <= terms.balloon_pct < Decimal(1)):
        raise DomainError("balloon_pct out of range")
    if terms.initial_payment_pct + terms.balloon_pct >= Decimal(1):
        raise DomainError("initial_payment_pct + balloon_pct must be < 1")
    if terms.financed_costs < Decimal(0):
        raise DomainError("financed_costs must be >= 0")
    if not (Decimal(0) <= terms.desgravamen_monthly_pct < Decimal(1)):
        raise DomainError("desgravamen_monthly_pct out of range")
    if terms.frequency_days != rate_spec.days_in_period:
        raise DomainError("rate_spec.days_in_period must equal terms.frequency_days")


def _validate_initial_costs(costs: tuple[InitialCost, ...]) -> None:
    for c in costs:
        if not c.name.strip():
            raise DomainError("initial cost name must not be empty")
        if c.amount < Decimal(0):
            raise DomainError("initial cost amount must be >= 0")


@dataclass(eq=False)
class Loan(AggregateRoot):
    client_id: UUID = field(default_factory=uuid4)
    vehicle_id: UUID = field(default_factory=uuid4)
    terms: LoanTerms = None  # type: ignore[assignment]
    rate_spec: InterestRateSpec = None  # type: ignore[assignment]
    grace_policy: GracePeriodPolicy = field(default_factory=GracePeriodPolicy)
    additional_charges: tuple[AdditionalCharge, ...] = ()
    # Desglose de los costos/gastos iniciales (financiados o al contado).
    # La suma de los financiados debe coincidir con terms.financed_costs.
    initial_costs: tuple[InitialCost, ...] = ()
    status: LoanStatus = "draft"
    schedule: tuple[PaymentScheduleEntry, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        client_id: UUID,
        vehicle_id: UUID,
        terms: LoanTerms,
        rate_spec: InterestRateSpec,
        grace_policy: GracePeriodPolicy | None = None,
        additional_charges: tuple[AdditionalCharge, ...] = (),
        initial_costs: tuple[InitialCost, ...] = (),
    ) -> Loan:
        _validate_terms(terms, rate_spec)
        _validate_initial_costs(initial_costs)

        now = datetime.now(UTC)
        loan = cls(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            client_id=client_id,
            vehicle_id=vehicle_id,
            terms=terms,
            rate_spec=rate_spec,
            grace_policy=grace_policy or GracePeriodPolicy(),
            additional_charges=additional_charges,
            initial_costs=initial_costs,
            status="draft",
            schedule=(),
        )
        loan.record_event(LoanCreated(loan_id=loan.id))
        return loan

    def update_parameters(
        self,
        *,
        terms: LoanTerms | None = None,
        rate_spec: InterestRateSpec | None = None,
        grace_policy: GracePeriodPolicy | None = None,
        additional_charges: tuple[AdditionalCharge, ...] | None = None,
        initial_costs: tuple[InitialCost, ...] | None = None,
    ) -> None:
        """Edita los parámetros y descarta el cronograma obsoleto.

        Tras editar hay que volver a generar el cronograma (POST /schedule);
        por eso el estado regresa a ``draft``.
        """
        new_terms = terms if terms is not None else self.terms
        new_spec = rate_spec if rate_spec is not None else self.rate_spec
        # Si cambia la frecuencia sin nuevos tramos, la TEP debe recalcularse
        # con los días del nuevo período.
        if new_spec.days_in_period != new_terms.frequency_days:
            new_spec = replace(new_spec, days_in_period=new_terms.frequency_days)
        _validate_terms(new_terms, new_spec)

        self.terms = new_terms
        self.rate_spec = new_spec
        if grace_policy is not None:
            self.grace_policy = grace_policy
        if additional_charges is not None:
            self.additional_charges = additional_charges
        if initial_costs is not None:
            _validate_initial_costs(initial_costs)
            self.initial_costs = initial_costs
        self.schedule = ()
        self.status = "draft"
        self.touch()
        self.record_event(LoanUpdated(loan_id=self.id))

    def set_schedule(self, entries: list[PaymentScheduleEntry]) -> None:
        if not entries:
            raise DomainError("schedule must not be empty")
        # Con cuota balón, el plan Interbank agrega el período N+1 en el que
        # se paga el cuotón.
        expected = self.terms.term_periods + (1 if self.terms.is_compra_inteligente else 0)
        if len(entries) != expected:
            raise DomainError(
                f"schedule has {len(entries)} rows but {expected} were expected"
            )
        self.schedule = tuple(entries)
        self.status = "scheduled"
        self.touch()
        self.record_event(ScheduleGenerated(loan_id=self.id, rows=len(entries)))
