import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- Настройка БД ---
# База данных будет лежать в папке /app/data внутри контейнера
DATABASE_URL = "sqlite:///./data/todo.db"

# Создаем папку data, если запускаем локально без докера (для тестов)
if not os.path.exists("./data"):
    os.makedirs("./data")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Модель БД ---
class TodoItemDB(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    completed = Column(Boolean, default=False)

# Создание таблиц при старте
Base.metadata.create_all(bind=engine)

# --- Pydantic модели ---
class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TodoResponse(TodoCreate):
    id: int
    class Config:
        from_attributes = True

# --- Приложение FastAPI ---
app = FastAPI(title="ToDo Service")

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/items", response_model=TodoResponse)
def create_item(item: TodoCreate, db: Session = Depends(get_db)):
    db_item = TodoItemDB(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items", response_model=List[TodoResponse])
def read_items(db: Session = Depends(get_db)):
    return db.query(TodoItemDB).all()

@app.get("/items/{item_id}", response_model=TodoResponse)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(TodoItemDB).filter(TodoItemDB.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=TodoResponse)
def update_item(item_id: int, item_data: TodoCreate, db: Session = Depends(get_db)):
    item = db.query(TodoItemDB).filter(TodoItemDB.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.title = item_data.title
    item.description = item_data.description
    item.completed = item_data.completed
    db.commit()
    db.refresh(item)
    return item

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(TodoItemDB).filter(TodoItemDB.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return {"detail": "Item deleted"}