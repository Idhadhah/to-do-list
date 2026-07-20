import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlalchemy
import sqlalchemy.orm

# Load variables from .env into the environment. In production (Render/Railway)
# you won't have a .env file at all -- you'll set these as dashboard env vars,
# and load_dotenv() just quietly does nothing in that case.
load_dotenv()

API_KEY = os.environ["API_KEY"]           # required -- app fails fast if missing
DB_PATH = os.environ.get("DB_PATH", "todos.db")

Base = sqlalchemy.orm.declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    text = sqlalchemy.Column("task", sqlalchemy.String, nullable=False)
    done = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)

    def toggle_done(self):
        self.done = not self.done


class TaskStorage:
    def __init__(self, db_path=DB_PATH):
        self.engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sqlalchemy.orm.sessionmaker(bind=self.engine)

    def get_all(self):
        with self.Session() as session:
            tasks = session.query(Task).order_by(Task.id).all()
            session.expunge_all()
        return tasks

    def get_by_id(self, task_id):
        with self.Session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                session.expunge(task)
            return task

    def insert(self, task):
        with self.Session() as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)

    def update(self, task):
        with self.Session() as session:
            session.merge(task)
            session.commit()

    def delete(self, task_id):
        with self.Session() as session:
            session.query(Task).filter(Task.id == task_id).delete()
            session.commit()


class NewTask(BaseModel):
    text: str = Field(..., min_length=1)


class TaskUpdate(BaseModel):
    text: str = Field(..., min_length=1)


def verify_api_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI()

# Comma-separated list of allowed frontend origins, e.g.
#   ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:5500
# Falls back to "*" for local dev convenience only.
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",")] if allowed_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = TaskStorage(DB_PATH)


@app.get("/")
def health_check():
    # Handy so Render/Railway health checks and you, in a browser, get something
    # other than a 404 when hitting the bare backend URL.
    return {"status": "ok"}


@app.post("/tasks", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
def add_task(task_in: NewTask):
    task = Task(text=task_in.text)
    storage.insert(task)
    return {"id": task.id, "text": task.text, "done": task.done}


@app.get("/tasks", dependencies=[Depends(verify_api_key)])
def list_tasks():
    return [{"id": t.id, "text": t.text, "done": t.done} for t in storage.get_all()]


@app.patch("/tasks/{task_id}", dependencies=[Depends(verify_api_key)])
def toggle_task(task_id: int):
    task = storage.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.toggle_done()
    storage.update(task)
    return {"id": task.id, "text": task.text, "done": task.done}


@app.put("/tasks/{task_id}", dependencies=[Depends(verify_api_key)])
def edit_task(task_id: int, task_in: TaskUpdate):
    task = storage.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.text = task_in.text
    storage.update(task)
    return {"id": task.id, "text": task.text, "done": task.done}


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
def remove_task(task_id: int):
    task = storage.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    storage.delete(task_id)
