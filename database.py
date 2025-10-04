import sqlite3
import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from config import DB_NAME, GEMINI_API_KEY

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
embedding_model_name = 'models/gemini-embedding-001'

def init_db():
    """Initialize the database with all required tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        personality_summary TEXT,
        proactive_ok BOOLEAN DEFAULT FALSE,
        last_seen TIMESTAMP,
        behavioral_notes TEXT
    )''')
    
    # Conversations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Todos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        task TEXT,
        status TEXT DEFAULT "pending",
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Memories table with embeddings
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        content TEXT,
        embedding BLOB,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    conn.commit()
    conn.close()

def get_embedding(text):
    """Generate embedding for text using Gemini API with validation."""
    try:
        result = genai.embed_content(model=embedding_model_name, content=text)
        embedding = np.array(result['embedding'])

        # Validation checks for the embedding
        if np.isnan(embedding).any():
            print("⚠️ [Memory System Warning] Embedding contained NaN values. Discarding.")
            return None
        if np.linalg.norm(embedding) == 0:
            print("⚠️ [Memory System Warning] Received a zero-length embedding. Discarding.")
            return None

        return embedding
    except Exception as e:
        print(f"⚠️ [Memory System Warning] Could not generate embedding: {e}")
        return None

def add_memory(user_id, content):
    """Add a memory with embedding to the database."""
    embedding = get_embedding(content)
    if embedding is not None:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO memories (user_id, content, embedding) VALUES (?, ?, ?)",
                       (user_id, content, embedding.tobytes()))
        conn.commit()
        conn.close()

def retrieve_relevant_memories(user_id, query_text, top_k=7):
    """Retrieve relevant memories based on semantic similarity."""
    query_embedding = get_embedding(query_text)
    if query_embedding is None:
        return []

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT content, embedding FROM memories WHERE user_id = ?", (user_id,))
    memories = []
    
    for content, embedding_blob in cursor.fetchall():
        try:
            stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            if np.linalg.norm(stored_embedding) > 0:
                similarity = cosine_similarity(query_embedding.reshape(1, -1), 
                                            stored_embedding.reshape(1, -1))[0][0]
                memories.append((content, similarity))
        except Exception as e:
            print(f"⚠️ [Memory System Warning] Could not process a stored memory. Skipping. Error: {e}")
            continue

    conn.close()
    memories.sort(key=lambda x: x[1], reverse=True)
    return [mem[0] for mem in memories[:top_k]]

def get_or_create_user(username):
    """Get existing user or create new user."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_data = cursor.fetchone()
    
    if user_data:
        conn.close()
        return dict(user_data)
    else:
        initial_summary = "A new user. I should get to know their preferences, communication style, and interests."
        last_seen_time = datetime.datetime.now().isoformat()
        initial_behavioral_notes = "No specific behavioral patterns observed yet."
        cursor.execute("INSERT INTO users (username, personality_summary, last_seen, behavioral_notes) VALUES (?, ?, ?, ?)",
                       (username, initial_summary, last_seen_time, initial_behavioral_notes))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {
            "id": user_id, "username": username, "personality_summary": initial_summary,
            "proactive_ok": False, "last_seen": last_seen_time, "behavioral_notes": initial_behavioral_notes
        }

def update_user(user_id, field, value):
    """Update user information."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if field in ["personality_summary", "proactive_ok", "last_seen", "behavioral_notes"]:
        cursor.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
        conn.commit()
    conn.close()

def log_conversation(user_id, role, content):
    """Log conversation to database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)", 
                   (user_id, role, content))
    conn.commit()
    conn.close()

def get_recent_conversations(user_id, limit=30):
    """Get recent conversation history."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", 
                   (user_id, limit))
    history = [{"role": row[0], "parts": [row[1]]} for row in reversed(cursor.fetchall())]
    conn.close()
    return history

def add_task(user_id, task):
    """Add a new task to user's todo list."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (user_id, task) VALUES (?, ?)", (user_id, task))
    conn.commit()
    conn.close()

def view_tasks(user_id):
    """View user's pending tasks."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, task FROM todos WHERE user_id = ? AND status = 'pending' ORDER BY id ASC", 
                   (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        return "\n--- Your To-Do List ---\n🎉 No pending tasks! You're all caught up.\n-----------------------\n"
    else:
        task_list = "\n--- Your To-Do List ---"
        for task_id, task_text in tasks:
            task_list += f"\n  [{task_id}] {task_text}"
        task_list += "\n-----------------------\n"
        return task_list

def complete_task(user_id, task_id):
    """Mark a task as completed."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET status = 'completed' WHERE user_id = ? AND id = ?", 
                   (user_id, task_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def remove_task(user_id, task_id):
    """Remove a task from the todo list."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE user_id = ? AND id = ?", (user_id, task_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success
