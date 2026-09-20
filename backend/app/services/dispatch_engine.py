"""Elevator dispatch: same-direction preference + floor distance; reject if full or banned."""

from __future__ import annotations

from dataclasses import dataclass


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


SAME_DIR_BONUS = 40.0
IDLE_BONUS = 20.0
DISTANCE_WEIGHT = 5.0

REASON_FULL = "轿厢满员"
REASON_RESTRICTED = "目的层禁停"


def score_car(
    car: CarState,
    call: CallRequest,
    banned_floors: frozenset[int] = frozenset(),
) -> ScoreResult:
    # 满员与禁停各自独立给出原因，文案互不覆盖。
    full = car.load + call.passengers > car.capacity
    banned = call.floor in banned_floors
    if full:
        return ScoreResult(car.car_id, -1e9, False, REASON_FULL)
    if banned:
        return ScoreResult(car.car_id, -1e9, False, REASON_RESTRICTED)

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

    return ScoreResult(car.car_id, score, True, "ok")


def pick_car(
    cars: list[CarState],
    call: CallRequest,
    banned_floors: frozenset[int] = frozenset(),
) -> ScoreResult | None:
    results = [score_car(c, call, banned_floors) for c in cars]
    accepted = [r for r in results if r.accepted]
    if not accepted:
        return None
    return max(accepted, key=lambda r: r.score)


def reject_reason(
    cars: list[CarState],
    call: CallRequest,
    banned_floors: frozenset[int] = frozenset(),
) -> str:
    """派工被拒时的主导原因：呼梯层为禁停层则归因为禁停，否则按满员处理。"""
    if call.floor in banned_floors:
        return REASON_RESTRICTED
    return REASON_FULL


def congestion_by_floor(calls: list[CallRequest]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for c in calls:
        counts[c.floor] = counts.get(c.floor, 0) + c.passengers
    return counts
