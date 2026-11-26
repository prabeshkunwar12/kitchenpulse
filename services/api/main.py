import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Integer, String, Boolean, DateTime, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///dev.db'))
class Base(DeclarativeBase): pass
class Item(Base):
    __tablename__ = 'items'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[int] = mapped_column(Integer)
    minimum: Mapped[int] = mapped_column(Integer)
    reported: Mapped[bool] = mapped_column(Boolean, default=False)
class Movement(Base):
    __tablename__ = 'movements'
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))
    delta: Mapped[int]
    balance: Mapped[int]
    reversed: Mapped[bool] = mapped_column(default=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
class NewItem(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    category: str = Field(min_length=1,max_length=100)
    unit: str = Field(min_length=1,max_length=30)
    quantity: int = Field(ge=0)
    minimum: int = Field(ge=0)
class Change(BaseModel):
    delta: int
class Threshold(BaseModel):
    minimum: int = Field(ge=0)
class Report(BaseModel):
    reported: bool

def serialize(i):
    return dict(id=i.id,name=i.name,category=i.category,unit=i.unit,quantity=i.quantity,minimum=i.minimum,reported=i.reported,low=i.quantity<=i.minimum or i.reported)
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield
app=FastAPI(title='KitchenPulse', lifespan=lifespan)
@app.get('/items')
def items():
    with Session(engine) as s: return [serialize(i) for i in s.scalars(select(Item).order_by(Item.name))]
@app.post('/items',status_code=201)
def add(body: NewItem):
    with Session(engine) as s, s.begin():
        if s.scalar(select(Item).where(Item.name==body.name)): raise HTTPException(409,'Item exists')
        i=Item(**body.model_dump()); s.add(i); s.flush()
        s.add(Movement(item_id=i.id,delta=i.quantity,balance=i.quantity))
        return serialize(i)
def locked(s,id):
    i=s.scalar(select(Item).where(Item.id==id).with_for_update())
    if i is None: raise HTTPException(404,'Item not found')
    return i
@app.post('/items/{id}/change')
def change(id:int,body:Change):
    with Session(engine) as s,s.begin():
        i=locked(s,id)
        if i.quantity+body.delta<0 or body.delta==0: raise HTTPException(400,'Invalid stock change')
        i.quantity+=body.delta
        s.add(Movement(item_id=id,delta=body.delta,balance=i.quantity)); return serialize(i)
@app.patch('/items/{id}/threshold')
def threshold(id:int,body:Threshold):
    with Session(engine) as s,s.begin():
        i=locked(s,id); i.minimum=body.minimum; return serialize(i)
@app.patch('/items/{id}/report')
def report(id:int,body:Report):
    with Session(engine) as s,s.begin():
        i=locked(s,id); i.reported=body.reported; return serialize(i)
@app.get('/history')
def history():
    with Session(engine) as s:
        return [dict(id=m.id,item_id=m.item_id,name=name,delta=m.delta,balance=m.balance,reversed=m.reversed,created=m.created) for m,name in s.execute(select(Movement,Item.name).join(Item).order_by(Movement.id.desc()).limit(100))]
@app.post('/history/{id}/undo')
def undo(id:int):
    with Session(engine) as s,s.begin():
        m=s.scalar(select(Movement).where(Movement.id==id).with_for_update())
        if not m or m.reversed: raise HTTPException(409,'Movement unavailable')
        i=locked(s,m.item_id)
        if i.quantity-m.delta<0: raise HTTPException(409,'Insufficient stock to undo')
        i.quantity-=m.delta; m.reversed=True
        s.add(Movement(item_id=i.id,delta=-m.delta,balance=i.quantity,reversed=True)); return serialize(i)
