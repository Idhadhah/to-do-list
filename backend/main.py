import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.orm

# Load variables from .env into the environment. In production (Render/Railway)
# you won't have a .env file at all -- you'll set these as dashboard env vars,
# and load_dotenv() just quietly does nothing in that case.
load_dotenv()

JWT_SECRET = os.environ["JWT_SECRET"]      # required -- app fails fast if missing
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))  # 24h
DB_PATH = os.environ.get("DB_PATH", "todos.db")

Base = sqlalchemy.orm.declarative_base()


class User(Base):
    __tablename__ = "users"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    email = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    text = sqlalchemy.Column("task", sqlalchemy.String, nullable=False)
    done = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    # Foreign key: this is what makes a task belong to exactly one user, while
    # a user can have many tasks (one-to-many). Every ownership check below
    # comes down to filtering on this column.
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)

    def toggle_done(self):
        self.done = not self.done


engine = sqlalchemy.create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)
Session = sqlalchemy.orm.sessionmaker(bind=engine)


class UserStorage:
    def get_by_email(self, email):
        with Session() as session:
            user = session.query(User).filter(User.email == email).first()
            if user:
                session.expunge(user)
            return user

    def get_by_id(self, user_id):
        with Session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                session.expunge(user)
            return user

    def insert(self, user):
        with Session() as session:
            session.add(user)
            try:
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                raise ValueError("email already registered")
            session.refresh(user)
            session.expunge(user)


class TaskStorage:
    def get_all(self, user_id):
        with Session() as session:
            tasks = session.query(Task).filter(Task.user_id == user_id).order_by(Task.id).all()
            session.expunge_all()
        return tasks

    def get_by_id(self, user_id, task_id):
        # Filtering by user_id here (not just task_id) is what stops one user
        # from reading, editing, or deleting another user's task -- even if
        # they know or guess its id. A mismatch looks exactly like "not found".
        with Session() as session:
            task = session.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
            if task:
                session.expunge(task)
            return task

    def insert(self, task):
        with Session() as session:
            session.add(task)
            session.commit()
            session.refresh(task)
            session.expunge(task)

    def update(self, task):
        with Session() as session:
            session.merge(task)
            session.commit()

    def delete(self, user_id, task_id):
        with Session() as session:
            session.query(Task).filter(Task.id == task_id, Task.user_id == user_id).delete()
            session.commit()


class SignupRequest(BaseModel):
    email: EmailStr
    # bcrypt ignores anything past 72 bytes, so cap the input instead of
    # silently truncating it.
    password: str = Field(..., min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class NewTask(BaseModel):
    text: str = Field(..., min_length=1)


class TaskUpdate(BaseModel):
    text: str = Field(..., min_length=1)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = user_storage.get_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


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

user_storage = UserStorage()
storage = TaskStorage()


@app.get("/")
def health_check():
    # Handy so Render/Railway health checks and you, in a browser, get something
    # other than a 404 when hitting the bare backend URL.
    return {"status": "ok"}


@app.post("/signup", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
def signup(body: SignupRequest):
    user = User(email=body.email, hashed_password=hash_password(body.password))
    try:
        user_storage.insert(user)
    except ValueError:
        raise HTTPException(status_code=409, detail="Email already registered")
    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = user_storage.get_by_email(body.email)
    # Same error for "no such user" and "wrong password" -- otherwise the
    # response itself would tell an attacker which emails have accounts.
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def add_task(task_in: NewTask, current_user: User = Depends(get_current_user)):
    task = Task(text=task_in.text, user_id=current_user.id)
    storage.insert(task)
    return {"id": task.id, "text": task.text, "done": task.done}


@app.get("/tasks")
def list_tasks(current_user: User = Depends(get_current_user)):
    return [{"id": t.id, "text": t.text, "done": t.done} for t in storage.get_all(current_user.id)]


@app.patch("/tasks/{task_id}")
def toggle_task(task_id: int, current_user: User = Depends(get_current_user)):
    task = storage.get_by_id(current_user.id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.toggle_done()
    storage.update(task)
    return {"id": task.id, "text": task.text, "done": task.done}


@app.put("/tasks/{task_id}")
def edit_task(task_id: int, task_in: TaskUpdate, current_user: User = Depends(get_current_user)):
    task = storage.get_by_id(current_user.id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.text = task_in.text
    storage.update(task)
    return {"id": task.id, "text": task.text, "done": task.done}


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task(task_id: int, current_user: User = Depends(get_current_user)):
    task = storage.get_by_id(current_user.id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    storage.delete(current_user.id, task_id)
