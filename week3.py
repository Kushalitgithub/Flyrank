import sqlite3
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: str
    done: bool

app = FastAPI()
tasks = [
    task1 := {"id": 1, "title": "Task 1", "done": False},
    task2 := {"id": 2, "title": "Task 2", "done": True},
    task3 := {"id": 3, "title": "Task 3", "done": False},
]

DB_NAME = 'tasks.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY ,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
        
        '''
    )

    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]

    # if there are no tasks in the database, insert some sample tasks
    if count == 0:
        for task in tasks:
            cursor.execute(
                "INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)",
                (task["id"], task["title"], task["done"])
            )

    conn.commit()
    conn.close()

def show_tasks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()

    for task in tasks:
        print(f"{task[0]}. {task[1]} - {'Done' if task[2] else 'Not Done'}")

    conn.close()

@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/tasks")
def get_tasks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, done FROM tasks")
    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "title": row[1],
            "done": bool(row[2])
        }
        for row in rows
    ]

@app.get("/tasks/{id}")
def get_task(id: int):  
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "id": row[0],
            "title": row[1],
            "done": bool(row[2])
        }
    else:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")

@app.post("/tasks")
def create_task(task: TaskCreate):
    if task.title.strip() == "":
        raise HTTPException(status_code=400, detail="Title cannot be empty") 

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(id) FROM tasks")
    max_id = cursor.fetchone()[0]
    next_id = (max_id + 1) if max_id is not None else 1
    cursor.execute("INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)", (next_id, task.title, False))
    conn.commit()
    conn.close()

    return {
        "id": next_id,
        "title": task.title,
        "done": False
    }

@app.put("/tasks/{id}")
def update_task(id: int, task: TaskUpdate):
    if task.title.strip() == "":
        raise HTTPException(status_code=400, detail="Title cannot be empty") 

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (task.title, task.done, id))
        conn.commit()
        conn.close()
        return {
            "id": id,
            "title": task.title,
            "done": task.done
        }
    else:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {id} not found")

@app.delete("/tasks/{id}")
def delete_task(id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return Response(status_code=204)
    else:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {id} not found")



@app.on_event("startup")
def startup():
    init_db()

