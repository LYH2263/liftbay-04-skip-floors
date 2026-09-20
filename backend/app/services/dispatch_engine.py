"""Elevator dispatch: same-direction preference + floor distance; reject if car full."""

from __future__ import annotations

from dataclasses import dataclass

REASON_OK = "ok"
REASON_FULL = "轿厢满员"
REASON_BLOCKED = "禁停层"


@dataclass(frozen=True)
class CarState:
    car_id: int
    floor: int
    direction: str  # "up" | "down" | "idle"
    load: int
    capacity: int


@dataclass(frozen=True)
class CallRequest:
    call_id: int
    floor: int
    direction: str  # desired travel after boarding
    passengers: int = 1


@dataclass(frozen=True)
class ScoreResult:
    car_id: int
    score: float
    accepted: bool
    reason: str


@dataclass(frozen=True)
class PickOutcome:
    result: ScoreResult | None
    reason: str  # REASON_OK | REASON_BLOCKED | REASON_FULL


SAME_DIR_BONUS = 40.0
IDLE_BONUS = 20.0
DISTANCE_WEIGHT = 5.0


def score_car(car: CarState, call: CallRequest) -> ScoreResult:
    if car.load + call.passengers > car.capacity:
        return ScoreResult(car.car_id, -1e9, False, REASON_FULL)

    distance = abs(car.floor - call.floor)
    score = 100.0 - distance * DISTANCE_WEIGHT

    if car.direction == "idle":
        score += IDLE_BONUS
    elif car.direction == call.direction:
        # approaching or already going same way
        if car.direction == "up" and car.floor <= call.floor:
            score += SAME_DIR_BONUS
        elif car.direction == "down" and car.floor >= call.floor:
            score += SAME_DIR_BONUS
        else:
            score -= 15.0  # same dir but already passed
    else:
        score -= 25.0

    return ScoreResult(car.car_id, score, True, REASON_OK)


def evaluate(
    cars: list[CarState],
    call: CallRequest,
    blocked_floors: frozenset[int] | set[int] | tuple[int, ...] = frozenset(),
) -> PickOutcome:
    # A blocked floor can never be a waiting/drop-off floor; short-circuit
    # before capacity so a car is never sent to stop there.
    if call.floor in blocked_floors:
        return PickOutcome(None, REASON_BLOCKED)

    results = [score_car(c, call) for c in cars]
    accepted = [r for r in results if r.accepted]
    if not accepted:
        return PickOutcome(None, REASON_FULL)
    return PickOutcome(max(accepted, key=lambda r: r.score), REASON_OK)


def pick_car(
    cars: list[CarState],
    call: CallRequest,
    blocked_floors: frozenset[int] | set[int] | tuple[int, ...] = frozenset(),
) -> ScoreResult | None:
    return evaluate(cars, call, blocked_floors).result


def congestion_by_floor(calls: list[CallRequest]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for c in calls:
        counts[c.floor] = counts.get(c.floor, 0) + c.passengers
    return counts
