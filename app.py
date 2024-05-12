from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret_key'

DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return render_template('index.html')

# Admin register API
@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY,
                      username TEXT NOT NULL,
                      password TEXT NOT NULL
                    )''')
    conn.commit()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        if existing_user is not None:
            return render_template('admin/register.html', error='Username already exists')

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return redirect(url_for('login'))

    return render_template('admin/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            session['user'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return render_template('admin/login.html', error='Invalid username or password')
    return render_template('admin/login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('admin/dashboard.html')
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/logoutStudent')
def logoutStudent():
    session.pop('student', None)
    return redirect(url_for('studentLogin'))

@app.route('/add_class', methods=['GET', 'POST'])
def add_class():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create classes table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS classes (
                      id INTEGER PRIMARY KEY,
                      name TEXT NOT NULL UNIQUE,  -- Add UNIQUE constraint to the 'name' column
                      duration INTEGER NOT NULL
                    )''')
    conn.commit()

    # Get list of classes from the database
    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        duration = request.form['duration']
        
        # Check if the class name already exists
        cursor.execute("SELECT id FROM classes WHERE name = ?", (name,))
        existing_class = cursor.fetchone()
        if existing_class is not None:
            # Class name already exists, handle the error (e.g., display a message)
            return render_template('admin/add_class.html', error='Class name already exists', classes=classes)
        
        # Insert the new class if it doesn't exist
        cursor.execute("INSERT INTO classes (name, duration) VALUES (?, ?)", (name, duration))
        conn.commit()
        
        # Update the list of classes after adding a new one
        cursor.execute("SELECT * FROM classes")
        classes = cursor.fetchall()
        
        return render_template('admin/add_class.html', classes=classes)
    
    return render_template('admin/add_class.html', classes=classes)



@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create teachers table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS teachers (
                      id INTEGER PRIMARY KEY,
                      name TEXT NOT NULL UNIQUE  -- Add UNIQUE constraint to ensure uniqueness
                    )''')
    conn.commit()

    if request.method == 'POST':
        name = request.form['name']
        
        # Check if the teacher name already exists
        cursor.execute("SELECT id FROM teachers WHERE name = ?", (name,))
        existing_teacher = cursor.fetchone()
        if existing_teacher is not None:
            # Teacher name already exists, handle the error (e.g., display a message)
            error = 'Teacher name already exists'
        else:
            # Insert the new teacher if it doesn't exist
            cursor.execute("INSERT INTO teachers (name) VALUES (?)", (name,))
            conn.commit()
            error = None
        
        # Fetch the list of teachers from the database
        cursor.execute("SELECT id, name FROM teachers")
        teachers = cursor.fetchall()
        
        return render_template('admin/add_teacher.html', teachers=teachers, error=error)
    
    # Fetch the list of teachers from the database for initial display
    cursor.execute("SELECT id, name FROM teachers")
    teachers = cursor.fetchall()
    
    return render_template('admin/add_teacher.html', teachers=teachers, error=None)


@app.route('/add_fee_structure', methods=['GET', 'POST'])
def add_fee_structure():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create fee_structures table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS fee_structures (
                      id INTEGER PRIMARY KEY,
                      class_id INTEGER NOT NULL,
                      teacher_id INTEGER NOT NULL,
                      amount INTEGER NOT NULL,
                      UNIQUE(class_id, teacher_id),  -- Add a UNIQUE constraint for class_id and teacher_id combination
                      FOREIGN KEY (class_id) REFERENCES classes (id),
                      FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                    )''')
    conn.commit()

    if request.method == 'POST':
        class_id = request.form['class_id']
        teacher_id = request.form['teacher_id']
        amount = request.form['amount']
        
        # Check if the combination of class_id and teacher_id already exists
        cursor.execute("SELECT id FROM fee_structures WHERE class_id = ? AND teacher_id = ?", (class_id, teacher_id))
        existing_entry = cursor.fetchone()
        if existing_entry:
            # If the entry already exists, handle the error (e.g., display a message)
            error = 'Combination of class and teacher already exists'
        else:
            # Insert the new entry if it doesn't exist
            cursor.execute("INSERT INTO fee_structures (class_id, teacher_id, amount) VALUES (?, ?, ?)", (class_id, teacher_id, amount))
            conn.commit()
            error = None
        
        # Fetch all fee structures from the database
        cursor.execute("SELECT fee_structures.id, classes.name AS class_name, teachers.name AS teacher_name, fee_structures.amount FROM fee_structures INNER JOIN classes ON fee_structures.class_id = classes.id INNER JOIN teachers ON fee_structures.teacher_id = teachers.id")
        fee_structures = cursor.fetchall()
        
        # Fetch all classes and teachers for the form
        cursor.execute("SELECT * FROM classes")
        classes = cursor.fetchall()
        cursor.execute("SELECT * FROM teachers")
        teachers = cursor.fetchall()
        
        return render_template('admin/add_fee_structure.html', classes=classes, teachers=teachers, fee_structures=fee_structures, error=error)

    # Fetch all classes and teachers for the form
    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()
    cursor.execute("SELECT * FROM teachers")
    teachers = cursor.fetchall()

    # Fetch all fee structures from the database
    cursor.execute("SELECT fee_structures.id, classes.name AS class_name, teachers.name AS teacher_name, fee_structures.amount FROM fee_structures INNER JOIN classes ON fee_structures.class_id = classes.id INNER JOIN teachers ON fee_structures.teacher_id = teachers.id")
    fee_structures = cursor.fetchall()
    
    return render_template('admin/add_fee_structure.html', classes=classes, teachers=teachers, fee_structures=fee_structures, error=None)


