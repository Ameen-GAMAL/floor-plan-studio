"""Versioned contracts. Dimensions are integer millimetres; areas are m²."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Rect(Contract):
    x1: StrictInt
    y1: StrictInt
    x2: StrictInt
    y2: StrictInt

    @model_validator(mode="after")
    def positive(self):
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Rectangle needs x2 > x1 and y2 > y1.")
        return self


class Floor(Contract):
    width_mm: StrictInt = Field(gt=0, le=40000)
    depth_mm: StrictInt = Field(gt=0, le=30000)
    external_wall_mm: StrictInt = Field(default=200, gt=0, le=500)
    internal_wall_mm: StrictInt = Field(default=100, gt=0, le=300)
    source_status: Literal["assumed", "measured"] = "assumed"
    source_note: str = Field(default="Synthetic presentation brief; verify on site.", max_length=500)


class Opening(Rect):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")


class FixedGeometry(Contract):
    corridor: Rect
    core: Rect
    exterior_openings: list[Opening] = Field(min_length=1, max_length=4)
    other_obstructions: list[Rect] = Field(default_factory=list, max_length=20)


class RoomSpec(Contract):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")
    name: str = Field(min_length=1, max_length=60)
    kind: Literal["reception", "workroom", "office", "meeting"]
    capacity: StrictInt = Field(ge=1, le=6)
    min_area_m2: float = Field(gt=0, le=10000)
    target_area_m2: float = Field(gt=0, le=10000)
    max_area_m2: float | None = Field(default=None, gt=0, le=10000)

    @model_validator(mode="after")
    def supported_capacity_and_bounds(self):
        allowed = {"reception": [1], "office": [1], "workroom": [2, 4, 6], "meeting": [4, 6]}
        if self.capacity not in allowed[self.kind]:
            raise ValueError(f"{self.kind} capacity must be one of {allowed[self.kind]}.")
        if self.max_area_m2 is not None and self.min_area_m2 > self.max_area_m2:
            raise ValueError(f"{self.name}: minimum area exceeds maximum area. Edit those bounds explicitly.")
        return self


class Relationship(Contract):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,49}$")
    a: str
    b: str
    kind: Literal["wall_adjacent", "door_connected", "near"]
    mandatory: bool = True


class DesignRules(Contract):
    grid_mm: StrictInt = Field(default=50, ge=10, le=100)
    min_short_side_mm: StrictInt = Field(default=3200, ge=1000, le=10000)
    max_aspect_ratio: float = Field(default=3, ge=1, le=6)
    min_aperture_mm: StrictInt = Field(default=900, ge=600, le=2000)
    min_corridor_mm: StrictInt = Field(default=1800, ge=600, le=4000)


class SolverSettings(Contract):
    time_limit_seconds: float = Field(default=25, ge=0, le=25)
    seed: StrictInt = 20261015


class Brief(Contract):
    schema_version: Literal["1.0"]
    revision: StrictInt = Field(ge=1)
    units: Literal["mm"]
    building_use: Literal["small_office"]
    project_name: str = Field(default="Small office study", min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    floor: Floor
    fixed: FixedGeometry
    rooms: list[RoomSpec] = Field(min_length=4, max_length=7)
    relationships: list[Relationship] = Field(default_factory=list, max_length=10)
    priority: Literal["area", "balanced", "privacy"] = "balanced"
    rules: DesignRules = Field(default_factory=DesignRules)
    solver: SolverSettings = Field(default_factory=SolverSettings)

    @model_validator(mode="after")
    def program(self):
        ids = [r.id for r in self.rooms]
        if len(ids) != len(set(ids)) or any(i in {"corridor", "core", "outside"} for i in ids):
            raise ValueError("Room IDs must be unique and cannot use corridor, core or outside.")
        counts = {k: sum(r.kind == k for r in self.rooms) for k in ["reception", "workroom", "meeting", "office"]}
        if any(counts[k] != 1 for k in ["reception", "workroom", "meeting"]) or not 1 <= counts["office"] <= 4:
            raise ValueError("The program needs one reception, workroom and meeting room, plus one to four offices.")
        relids = [r.id for r in self.relationships]
        if len(relids) != len(set(relids)):
            raise ValueError("Relationship IDs must be unique.")
        for rel in self.relationships:
            if rel.a not in ids or rel.b not in ids or rel.a == rel.b:
                raise ValueError(f"{rel.id}: select two different existing rooms.")
        openingids = [o.id for o in self.fixed.exterior_openings]
        if len(openingids) != len(set(openingids)):
            raise ValueError("Exterior opening IDs must be unique.")
        return self


def brief_hash(brief: Brief) -> str:
    payload = json.dumps(brief.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PolygonItem(Contract):
    id: str
    polygon: list[tuple[StrictInt, StrictInt]] = Field(min_length=4)


class Space(PolygonItem):
    name: str
    kind: str
    capacity: StrictInt = 0


class Door(PolygonItem):
    connects: tuple[str, str]


class Furniture(PolygonItem):
    room_id: str
    kind: str
    label: str


class Layout(Contract):
    schema_version: Literal["1.0"] = "1.0"
    units: Literal["mm"] = "mm"
    brief_revision: StrictInt
    brief_hash: str
    grid_mm: StrictInt
    model_version: str
    rooms: list[Space]
    corridor: Space
    core: Space
    walls: list[PolygonItem]
    doors: list[Door]
    furniture: list[Furniture]
    metadata: dict[str, Any]


class Check(Contract):
    id: str
    description: str
    source: str
    provenance: Literal["user", "design_assumption", "derived", "not_selected"]
    classification: Literal["hard", "soft", "review"] = "hard"
    units: str
    expected: Any
    measured: Any = None
    tolerance: Any = 0
    status: Literal["pass", "fail", "unverified"]
    implementation_status: Literal["implemented", "not_implemented"] = "implemented"
    validation_procedure: str
    scope: str = "Exported two-dimensional geometry"
    geometry_ids: list[str] = Field(default_factory=list)


class Report(Contract):
    validator_version: str
    brief_revision: StrictInt
    brief_hash: str
    validation_status: Literal["passed", "failed", "unverified"]
    regulatory_status: Literal["unverified"] = "unverified"
    scope: str
    checks: list[Check]
    area_ledger_m2: dict[str, float]
    room_schedule: list[dict[str, Any]]
    connectivity_edges: list[tuple[str, str]]


class GenerateResult(Contract):
    search_status: Literal["feasible", "infeasible", "unknown", "invalid_input", "unsupported", "error"]
    optimality: Literal["proven", "not_proven"] = "not_proven"
    validation_status: Literal["passed", "failed", "unverified", "not_run"] = "not_run"
    regulatory_status: Literal["unverified"] = "unverified"
    brief_revision: int
    brief_hash: str
    brief: Brief
    message: str
    explanation: dict[str, Any] | None = None
    layout: Layout | None = None
    report: Report | None = None
    svg: str | None = None
    elapsed_seconds: float = 0


class ValidationRequest(Contract):
    brief: Brief
    layout: Layout
