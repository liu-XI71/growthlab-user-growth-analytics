from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GuardrailInput(BaseModel):
    name: str
    control_value: float
    treatment_value: float
    desired_direction: Literal["higher", "lower"] = "higher"
    tolerance: float = Field(default=0.0, ge=0)


class RoiInputs(BaseModel):
    active_days_30: float = Field(gt=0, le=30)
    daily_active_hours: float = Field(gt=0, le=24)
    value_per_hour: float = Field(gt=0)
    incentive_cost_per_acquisition: float = Field(gt=0)
    retention_discount: float = Field(default=1.0, ge=0, le=1)
    external_benchmark_ratio: float = Field(default=1.6, gt=0)


class RoiSensitivityRequest(BaseModel):
    base: RoiInputs
    variations: dict[str, list[float]] = Field(
        default_factory=lambda: {
            "active_days_30": [0.8, 1.2],
            "daily_active_hours": [0.8, 1.2],
            "value_per_hour": [0.8, 1.2],
            "incentive_cost_per_acquisition": [0.8, 1.2],
            "retention_discount": [0.85, 1.05],
        }
    )


class ExperimentAnalysisRequest(BaseModel):
    experiment_id: str | None = None
    control_successes: int | None = Field(default=None, ge=0)
    control_n: int | None = Field(default=None, gt=0)
    treatment_successes: int | None = Field(default=None, ge=0)
    treatment_n: int | None = Field(default=None, gt=0)
    objective: str | None = None
    strategy: str | None = None
    core_metric: str | None = None
    business_metric: str | None = None
    baseline_rate: float | None = Field(default=None, gt=0, lt=1)
    mde_absolute: float | None = Field(default=None, gt=0, lt=1)
    alpha: float = Field(default=0.05, gt=0, lt=1)
    power: float = Field(default=0.80, gt=0, lt=1)
    eligible_users_per_day: int = Field(default=10_000, gt=0)
    expected_treatment_ratio: float = Field(default=1.0, gt=0)
    minimum_full_weeks: int = Field(default=2, ge=1, le=12)
    observed_days: int | None = Field(
        default=None,
        ge=1,
        description="Completed experiment days. Required for an ad-hoc launch decision.",
    )
    guardrails: list[GuardrailInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source(self) -> ExperimentAnalysisRequest:
        counts = [
            self.control_successes,
            self.control_n,
            self.treatment_successes,
            self.treatment_n,
        ]
        if not self.experiment_id and any(value is None for value in counts):
            raise ValueError("Provide experiment_id or all four success/sample counts")
        if any(value is not None for value in counts) and any(value is None for value in counts):
            raise ValueError("When overriding counts, provide all four success/sample counts")
        if self.control_n is not None and self.control_successes is not None:
            if self.control_successes > self.control_n:
                raise ValueError("control_successes cannot exceed control_n")
        if self.treatment_n is not None and self.treatment_successes is not None:
            if self.treatment_successes > self.treatment_n:
                raise ValueError("treatment_successes cannot exceed treatment_n")
        return self


class FunnelStepInput(BaseModel):
    step: str = Field(min_length=1, max_length=80)
    baseline_uv: int = Field(ge=0)
    current_uv: int = Field(ge=0)


class FunnelWorkbenchRequest(BaseModel):
    steps: list[FunnelStepInput] = Field(min_length=2, max_length=20)
    material_threshold: float = Field(default=0.02, gt=0, lt=1)


class MixShiftRowInput(BaseModel):
    segment: str = Field(min_length=1, max_length=80)
    baseline_users: int = Field(ge=0)
    current_users: int = Field(ge=0)
    baseline_rate: float = Field(ge=0, le=1)
    current_rate: float = Field(ge=0, le=1)


class MixShiftWorkbenchRequest(BaseModel):
    rows: list[MixShiftRowInput] = Field(min_length=1, max_length=100)


class EconomicsScenarioRequest(BaseModel):
    experiment_id: str = Field(default="referral_ui_simplification", min_length=1, max_length=100)
    budget_multipliers: list[float] = Field(
        default_factory=lambda: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
        min_length=2,
        max_length=30,
    )
    response_elasticity: float = Field(default=0.82, gt=0, le=1)
    eligible_population: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Optional explicit planning population. If omitted, results stay normalized per 10k "
            "and are not silently extrapolated."
        ),
    )

    @model_validator(mode="after")
    def validate_multipliers(self) -> EconomicsScenarioRequest:
        if any(value <= 0 or value > 10 for value in self.budget_multipliers):
            raise ValueError("budget_multipliers must be in (0, 10]")
        if len(set(self.budget_multipliers)) != len(self.budget_multipliers):
            raise ValueError("budget_multipliers must be unique")
        return self
