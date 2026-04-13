from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pyodbc
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')  # Change this to a secure key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=Menu_list;UID=Menu_List;PWD=menu_list'
master_conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=master;UID=Menu_List;PWD=menu_list'

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
        cursor.execute('CREATE DATABASE Menu_list')
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
            ('Chapati', 'Freshly made flatbread', 2.50, 'https://source.unsplash.com/random/400x300/?chapati', 'Food', 1),
            ('Chicken Curry', 'Spicy chicken curry with rice', 8.99, 'https://source.unsplash.com/random/400x300/?chicken-curry', 'Food', 1),
            ('Masala Tea', 'Traditional spiced tea', 3.00, 'https://source.unsplash.com/random/400x300/?tea', 'Drink', 1),
            ('Gulab Jamun', 'Sweet dumplings in syrup', 4.50, 'https://source.unsplash.com/random/400x300/?gulab-jamun', 'Sweety', 1),
            ('Paneer Tikka', 'Grilled paneer skewers', 7.99, 'https://source.unsplash.com/random/400x300/?paneer-tikka', 'Food', 1),
            ('Lassi', 'Yogurt drink', 3.50, 'https://source.unsplash.com/random/400x300/?lassi', 'Drink', 1),
            ('Ras Malai', 'Cheese dumplings in sweetened milk', 5.00, 'https://source.unsplash.com/random/400x300/?ras-malai', 'Sweety', 1),
            ('Biryani', 'Fragrant rice dish with meat', 10.99, 'https://source.unsplash.com/random/400x300/?biryani', 'Food', 1),
            ('Coffee', 'Fresh brewed coffee', 2.50, 'https://source.unsplash.com/random/400x300/?coffee', 'Drink', 1),
            ('Jalebi', 'Crispy sweet spirals', 3.99, 'https://source.unsplash.com/random/400x300/?jalebi', 'Sweety', 1),
            ('Naan', 'Leavened flatbread', 2.00, 'https://source.unsplash.com/random/400x300/?naan', 'Food', 1),
            ('Mango Lassi', 'Mango flavored yogurt drink', 4.00, 'https://source.unsplash.com/random/400x300/?mango-lassi', 'Drink', 1),
        ]
        for item in sample_items:
            cursor.execute('INSERT INTO MenuItems (name, description, price, image_url, category, available) VALUES (?, ?, ?, ?, ?, ?)', item)
    
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
    offset = (page - 1) * 18
    
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
    
    query += ' ORDER BY id OFFSET ? ROWS FETCH NEXT 18 ROWS ONLY'
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
    total_pages = max(1, (total + 17) // 18)
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