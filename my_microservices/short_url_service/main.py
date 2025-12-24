import os
import string
import random
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- Настройка БД ---
DATABASE_URL = "sqlite:///./data/shorturl.db"

if not os.path.exists("./data"):
    os.makedirs("./data")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Модель БД ---
class URLItem(Base):
    __tablename__ = "urls"
    short_id = Column(String, primary_key=True, index=True)
    full_url = Column(String, index=True)

Base.metadata.create_all(bind=engine)

# --- Утилиты ---
def generate_short_id(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# --- Pydantic модели ---
class URLCreate(BaseModel):
    url: str

class URLInfo(BaseModel):
    short_id: str
    full_url: str

# --- Приложение ---
app = FastAPI(title="Short URL Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/shorten", response_model=URLInfo)
def shorten_url(item: URLCreate, db: Session = Depends(get_db)):
    # Простая логика: генерируем новый ID
    # (В продакшене стоило бы проверять коллизии)
    short_id = generate_short_id()
    db_item = URLItem(short_id=short_id, full_url=item.url)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/{short_id}")
def redirect_to_full(short_id: str, db: Session = Depends(get_db)):
    item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return RedirectResponse(url=item.full_url)

@app.get("/stats/{short_id}", response_model=URLInfo)
def get_stats(short_id: str, db: Session = Depends(get_db)):
    item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return item