# Student register APIs
@app.route('/registerStudent', methods=['GET', 'POST'])
def registerStudent():
    conn = get_db()
    cursor = conn.cursor()

    # Create student table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS student (
                      id INTEGER PRIMARY KEY,
                      username TEXT NOT NULL,
                      password TEXT NOT NULL
                    )''')
    conn.commit()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if the username already exists
        cursor.execute("SELECT username FROM student WHERE username = ?", (username,))
        existing_student = cursor.fetchone()
        if existing_student is not None:
            return render_template('student/register.html', error='Username already exists')
        
        # Insert new student if the username doesn't exist
        cursor.execute("INSERT INTO student (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return redirect(url_for('studentLogin'))

    return render_template('student/register.html')


@app.route('/studentLogin', methods=['GET', 'POST'])
def studentLogin():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM student WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            session['student'] = user[0]
            return redirect(url_for('display_fee_structure'))
        else:
            return render_template('student/login.html', error='Invalid username or password')
    return render_template('student/login.html')


@app.route('/display_fee_structure')
def display_fee_structure():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fee_structures.id, classes.name, teachers.name, fee_structures.amount FROM fee_structures INNER JOIN classes ON fee_structures.class_id = classes.id INNER JOIN teachers ON fee_structures.teacher_id = teachers.id")
    fee_structure = cursor.fetchall()
    return render_template('student/display_fee_structure.html', fee_structure=fee_structure)

@app.route('/delete_class/<class_name>', methods=['GET', 'POST'])
def delete_class(class_name):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM classes WHERE name=?", (class_name,))
    conn.commit()
        
        # Update the list of classes after adding a new one
    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()
    
    return render_template('admin/add_class.html', classes=classes)

@app.route('/delete_teacher/<teacher_name>', methods=['GET', 'POST'])
def delete_teachers(teacher_name):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM teachers WHERE name=?", (teacher_name,))
    conn.commit()
        
    cursor.execute("SELECT * FROM teachers")
    teachers = cursor.fetchall()

    return render_template('admin/add_teacher.html', teachers=teachers)


if __name__ == '__main__':
    app.run(debug=True)
