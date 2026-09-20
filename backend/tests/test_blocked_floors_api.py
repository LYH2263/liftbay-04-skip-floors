def test_buildings_expose_blocked_floors(client, building, blocked_13):
    res = client.get("/api/buildings")
    assert res.status_code == 200
    rows = res.json()
    target = next(b for b in rows if b["id"] == building.id)
    assert [f["floor"] for f in target["blocked_floors"]] == [13]


def test_register_call_on_blocked_floor_rejected(client, building, blocked_13):
    res = client.post(
        "/api/calls",
        json={"building_id": building.id, "floor": 13, "direction": "down", "passengers": 1},
    )
    assert res.status_code == 400
    assert "禁停" in res.text


def test_add_and_remove_blocked_floor_persists(client, db_session, building):
    add = client.post(f"/api/buildings/{building.id}/blocked-floors", json={"floor": 7})
    assert add.status_code == 201
    # idempotency guard
    dup = client.post(f"/api/buildings/{building.id}/blocked-floors", json={"floor": 7})
    assert dup.status_code == 409

    listing = client.get("/api/buildings").json()
    assert 7 in [f["floor"] for f in listing[0]["blocked_floors"]]

    rm = client.delete(f"/api/buildings/{building.id}/blocked-floors/7")
    assert rm.status_code == 204
    listing = client.get("/api/buildings").json()
    assert 7 not in [f["floor"] for f in listing[0]["blocked_floors"]]


def test_dispatch_does_not_park_car_on_blocked_floor(client, db_session, building, cars, blocked_13):
    # A waiting ticket on the blocked floor can only arrive via direct DB
    # insert (the registration endpoint refuses it). Dispatch must not move a
    # car onto that floor.
    from app.models.models import CallTicket

    ticket = CallTicket(building_id=building.id, floor=13, direction="down", passengers=1, status="waiting")
    db_session.add(ticket)
    db_session.commit()

    res = client.post("/api/dispatch", json={"call_id": ticket.id})
    assert res.status_code == 409
    assert "禁停" in res.text

    db_session.expire_all()
    car = db_session.get(type(cars[0]), cars[0].id)
    assert car.floor == 1  # unchanged, never parked on 13

    replay = client.get("/api/replay").json()
    assert any("禁停" in log["detail"] and log["car_id"] is None for log in replay)


def test_full_reason_is_not_masked_by_blocked_copy(client, db_session, building):
    # Single car already full; call on a normal (non-blocked) floor.
    from app.models.models import CallTicket, ElevatorCar

    full_car = ElevatorCar(building_id=building.id, label="FULL", floor=1, direction="idle", load=8, capacity=8)
    db_session.add(full_car)
    db_session.commit()

    ticket = CallTicket(building_id=building.id, floor=9, direction="up", passengers=2, status="waiting")
    db_session.add(ticket)
    db_session.commit()

    res = client.post("/api/dispatch", json={"call_id": ticket.id})
    assert res.status_code == 409
    assert "满员" in res.text
    assert "禁停" not in res.text

    replay = client.get("/api/replay").json()
    detail = next(log["detail"] for log in replay if log["call_id"] == ticket.id)
    assert "满员" in detail
    assert "禁停" not in detail
