from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import BlockedFloor, Building, CallTicket, DispatchLog, ElevatorCar
from app.schemas.schemas import (
    BlockedFloorCreate,
    BlockedFloorOut,
    BuildingOut,
    CallCreate,
    CallOut,
    CarOut,
    CongestionFloor,
    DispatchRequest,
    LogOut,
)
from app.services.dispatch_engine import (
    REASON_BLOCKED,
    REASON_FULL,
    CallRequest,
    CarState,
    congestion_by_floor,
    evaluate,
)

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "ok"}


@api_router.get("/buildings", response_model=list[BuildingOut])
def buildings(db: Session = Depends(get_db)):
    return db.scalars(select(Building).order_by(Building.id)).all()


@api_router.post("/buildings/{building_id}/blocked-floors", response_model=BlockedFloorOut, status_code=201)
def add_blocked_floor(building_id: int, body: BlockedFloorCreate, db: Session = Depends(get_db)):
    b = db.get(Building, building_id)
    if not b:
        raise HTTPException(404, "楼栋不存在")
    if body.floor > b.floors:
        raise HTTPException(400, "楼层超出")
    exists = db.scalar(
        select(BlockedFloor.id).where(
            BlockedFloor.building_id == building_id, BlockedFloor.floor == body.floor
        )
    )
    if exists:
        raise HTTPException(409, "该层已是禁停层")
    row = BlockedFloor(building_id=building_id, floor=body.floor)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@api_router.delete("/buildings/{building_id}/blocked-floors/{floor}", status_code=204)
def remove_blocked_floor(building_id: int, floor: int, db: Session = Depends(get_db)):
    row = db.scalar(
        select(BlockedFloor).where(
            BlockedFloor.building_id == building_id, BlockedFloor.floor == floor
        )
    )
    if not row:
        raise HTTPException(404, "禁停层不存在")
    db.delete(row)
    db.commit()


@api_router.get("/cars", response_model=list[CarOut])
def cars(db: Session = Depends(get_db)):
    return db.scalars(select(ElevatorCar).order_by(ElevatorCar.id)).all()


@api_router.get("/calls", response_model=list[CallOut])
def calls(db: Session = Depends(get_db)):
    return db.scalars(select(CallTicket).order_by(CallTicket.id.desc())).all()


@api_router.post("/calls", response_model=CallOut)
def create_call(body: CallCreate, db: Session = Depends(get_db)):
    b = db.get(Building, body.building_id)
    if not b:
        raise HTTPException(404, "楼栋不存在")
    if body.floor > b.floors:
        raise HTTPException(400, "楼层超出")
    if body.direction not in ("up", "down"):
        raise HTTPException(400, "方向无效")
    blocked = db.scalar(
        select(BlockedFloor.id).where(
            BlockedFloor.building_id == body.building_id, BlockedFloor.floor == body.floor
        )
    )
    if blocked:
        raise HTTPException(400, f"{body.floor} 层为禁停层，无法登记呼梯")
    ticket = CallTicket(
        building_id=body.building_id,
        floor=body.floor,
        direction=body.direction,
        passengers=body.passengers,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@api_router.post("/dispatch", response_model=CallOut)
def dispatch(body: DispatchRequest, db: Session = Depends(get_db)):
    ticket = db.get(CallTicket, body.call_id)
    if not ticket:
        raise HTTPException(404, "呼梯不存在")
    if ticket.status != "waiting":
        raise HTTPException(400, "呼梯已处理")
    car_rows = db.scalars(
        select(ElevatorCar).where(ElevatorCar.building_id == ticket.building_id)
    ).all()
    cars = [
        CarState(c.id, c.floor, c.direction, c.load, c.capacity) for c in car_rows
    ]
    blocked_floors = frozenset(
        db.scalars(
            select(BlockedFloor.floor).where(BlockedFloor.building_id == ticket.building_id)
        ).all()
    )
    call = CallRequest(ticket.id, ticket.floor, ticket.direction, ticket.passengers)
    outcome = evaluate(cars, call, blocked_floors)
    if outcome.result is None:
        if outcome.reason == REASON_BLOCKED:
            detail = f"{ticket.floor} 层为禁停层，拒绝派工"
            message = f"无可用轿厢（{ticket.floor} 层禁停）"
        else:
            detail = "全部轿厢满员，拒绝派工"
            message = "无可用轿厢（满员）"
        db.add(DispatchLog(call_id=ticket.id, car_id=None, detail=detail))
        ticket.status = "rejected"
        db.commit()
        db.refresh(ticket)
        raise HTTPException(409, message)
    best = outcome.result
    car = db.get(ElevatorCar, best.car_id)
    assert car
    ticket.status = "assigned"
    ticket.assigned_car_id = car.id
    ticket.score = f"{best.score:.1f}"
    car.load += ticket.passengers
    car.floor = ticket.floor
    car.direction = ticket.direction
    db.add(
        DispatchLog(
            call_id=ticket.id,
            car_id=car.id,
            detail=f"派予 {car.label}，评分 {best.score:.1f}（同向/距离综合）",
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@api_router.get("/replay", response_model=list[LogOut])
def replay(db: Session = Depends(get_db)):
    return db.scalars(select(DispatchLog).order_by(DispatchLog.id.desc())).all()


@api_router.get("/congestion", response_model=list[CongestionFloor])
def congestion(db: Session = Depends(get_db)):
    waiting = db.scalars(select(CallTicket).where(CallTicket.status == "waiting")).all()
    counts = congestion_by_floor(
        [CallRequest(c.id, c.floor, c.direction, c.passengers) for c in waiting]
    )
    return [
        CongestionFloor(floor=f, passengers=p)
        for f, p in sorted(counts.items(), key=lambda x: -x[1])
    ]
