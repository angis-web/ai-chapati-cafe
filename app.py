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

conn_str = 'DRIVER={SQL Server};SERVER=localhost;DATABASE=Menu_list;UID=Menu_List;PWD=menu_list'

def get_db_connection():
    return pyodbc.connect(conn_str)

def init_db():
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
    
    # Create other tables if they don't exist
    tables_to_create = [
        ('Users', '''
        CREATE TABLE Users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(50) UNIQUE,
            email NVARCHAR(100) UNIQUE,
            password_hash NVARCHAR(255),
            full_name NVARCHAR(100),
            phone NVARCHAR(20),
            address NVARCHAR(500),
            created_at DATETIME DEFAULT GETDATE()
        )
        '''),
        ('Cart', '''
        CREATE TABLE Cart (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT,
            menu_item_id INT,
            quantity INT DEFAULT 1,
            added_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (user_id) REFERENCES Users(id),
            FOREIGN KEY (menu_item_id) REFERENCES MenuItems(id)
        )
        '''),
        ('Orders', '''
        CREATE TABLE Orders (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT,
            total_amount DECIMAL(10,2),
            status NVARCHAR(20) DEFAULT 'pending',
            delivery_address NVARCHAR(500),
            phone NVARCHAR(20),
            special_instructions NVARCHAR(500),
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
        '''),
        ('OrderItems', '''
        CREATE TABLE OrderItems (
            id INT IDENTITY(1,1) PRIMARY KEY,
            order_id INT,
            menu_item_id INT,
            quantity INT,
            price DECIMAL(10,2),
            FOREIGN KEY (order_id) REFERENCES Orders(id),
            FOREIGN KEY (menu_item_id) REFERENCES MenuItems(id)
        )
        ''')
    ]
    
    for table_name, create_sql in tables_to_create:
        try:
            cursor.execute(f"SELECT TOP 1 * FROM {table_name}")
        except:
            cursor.execute(create_sql)
    
    # Insert sample data if MenuItems is empty
    cursor.execute('SELECT COUNT(*) FROM MenuItems')
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ('Chapati', 'Freshly made flatbread', 2.50, 'https://source.unsplash.com/random/400x300/?chapati', 'Food', 1),
            ('Chicken Curry', 'Spicy chicken curry with rice', 8.99, 'https://source.unsplash.com/random/400x300/?chicken-curry', 'Food', 1),
            ('Masala Tea', 'Traditional spiced tea', 3.00, 'https://source.unsplash.com/random/400x300/?tea', 'Drink', 1),
            ('Gulab Jamun', 'Sweet dumplings in syrup', 4.50, 'https://source.unsplash.com/random/400x300/?gulab-jamun', 'Sweets', 1),
            ('Paneer Tikka', 'Grilled paneer skewers', 7.99, 'https://source.unsplash.com/random/400x300/?paneer-tikka', 'Food', 1),
            ('Lassi', 'Yogurt drink', 3.50, 'https://source.unsplash.com/random/400x300/?lassi', 'Drink', 1),
            ('Ras Malai', 'Cheese dumplings in sweetened milk', 5.00, 'https://source.unsplash.com/random/400x300/?ras-malai', 'Sweets', 1),
            ('Biryani', 'Fragrant rice dish with meat', 10.99, 'https://source.unsplash.com/random/400x300/?biryani', 'Food', 1),
            ('Coffee', 'Fresh brewed coffee', 2.50, 'https://source.unsplash.com/random/400x300/?coffee', 'Drink', 1),
            ('Jalebi', 'Crispy sweet spirals', 3.99, 'https://source.unsplash.com/random/400x300/?jalebi', 'Sweets', 1),
            ('Naan', 'Leavened flatbread', 2.00, 'https://source.unsplash.com/random/400x300/?naan', 'Food', 1),
            ('Mango Lassi', 'Mango flavored yogurt drink', 4.00, 'https://source.unsplash.com/random/400x300/?mango-lassi', 'Drink', 1),
        ]
        for item in sample_items:
            cursor.execute('INSERT INTO MenuItems (name, description, price, image_url, category, available) VALUES (?, ?, ?, ?, ?, ?)', item)
    
    conn.commit()
    conn.close()

init_db()

@app.before_request
def require_login():
    allowed_routes = ['index', 'menu', 'login', 'register', 'static', 'search']
    if request.endpoint not in allowed_routes and 'user_id' not in session and 'admin' not in session:
        return redirect(url_for('login'))

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
    offset = (page - 1) * 12
    
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
    
    query += ' ORDER BY id OFFSET ? ROWS FETCH NEXT 12 ROWS ONLY'
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
    total_pages = (total + 11) // 12
    conn.close()
    
    return render_template('menu.html', items=items, page=page, total_pages=total_pages, cat=cat, search=search)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    return redirect(url_for('menu', search=query))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.quantity, m.name, m.price, m.image_url, (c.quantity * m.price) as total
        FROM Cart c
        JOIN MenuItems m ON c.menu_item_id = m.id
        WHERE c.user_id = ?
    ''', session['user_id'])
    cart_items = cursor.fetchall()
    
    total = sum(item.total for item in cart_items)
    conn.close()
    
    return render_template('cart.html', cart_items=cart_items, total=total)





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

@app.route('/admin/orders')
def admin_orders():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.id, o.total_amount, o.status, o.created_at, u.username, u.full_name
        FROM Orders o
        JOIN Users u ON o.user_id = u.id
        ORDER BY o.created_at DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>')
def admin_order_detail(order_id):
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get order info
    cursor.execute('''
        SELECT o.*, u.username, u.full_name, u.phone, u.address
        FROM Orders o
        JOIN Users u ON o.user_id = u.id
        WHERE o.id = ?
    ''', order_id)
    order = cursor.fetchone()
    
    if not order:
        conn.close()
        return redirect(url_for('admin_orders'))
    
    # Get order items
    cursor.execute('''
        SELECT oi.quantity, m.name, oi.price, (oi.quantity * oi.price) as total
        FROM OrderItems oi
        JOIN MenuItems m ON oi.menu_item_id = m.id
        WHERE oi.order_id = ?
    ''', order_id)
    order_items = cursor.fetchall()
    
    conn.close()
    return render_template('admin_order_detail.html', order=order, order_items=order_items)

@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'admin' not in session:
        return jsonify({'success': False})
    
    status = request.form['status']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE Orders SET status = ?, updated_at = GETDATE() WHERE id = ?', status, order_id)
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

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