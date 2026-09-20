from app.models.models import Building, CallTicket, ElevatorCar, RestrictedFloor


def _mk_building(session, floors=18):
    b = Building(name="测试楼", floors=floors)
    session.add(b)
    session.flush()
    return b


def _mk_car(session, building_id, label, floor=1, load=0, capacity=10, direction="idle"):
    car = ElevatorCar(
        building_id=building_id, label=label, floor=floor,
        direction=direction, load=load, capacity=capacity,
    )
    session.add(car)
    session.flush()
    return car


# —— 禁停层维护：再次进入仍在 ——

def test_restricted_floor_persists(env):
    client, Session = env
    with Session() as s:
        b = _mk_building(s)
        s.commit()
        bid = b.id

    r = client.post(f"/api/buildings/{bid}/restricted-floors", json={"floor": 13})
    assert r.status_code == 200
    assert r.json()["floor"] == 13

    # 再次查询（重新进入页面）禁停层仍在
    r = client.get("/api/buildings")
    floors = [rf["floor"] for rf in r.json()[0]["restricted_floors"]]
    assert floors == [13]

    r = client.get(f"/api/buildings/{bid}/restricted-floors")
    assert [x["floor"] for x in r.json()] == [13]


def test_restricted_floor_dedup_and_range(env):
    client, Session = env
    with Session() as s:
        bid = _mk_building(s, floors=18).id
        s.commit()

    assert client.post(f"/api/buildings/{bid}/restricted-floors", json={"floor": 13}).status_code == 200
    assert client.post(f"/api/buildings/{bid}/restricted-floors", json={"floor": 13}).status_code == 409
    assert client.post(f"/api/buildings/{bid}/restricted-floors", json={"floor": 19}).status_code == 400


def test_restricted_floor_delete(env):
    client, Session = env
    with Session() as s:
        bid = _mk_building(s).id
        s.commit()
    rf_id = client.post(f"/api/buildings/{bid}/restricted-floors", json={"floor": 13}).json()["id"]
    assert client.delete(f"/api/buildings/{bid}/restricted-floors/{rf_id}").status_code == 204
    assert client.get(f"/api/buildings/{bid}/restricted-floors").json() == []


# —— 登记拒绝：禁停层不可作为呼梯候梯层 ——

def test_call_registration_rejected_on_restricted_floor(env):
    client, Session = env
    with Session() as s:
        b = _mk_building(s)
        s.add(RestrictedFloor(building_id=b.id, floor=13))
        s.commit()
        bid = b.id

    r = client.post("/api/calls", json={"building_id": bid, "floor": 13, "direction": "up", "passengers": 1})
    assert r.status_code == 400
    assert "禁停" in r.json()["detail"]

    # 没有候梯票被登记
    r = client.get("/api/calls")
    assert r.json() == []


def test_call_registration_ok_on_normal_floor(env):
    client, Session = env
    with Session() as s:
        b = _mk_building(s)
        s.add(RestrictedFloor(building_id=b.id, floor=13))
        s.commit()
        bid = b.id

    r = client.post("/api/calls", json={"building_id": bid, "floor": 12, "direction": "up", "passengers": 1})
    assert r.status_code == 200
    assert r.json()["floor"] == 12


# —— 派工：不会把轿厢停进禁停层 ——

def test_dispatch_never_parks_on_restricted_floor(env):
    client, Session = env
    with Session() as s:
        b = _mk_building(s)
        s.add(RestrictedFloor(building_id=b.id, floor=13))
        car = _mk_car(s, b.id, "T1", floor=1, load=0, capacity=10)
        ticket = CallTicket(building_id=b.id, floor=13, direction="up", passengers=1, status="waiting")
        s.add(ticket)
        s.commit()
        cid, car_id, car_floor = ticket.id, car.id, car.floor

    r = client.post("/api/dispatch", json={"call_id": cid})
    assert r.status_code == 409
    assert "禁停" in r.json()["detail"]
    assert "满员" not in r.json()["detail"]

    with Session() as s:
        # 轿厢位置没有被写成禁停层
        moved = s.get(ElevatorCar, car_id)
        assert moved.floor == car_floor
        # 呼梯被标记拒绝
        assert s.get(CallTicket, cid).status == "rejected"

    # 回放能区分禁停层
    logs = client.get("/api/replay").json()
    assert len(logs) == 1
    assert logs[0]["car_id"] is None
    assert "禁停" in logs[0]["detail"]
    assert "满员" not in logs[0]["detail"]


# —— 满员原因不被禁停文案覆盖 ——

def test_dispatch_full_reason_not_masked_by_restricted(env):
    client, Session = env
    with Session() as s:
        b = _mk_building(s)
        # 13 层禁停，但呼梯发生在普通层 8，轿厢全部满员
        s.add(RestrictedFloor(building_id=b.id, floor=13))
        _mk_car(s, b.id, "F1", floor=3, load=10, capacity=10)
        _mk_car(s, b.id, "F2", floor=9, load=9, capacity=9)
        ticket = CallTicket(building_id=b.id, floor=8, direction="up", passengers=2, status="waiting")
        s.add(ticket)
        s.commit()
        cid = ticket.id

    r = client.post("/api/dispatch", json={"call_id": cid})
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "满员" in detail
    assert "禁停" not in detail

    logs = client.get("/api/replay").json()
    assert "满员" in logs[0]["detail"]
    assert "禁停" not in logs[0]["detail"]


def test_dispatch_normal_floor_still_works_with_restricted_list(env):
    client, Session = env
    with Session() as s:
        b = _mk_building(s)
        s.add(RestrictedFloor(building_id=b.id, floor=13))
        car = _mk_car(s, b.id, "T1", floor=10, load=0, capacity=10)
        ticket = CallTicket(building_id=b.id, floor=12, direction="up", passengers=1, status="waiting")
        s.add(ticket)
        s.commit()
        cid, car_id = ticket.id, car.id

    r = client.post("/api/dispatch", json={"call_id": cid})
    assert r.status_code == 200
    assert r.json()["assigned_car_id"] == car_id
    with Session() as s:
        assert s.get(ElevatorCar, car_id).floor == 12


# —— 禁停层不产生候梯候选 ——

def test_congestion_excludes_restricted_floors(env):
    client, Session = env
    with Session() as s:
        b = _mk_building(s)
        s.add(RestrictedFloor(building_id=b.id, floor=13))
        s.add(CallTicket(building_id=b.id, floor=5, direction="up", passengers=3, status="waiting"))
        s.commit()

    rows = client.get("/api/congestion").json()
    floors = {r["floor"]: r["passengers"] for r in rows}
    assert floors.get(5) == 3
    assert 13 not in floors
