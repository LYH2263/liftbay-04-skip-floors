from app.services.dispatch_engine import (
    REASON_FULL,
    REASON_RESTRICTED,
    CallRequest,
    CarState,
    pick_car,
    reject_reason,
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


def test_restricted_floor_rejects_available_car():
    # 轿厢有空位，但呼梯层是禁停层：派工不得停车
    car = CarState(1, 1, "idle", load=0, capacity=10)
    call = CallRequest(4, 13, "up", 1)
    r = score_car(car, call, banned_floors=frozenset({13}))
    assert r.accepted is False
    assert r.reason == REASON_RESTRICTED
    assert pick_car([car], call, frozenset({13})) is None
    assert reject_reason([car], call, frozenset({13})) == REASON_RESTRICTED


def test_full_reason_not_overwritten_by_restricted():
    # 呼梯层是普通层时，即便存在禁停层配置，满员原因不能被禁停文案覆盖
    cars = [
        CarState(1, 5, "idle", load=10, capacity=10),
        CarState(2, 9, "idle", load=8, capacity=8),
    ]
    call = CallRequest(5, 8, "up", 2)
    banned = frozenset({13})
    assert pick_car(cars, call, banned) is None
    assert reject_reason(cars, call, banned) == REASON_FULL
    for c in cars:
        assert score_car(c, call, banned).reason == REASON_FULL


def test_restricted_does_not_block_normal_floor_dispatch():
    cars = [CarState(1, 10, "idle", load=0, capacity=10)]
    call = CallRequest(6, 12, "up", 1)
    best = pick_car(cars, call, frozenset({13}))
    assert best is not None
    assert best.car_id == 1
    assert best.accepted is True
