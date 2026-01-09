from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from ..database import Base
import enum

class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class PositionType(str, enum.Enum):
    CE = "CE"
    PE = "PE"

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    symbol = Column(String, index=True)
    position_type = Column(String)  # CE or PE
    quantity = Column(Integer)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float)
    target = Column(Float)
    pnl = Column(Float, default=0.0)
    status = Column(String, default="OPEN")  # OPEN or CLOSED
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    exit_time = Column(DateTime(timezone=True), nullable=True)
    strategy = Column(String, nullable=True)
    notes = Column(String, nullable=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    symbol = Column(String, index=True)
    order_type = Column(String)  # MARKET, LIMIT, STOP_LOSS
    side = Column(String)  # BUY or SELL
    quantity = Column(Integer)
    price = Column(Float, nullable=True)
    executed_price = Column(Float, nullable=True)
    status = Column(String, default="PENDING")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    position_type = Column(String)  # CE or PE
    quantity = Column(Integer)
    entry_price = Column(Float)
    current_price = Column(Float)
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    stop_loss = Column(Float)
    target = Column(Float)
    status = Column(String, default="OPEN")
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AccountBalance(Base):
    __tablename__ = "account_balance"

    id = Column(Integer, primary_key=True, index=True)
    total_balance = Column(Float)
    available_balance = Column(Float)
    used_margin = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_paper_trading = Column(Boolean, default=True)
