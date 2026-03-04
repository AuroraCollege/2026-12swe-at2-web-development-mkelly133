from flask import Flask, render_template, request, redirect, url_for, session
import database
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

# Initialize database on startup
database.init_db()
database.add_sample_data()

@app.route("/")
def index():
    """Render the landing page and reset quiz session state.

    This route is the quiz entry point. It clears any previous quiz progress
    stored in the session so each new visit starts from a clean state.
    """
    session.clear()
    return render_template("index.html", title="Quiz App")

@app.route("/start", methods=["POST"])
def start_quiz():
    """Initialize a new quiz attempt in session storage.

    Reads the submitted username (defaulting to Anonymous), stores it in
    session, resets the current question index and answer map, then redirects
    to the quiz question page.
    """
    username = request.form.get('username', 'Anonymous')
    session['username'] = username
    session['current_question'] = 0
    session['answers'] = {}
    return redirect(url_for('quiz'))

@app.route("/quiz")
def quiz():
    """Render the current question for the active quiz attempt.

    If no quiz session exists, the user is redirected to the landing page.
    If all questions are completed, the user is redirected to results.
    Otherwise the current question and progress counters are rendered.
    """
    if 'current_question' not in session:
        return redirect(url_for('index'))
    
    questions = database.get_all_questions()
    current_index = session['current_question']
    
    if current_index >= len(questions):
        return redirect(url_for('results'))
    
    question = questions[current_index]
    return render_template("quiz.html", 
                         question=question,
                         current=current_index + 1,
                         total=len(questions))

@app.route("/answer", methods=["POST"])
def answer():
    """Store the submitted answer for the current question and advance.

    Persists the selected choice ID in session under the current question ID,
    increments question position, and redirects back to the quiz route to show
    the next question.
    """
    if 'current_question' not in session:
        return redirect(url_for('index'))
    
    choice_id = request.form.get('choice_id')
    questions = database.get_all_questions()
    current_index = session['current_question']
    
    if choice_id:
        question_id = questions[current_index]['id']
        session['answers'][str(question_id)] = choice_id
    
    session['current_question'] = current_index + 1
    
    return redirect(url_for('quiz'))

@app.route("/results")
def results():
    """Calculate and render quiz results for the current session.

    Compares submitted answers against the answer key, builds per-question
    feedback, computes total score and percentage, saves the score to the
    leaderboard table, and renders the results page.
    """
    if 'answers' not in session:
        return redirect(url_for('index'))
    
    questions = database.get_all_questions()
    answers = session.get('answers', {})
    username = session.get('username', 'Anonymous')
    
    # Check answers
    score = 0
    results_list = []
    
    for question in questions:
        question_id = str(question['id'])
        if question_id in answers:
            choice_id = answers[question_id]
            is_correct = database.check_answer(choice_id)
            if is_correct:
                score += 1
            
            # Find the chosen answer text
            chosen_choice = next((c for c in question['choices'] if c['id'] == choice_id), None)
            correct_choice = next((c for c in question['choices'] if c['is_correct']), None)
            
            results_list.append({
                'question': question['question_text'],
                'your_answer': chosen_choice['text'] if chosen_choice else 'Not answered',
                'correct_answer': correct_choice['text'] if correct_choice else '',
                'is_correct': is_correct
            })
    
    total_questions = len(questions)
    percentage = round((score / total_questions * 100), 2) if total_questions > 0 else 0
    
    # Save score
    database.save_score(username, score)
    
    return render_template("results.html",
                         score=score,
                         total=total_questions,
                         percentage=percentage,
                         results=results_list,
                         username=username)

@app.route("/leaderboard")
def leaderboard():
    """Render the leaderboard page with top saved scores.

    Fetches a limited set of high scores from the database and passes them to
    the leaderboard template for display.
    """
    scores = database.get_leaderboard(limit=10)
    return render_template("leaderboard.html", scores=scores)
