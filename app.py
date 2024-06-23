from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import json

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
                      firstname TEXT NOT NULL,
                      lastname TEXT NOT NULL,
                      email TEXT NOT NULL,
                      username TEXT NOT NULL,
                      password TEXT NOT NULL
                    )''')
    conn.commit()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        
        # Check if the username already exists
        cursor.execute("SELECT username FROM student WHERE username = ?", (username,))
        existing_student = cursor.fetchone()
        if existing_student is not None:
            return render_template('student/register.html', error='Username already exists')
        
        # Insert new student if the username doesn't exist
        cursor.execute("INSERT INTO student (firstname, lastname, email, username, password) VALUES (?, ?, ?, ?, ?)", (firstname, lastname, email,username, password))
        conn.commit()
        return redirect(url_for('studentLogin'))

    return render_template('student/register.html')

# @app.route('/abcxyz', methods=['GET'])
# def studentGET():
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM student")
#     user = cursor.fetchall()
#     return user

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

    # Check if the fee_structures table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fee_structures'")
    fee_structures_table_exists = cursor.fetchone()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='classenrollment'")
    classenrollment_table_exists = cursor.fetchone()

    fee_structure = None
    error = None

    if fee_structures_table_exists:
        # Retrieve fee structures
        cursor.execute("""
            SELECT fee_structures.id, classes.id AS class_id, classes.name AS class_name, 
            teachers.id AS teacher_id, teachers.name AS teacher_name, fee_structures.amount AS class_fee_amount
            FROM fee_structures
            INNER JOIN classes ON fee_structures.class_id = classes.id
            INNER JOIN teachers ON fee_structures.teacher_id = teachers.id
        """)
        fee_structure = cursor.fetchall()

        # Retrieve student_id from session
        student_id = session.get('student')
        if student_id is not None:
            student_id = int(student_id)
            
            if classenrollment_table_exists:
                # Retrieve already enrolled classes for the student
                cursor.execute("SELECT class_id FROM classenrollment WHERE student_id = ?", (student_id,))
                enrolled_class_ids = [enrollment[0] for enrollment in cursor.fetchall()]

                # Mark fee structures with enrollment status
                fee_structure = [
                    {
                        'id': fee[0],
                        'class_id': fee[1],
                        'class_name': fee[2],
                        'teacher_id': fee[3],
                        'teacher_name': fee[4],
                        'class_fee_amount': fee[5],
                        'enrolled': fee[0] in enrolled_class_ids
                    }
                    for fee in fee_structure
                ]
            else:
                fee_structure = [
                    {
                        'id': fee[0],
                        'class_id': fee[1],
                        'class_name': fee[2],
                        'teacher_id': fee[3],
                        'teacher_name': fee[4],
                        'class_fee_amount': fee[5],
                        'enrolled': False
                    }
                    for fee in fee_structure
                ]
        else:
            error = "User not logged in"
    else:
        error = "No fee structures available"

    return render_template('student/display_fee_structure.html', fee_structure=fee_structure, error=error)


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

@app.route('/api/apply_for_classes', methods=['POST'])
def api_apply_for_classes():
    conn = get_db()
    cursor = conn.cursor()

    # Create the classenrollment table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classenrollment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            FOREIGN KEY (class_id) REFERENCES classes(id),
            FOREIGN KEY (student_id) REFERENCES student(id)
        )
    """)

    data = request.get_json()  # Get the JSON data from the request
    if not data:
        return "Invalid input", 400

    class_id = data.get("class_id")
    if not class_id:
        return "Class ID is required", 400

    student_id = session.get('student')
    if student_id is not None:
        student_id = int(student_id)
    else:
        return "User not logged in", 400

    cursor.execute("SELECT * FROM student WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if student is None:
        error = "No existing user found"
        return error, 400

    cursor.execute("SELECT * FROM classenrollment WHERE class_id = ? AND student_id = ?", (class_id, student_id))
    value = cursor.fetchone()
    if value:
        return "You've already applied for the requested class", 400

    # Insert the application into the database
    cursor.execute("INSERT INTO classenrollment (class_id, student_id) VALUES (?, ?)", (class_id, student_id))
    conn.commit()

    return f"Thank You {student[1]} {student[2]}, You've successfully applied for the requested class", 200

if __name__ == '__main__':
    app.run(debug=True)
