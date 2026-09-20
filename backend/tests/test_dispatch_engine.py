from app.services.dispatch_engine import (
    REASON_BLOCKED,
    REASON_FULL,
    CallRequest,
    CarState,
    evaluate,
    pick_car,
    score_car,
)


def test_reject_when_full():
    car = CarState(1, 5, "idle", load=8, capacity=8)
    call = CallRequest(1, 5, "up", passengers=1)
    r = score_car(car, call)
    assert r.accepted is False
    assert "满员" in r.reason


def test_same_direction_beats_far_idle():
    cars = [
        CarState(1, 2, "up", load=1, capacity=10),
        CarState(2, 12, "idle", load=0, capacity=10),
    ]
    call = CallRequest(9, 4, "up", 1)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 1


def test_closer_idle_wins_when_opposite():
    cars = [
        CarState(1, 10, "down", load=0, capacity=10),
        CarState(2, 3, "idle", load=0, capacity=10),
    ]
    call = CallRequest(3, 2, "up", 1)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 2


def test_blocked_floor_rejects_even_with_idle_cars():
    cars = [
        CarState(1, 3, "idle", load=0, capacity=10),
        CarState(2, 12, "idle", load=0, capacity=10),
    ]
    call = CallRequest(4, 13, "down", 1)
    outcome = evaluate(cars, call, blocked_floors=frozenset({13}))
    assert outcome.result is None
    assert outcome.reason == REASON_BLOCKED
    # pick_car stays consistent with the evaluate outcome
    assert pick_car(cars, call, blocked_floors=frozenset({13})) is None


def test_blocked_floor_does_not_relax_when_cars_full():
    # Blocked floors are refused regardless of capacity; capacity must not
    # mask the blocked-floor reason.
    cars = [CarState(1, 13, "idle", load=10, capacity=10)]
    call = CallRequest(5, 13, "up", 1)
    outcome = evaluate(cars, call, blocked_floors=frozenset({13}))
    assert outcome.result is None
    assert outcome.reason == REASON_BLOCKED


def test_full_reason_not_overridden_by_blocked_text():
    # Normal (non-blocked) floor, every car full -> capacity reason, never the
    # blocked-floor copy.
    cars = [
        CarState(1, 5, "idle", load=8, capacity=8),
        CarState(2, 6, "up", load=10, capacity=10),
    ]
    call = CallRequest(6, 7, "up", 1)
    outcome = evaluate(cars, call, blocked_floors=frozenset({13}))
    assert outcome.result is None
    assert outcome.reason == REASON_FULL
    assert "禁停" not in outcome.reason
