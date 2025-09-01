
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

app = FastAPI(title="Wallet Assignment API")

# SQLite DB setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./wallet.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False)
    wallet_balance = Column(Float, default=0.0)
    transactions = relationship("TransactionDB", back_populates="user")

class TransactionDB(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # 'credit' or 'debit'
    description = Column(String, nullable=True)
    user = relationship("UserDB", back_populates="transactions")

Base.metadata.create_all(bind=engine)

# Pydantic models
class UserCreate(BaseModel):
    name: str
    email: str
    phone: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    wallet_balance: float
    class Config:
        orm_mode = True

class WalletUpdate(BaseModel):
    amount: float

class TransactionOut(BaseModel):
    id: int
    user_id: int
    amount: float
    type: str
    description: Optional[str]
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create User
@app.post("/users", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = UserDB(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# List Users
@app.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    users = db.query(UserDB).all()
    return users

# Update Wallet
@app.post("/wallet/{user_id}")
def update_wallet(user_id: int, update: WalletUpdate, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.wallet_balance += update.amount
    txn_type = "credit" if update.amount >= 0 else "debit"
    txn = TransactionDB(user_id=user_id, amount=update.amount, type=txn_type, description=f"Wallet updated by {update.amount}")
    db.add(txn)
    db.commit()
    db.refresh(user)
    return {"wallet_balance": user.wallet_balance}

# Fetch Transactions
@app.get("/transactions/{user_id}", response_model=List[TransactionOut])
def fetch_transactions(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    txns = db.query(TransactionDB).filter(TransactionDB.user_id == user_id).all()
    return txns
