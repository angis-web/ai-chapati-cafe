from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from flask_session import Session
import os
import re


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
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

DB_SERVER = os.environ.get('DB_SERVER', 'localhost') or 'localhost'
DB_NAME = os.environ.get('DB_NAME', 'Menu_list') or 'Menu_list'
DB_UID = os.environ.get('DB_UID', 'Menu_List') or 'Menu_List'
DB_PWD = os.environ.get('DB_PWD', 'menu_list') or 'menu_list'

conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};UID={DB_UID};PWD={DB_PWD}'
master_conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE=master;UID={DB_UID};PWD={DB_PWD}'


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
    return pyodbc.connect(conn_str)

def ensure_database():
    try:
        conn = pyodbc.connect(conn_str)
        conn.close()
    except:
        # Database doesn't exist, create it
        conn = pyodbc.connect(master_conn_str)
        cursor = conn.cursor()
        cursor.execute(f'CREATE DATABASE [{DB_NAME}]')
        conn.commit()
        conn.close()

def init_db():
    ensure_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if MenuItems table exists and add missing columns
    try:
        cursor.execute("SELECT TOP 1 * FROM MenuItems")
        columns = [column[0] for column in cursor.description]
        
        if 'available' not in columns:
            cursor.execute('ALTER TABLE MenuItems ADD available BIT DEFAULT 1')
        
        if 'created_at' not in columns:
            cursor.execute('ALTER TABLE MenuItems ADD created_at DATETIME DEFAULT GETDATE()')
    except:
        # Table doesn't exist, create it
        cursor.execute('''
        CREATE TABLE MenuItems (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(100),
            description NVARCHAR(500),
            price DECIMAL(10,2),
            image_url NVARCHAR(500),
            category NVARCHAR(50),
            available BIT DEFAULT 1,
            created_at DATETIME DEFAULT GETDATE()
        )
        ''')
    
    # Insert sample data if MenuItems is empty
    cursor.execute('SELECT COUNT(*) FROM MenuItems')
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ('Chapati', '', 2.50, 'images/chapati-img1.png', 'Food', 1),
            ('Chicken Curry', '', 8.99, 'images/chapati-chicken.png', 'Food', 1),
            ('Masala Tea', '', 3.00, 'images/tea-tea.jpg', 'Drink', 1),
            ('Gulab Jamun', '', 4.50, 'images/juice-power.jpg', 'Sweets', 1),
            ('Paneer Tikka', '', 7.99, 'images/meat.jpg', 'Food', 1),
            ('Lassi', '', 3.50, 'images/milk-milk.jpg', 'Drink', 1),
            ('Ras Malai', '', 5.00, 'images/milk-with-biscuits.jpg', 'Sweets', 1),
            ('Biryani', '', 10.99, 'images/pasta-shrimp-spaghetti-with-fresh-herbs.jpg', 'Food', 1),
            ('Coffee', '', 2.50, 'images/coffee-cappuccino.jpg', 'Drink', 1),
            ('Jalebi', '', 3.99, 'images/chips.jpg', 'Sweets', 1),
            ('Naan', '', 2.00, 'images/chapati-img2.png', 'Food', 1),
            ('Mango Lassi', '', 4.00, 'images/juice-mango.jpg', 'Drink', 1),
            ('Burger', '', 6.99, 'images/burger-cc-with-fresh-lettuce.jpg', 'Food', 1),
            ('Chips', '', 2.99, 'images/chips-potato.jpg', 'Food', 1),
            ('Orange Juice', '', 3.50, 'images/juice-orange.jpg', 'Drink', 1),
            ('Pizza', '', 9.99, 'images/pizza-pepperonia.jpg', 'Food', 1),
            ('Spaghetti', '', 7.50, 'images/pasta-spaghetti.jpg', 'Food', 1),
        ]
        for item in sample_items:
            cursor.execute('INSERT INTO MenuItems (name, description, price, image_url, category, available) VALUES (?, ?, ?, ?, ?, ?)', item)
    
    # Update category from Sweety to Sweets
    cursor.execute("UPDATE MenuItems SET category = 'Sweets' WHERE category = 'Sweety'")
    
    conn.commit()
    conn.close()

ensure_database()
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT TOP 4 * FROM MenuItems WHERE available = 1 ORDER BY NEWID()')
    items = cursor.fetchall()
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
    
    query = 'SELECT * FROM MenuItems WHERE available = 1'
    params = []
    
    if cat != 'All':
        query += ' AND category = ?'
        params.append(cat)
    
    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += ' ORDER BY id OFFSET ? ROWS FETCH NEXT 10 ROWS ONLY'
    params.append(offset)
    
    cursor.execute(query, params)
    items = cursor.fetchall()
    
    # Get total count
    count_query = 'SELECT COUNT(*) FROM MenuItems WHERE available = 1'
    count_params = []
    if cat != 'All':
        count_query += ' AND category = ?'
        count_params.append(cat)
    if search:
        count_query += ' AND (name LIKE ? OR description LIKE ?)'
        count_params.extend([f'%{search}%', f'%{search}%'])
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
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
    items = cursor.fetchall()
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
    available = request.form.get('available', '1') == '1'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO MenuItems (name, description, price, image_url, category, available) VALUES (?, ?, ?, ?, ?, ?)',
                 name, description, price, image_url, category, available)
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
    available = request.form.get('available', '1') == '1'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE MenuItems SET name=?, description=?, price=?, image_url=?, category=?, available=? WHERE id=?',
                 name, description, price, image_url, category, available, id)
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_item/<int:id>')
def delete_item(id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM MenuItems WHERE id=?', id)
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)