import sqlite3

DATABASE = 'quiz.db'

def get_db_connection():
    """Create and return a SQLite connection configured for dict-like rows.

    The returned connection uses sqlite3.Row so callers can access columns by
    name instead of numeric indexes.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create required tables and migrate legacy quiz schema if needed.

    Ensures `quiz_questions` and `leaderboard` exist. If an older
    `quiz_questions` schema still includes a `category` column, this function
    migrates data into the current schema that excludes category.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create quiz_questions table (questions + choices in one table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            choice1 TEXT NOT NULL,
            choice2 TEXT NOT NULL,
            choice3 TEXT NOT NULL,
            choice4 TEXT NOT NULL,
            correct_answer INTEGER NOT NULL
        )
    ''')

    # Migrate old schema if category column exists
    cursor.execute("PRAGMA table_info(quiz_questions)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'category' in columns:
        cursor.execute('''
            CREATE TABLE quiz_questions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                choice1 TEXT NOT NULL,
                choice2 TEXT NOT NULL,
                choice3 TEXT NOT NULL,
                choice4 TEXT NOT NULL,
                correct_answer INTEGER NOT NULL
            )
        ''')
        cursor.execute('''
            INSERT INTO quiz_questions_new (id, question_text, choice1, choice2, choice3, choice4, correct_answer)
            SELECT id, question_text, choice1, choice2, choice3, choice4, correct_answer
            FROM quiz_questions
        ''')
        cursor.execute('DROP TABLE quiz_questions')
        cursor.execute('ALTER TABLE quiz_questions_new RENAME TO quiz_questions')
    
    # Create leaderboard table (simplified)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            score INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def add_sample_data():
    """Seed the quiz table with starter questions when it is empty.

    This function is idempotent for normal startup use because it first checks
    whether rows already exist before inserting sample data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute('SELECT COUNT(*) FROM quiz_questions')
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Sample questions (question_text, choice1, choice2, choice3, choice4, correct_answer)
        questions = [
            ("What is the capital of France?", "London", "Paris", "Berlin", "Madrid", 2),
            ("What is 2 + 2?", "3", "4", "5", "22", 2),
            ("What year did World War II end?", "1943", "1944", "1945", "1946", 3),
            ("What is the largest planet in our solar system?", "Earth", "Mars", "Jupiter", "Saturn", 3),
            ("Who wrote 'Romeo and Juliet'?", "Charles Dickens", "Jane Austen", "William Shakespeare", "Mark Twain", 3)
        ]
        
        for question_text, c1, c2, c3, c4, correct in questions:
            cursor.execute(
                'INSERT INTO quiz_questions (question_text, choice1, choice2, choice3, choice4, correct_answer) VALUES (?, ?, ?, ?, ?, ?)',
                (question_text, c1, c2, c3, c4, correct)
            )
        
        conn.commit()
        print("Sample data added successfully!")
    
    conn.close()

def get_all_questions():
    """Return all quiz questions in app-friendly structure.

    Reads rows from `quiz_questions` and transforms each row into a dictionary
    containing the question text and a list of four choices, including a
    derived `is_correct` flag for server-side result computation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM quiz_questions ORDER BY id')
    questions = cursor.fetchall()
    
    result = []
    for question in questions:
        # Convert the new format to the expected format
        choices = [
            {'id': f"{question['id']}_1", 'text': question['choice1'], 'is_correct': question['correct_answer'] == 1},
            {'id': f"{question['id']}_2", 'text': question['choice2'], 'is_correct': question['correct_answer'] == 2},
            {'id': f"{question['id']}_3", 'text': question['choice3'], 'is_correct': question['correct_answer'] == 3},
            {'id': f"{question['id']}_4", 'text': question['choice4'], 'is_correct': question['correct_answer'] == 4}
        ]
        
        result.append({
            'id': question['id'],
            'question_text': question['question_text'],
            'choices': choices
        })
    
    conn.close()
    return result

def check_answer(choice_id):
    """Validate whether a submitted choice ID matches the correct answer.

    Expects choice IDs formatted as `questionId_choiceNumber` (for example,
    `3_2`), loads the stored answer key for that question, and returns True
    only when the selected choice number matches.
    """
    # Parse choice_id format: "question_id_choice_number"
    parts = str(choice_id).split('_')
    if len(parts) != 2:
        return False
    
    question_id, choice_num = parts
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT correct_answer FROM quiz_questions WHERE id = ?', (int(question_id),))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result['correct_answer'] == int(choice_num)
    return False

def save_score(username, score):
    """Insert one completed quiz score into the leaderboard table.

    Stores only username and numeric score, matching the simplified
    leaderboard schema.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO leaderboard (username, score) VALUES (?, ?)',
        (username, score)
    )
    
    conn.commit()
    conn.close()

def get_leaderboard(limit=10):
    """Fetch top leaderboard entries ordered by highest score first.

    Returns a list of dictionaries containing username and score, limited to
    the requested number of rows.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, score
        FROM leaderboard
        ORDER BY score DESC
        LIMIT ?
    ''', (limit,))
    
    scores = cursor.fetchall()
    conn.close()
    
    return [dict(s) for s in scores]

if __name__ == '__main__':
    init_db()
    add_sample_data()
    print("Database initialized!")
