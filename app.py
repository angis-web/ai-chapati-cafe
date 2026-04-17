from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import re

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    import sqlite3
    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False

from flask_session import Session
from flask_sqlalchemy import SQLAlchemy


def load_dotenv(dotenv_path='.env'):
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, encoding='utf-8') as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here') or 'your_secret_key_here'

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_POSTGRES = bool(DATABASE_URL)

if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    import tempfile
    db_path = os.path.join(tempfile.gettempdir(), 'database.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
Session(app)


def get_description_from_image(image_url):
    if not image_url:
        return 'Delicious menu item prepared fresh from our kitchen.'
    filename = os.path.basename(image_url)
    name = os.path.splitext(filename)[0]
    words = re.split(r'[-_]+', name)
    filtered = [word for word in words if word and word.lower() not in {'img', 'image', 'photo', 'with', 'fresh', 'food', 'meal', 'and', 'the'}]
    if not filtered:
        filtered = [word for word in words if word]
    clean_name = ' '.join(word.capitalize() for word in filtered)
    return f'{clean_name} served fresh and flavorful.'


@app.template_filter('image_description')
def image_description_filter(image_url):
    return get_description_from_image(image_url)


def get_db_connection():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        import tempfile
        db_path = os.path.join(tempfile.gettempdir(), 'database.db')
        return sqlite3.connect(db_path)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        # Postgres
        try:
            cursor.execute("SELECT * FROM MenuItems LIMIT 1")
            columns = [desc[0] for desc in cursor.description]
            
            if 'available' not in columns:
                cursor.execute('ALTER TABLE MenuItems ADD COLUMN available BOOLEAN DEFAULT TRUE')
            
            if 'created_at' not in columns:
                cursor.execute('ALTER TABLE MenuItems ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except:
            cursor.execute('''
            CREATE TABLE MenuItems (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                description TEXT,
                price DECIMAL(10,2),
                image_url VARCHAR(500),
                category VARCHAR(50),
                available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
        
        cursor.execute("UPDATE MenuItems SET category = 'Sweets' WHERE category = 'Sweety'")
    else:
        # SQLite
        try:
            cursor.execute("SELECT * FROM MenuItems LIMIT 1")
            columns = [desc[0] for desc in cursor.description]
            
            if 'available' not in columns:
                cursor.execute('ALTER TABLE MenuItems ADD COLUMN available INTEGER DEFAULT 1')
            
            if 'created_at' not in columns:
                cursor.execute('ALTER TABLE MenuItems ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP')
        except:
            cursor.execute('''
            CREATE TABLE MenuItems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                price REAL,
                image_url TEXT,
                category TEXT,
                available INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
        
        cursor.execute("UPDATE MenuItems SET category = 'Sweets' WHERE category = 'Sweety'")
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute('SELECT * FROM MenuItems WHERE available = %s ORDER BY RANDOM() LIMIT 4', (True,))
    else:
        cursor.execute('SELECT * FROM MenuItems WHERE available = ? ORDER BY RANDOM() LIMIT 4', (1,))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    items = [dict(zip(columns, row)) for row in rows]
    conn.close()
    
    return render_template('index.html', items=items)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check for admin login
        if username == 'admin' and password == '12345':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            flash('Invalid admin credentials.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/menu')
def menu():
    page = int(request.args.get('page', 1))
    cat = request.args.get('cat', 'All')
    search = request.args.get('search', '')
    offset = (page - 1) * 10
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM MenuItems WHERE available = %s' if USE_POSTGRES else 'SELECT * FROM MenuItems WHERE available = ?'
    params = [True] if USE_POSTGRES else [1]
    
    if cat != 'All':
        query += ' AND category = %s' if USE_POSTGRES else ' AND category = ?'
        params.append(cat)
    
    if search:
        query += ' AND (name LIKE %s OR description LIKE %s)' if USE_POSTGRES else ' AND (name LIKE ? OR description LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param])
    
    query += ' ORDER BY id LIMIT 10 OFFSET %s' if USE_POSTGRES else ' ORDER BY id LIMIT 10 OFFSET ?'
    params.append(offset)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    items = [dict(zip(columns, row)) for row in rows]
    
    # Get total count
    count_query = 'SELECT COUNT(*) FROM MenuItems WHERE available = %s' if USE_POSTGRES else 'SELECT COUNT(*) FROM MenuItems WHERE available = ?'
    count_params = [True] if USE_POSTGRES else [1]
    if cat != 'All':
        count_query += ' AND category = %s' if USE_POSTGRES else ' AND category = ?'
        count_params.append(cat)
    if search:
        count_query += ' AND (name LIKE %s OR description LIKE %s)' if USE_POSTGRES else ' AND (name LIKE ? OR description LIKE ?)'
        count_params.extend([search_param, search_param])
    
    cursor.execute(count_query, count_params)
    result = cursor.fetchone()
    total = result[0] if result else 0
    total_pages = max(1, (total + 9) // 10)
    conn.close()
    
    return render_template('menu.html', items=items, page=page, total_pages=total_pages, cat=cat, search=search)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    return redirect(url_for('menu', search=query))





@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM MenuItems ORDER BY id')
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    items = [dict(zip(columns, row)) for row in rows]
    conn.close()
    return render_template('admin.html', items=items)


@app.route('/add_item', methods=['POST'])
def add_item():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    image_url = request.form['image_url']
    category = request.form['category']
    available = 'available' in request.form
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO MenuItems (name, description, price, image_url, category, available) VALUES (?, ?, ?, ?, ?, ?)',
                 (name, description, price, image_url, category, available))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/update_item/<int:id>', methods=['POST'])
def update_item(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    image_url = request.form['image_url']
    category = request.form['category']
    available = 'available' in request.form
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE MenuItems SET name=?, description=?, price=?, image_url=?, category=?, available=? WHERE id=?',
                 (name, description, price, image_url, category, available, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_item/<int:id>')
def delete_item(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM MenuItems WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# For Vercel deployment
application = app

if __name__ == '__main__':
    app.run(debug=True)