from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from flask_session import Session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

conn_str = 'DRIVER={SQL Server};SERVER=localhost;DATABASE=Menu_list;UID=Menu_List;PWD=menu_list'

def get_db_connection():
    return pyodbc.connect(conn_str)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='MenuItems' AND xtype='U')
    CREATE TABLE MenuItems (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(100),
        description NVARCHAR(500),
        price DECIMAL(10,2),
        image_url NVARCHAR(500),
        category NVARCHAR(50)
    )
    ''')
    # Insert sample data if empty
    cursor.execute('SELECT COUNT(*) FROM MenuItems')
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ('Chapati', 'Freshly made flatbread', 2.50, 'https://source.unsplash.com/random/400x300/?chapati', 'Food'),
            ('Chicken Curry', 'Spicy chicken curry with rice', 8.99, 'https://source.unsplash.com/random/400x300/?chicken-curry', 'Food'),
            ('Masala Tea', 'Traditional spiced tea', 3.00, 'https://source.unsplash.com/random/400x300/?tea', 'Drink'),
            ('Gulab Jamun', 'Sweet dumplings in syrup', 4.50, 'https://source.unsplash.com/random/400x300/?gulab-jamun', 'Sweets'),
            ('Paneer Tikka', 'Grilled paneer skewers', 7.99, 'https://source.unsplash.com/random/400x300/?paneer-tikka', 'Food'),
            ('Lassi', 'Yogurt drink', 3.50, 'https://source.unsplash.com/random/400x300/?lassi', 'Drink'),
            ('Ras Malai', 'Cheese dumplings in sweetened milk', 5.00, 'https://source.unsplash.com/random/400x300/?ras-malai', 'Sweets'),
            ('Biryani', 'Fragrant rice dish with meat', 10.99, 'https://source.unsplash.com/random/400x300/?biryani', 'Food'),
            ('Coffee', 'Fresh brewed coffee', 2.50, 'https://source.unsplash.com/random/400x300/?coffee', 'Drink'),
            ('Jalebi', 'Crispy sweet spirals', 3.99, 'https://source.unsplash.com/random/400x300/?jalebi', 'Sweets'),
            ('Naan', 'Leavened flatbread', 2.00, 'https://source.unsplash.com/random/400x300/?naan', 'Food'),
            ('Mango Lassi', 'Mango flavored yogurt drink', 4.00, 'https://source.unsplash.com/random/400x300/?mango-lassi', 'Drink'),
        ]
        for item in sample_items:
            cursor.execute('INSERT INTO MenuItems (name, description, price, image_url, category) VALUES (?, ?, ?, ?, ?)', item)
    conn.commit()
    conn.close()

init_db()

@app.before_request
def require_login():
    if request.endpoint in ['admin', 'add_item', 'update_item', 'delete_item'] and 'admin' not in session:
        return redirect(url_for('login'))

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT TOP 4 * FROM MenuItems ORDER BY NEWID()')
    items = cursor.fetchall()
    conn.close()
    return render_template('index.html', items=items)

@app.route('/menu')
def menu():
    page = int(request.args.get('page', 1))
    cat = request.args.get('cat', 'All')
    offset = (page - 1) * 10
    conn = get_db_connection()
    cursor = conn.cursor()
    if cat == 'All':
        cursor.execute('SELECT * FROM MenuItems ORDER BY id OFFSET ? ROWS FETCH NEXT 10 ROWS ONLY', offset)
        items = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) FROM MenuItems')
    else:
        cursor.execute('SELECT * FROM MenuItems WHERE category = ? ORDER BY id OFFSET ? ROWS FETCH NEXT 10 ROWS ONLY', cat, offset)
        items = cursor.fetchall()
        cursor.execute('SELECT COUNT(*) FROM MenuItems WHERE category = ?', cat)
    total = cursor.fetchone()[0]
    total_pages = (total + 9) // 10
    conn.close()
    return render_template('menu.html', items=items, page=page, total_pages=total_pages, cat=cat)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == '12345':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM MenuItems')
    items = cursor.fetchall()
    conn.close()
    return render_template('admin.html', items=items)

@app.route('/add_item', methods=['POST'])
def add_item():
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    image_url = request.form['image_url']
    category = request.form['category']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO MenuItems (name, description, price, image_url, category) VALUES (?, ?, ?, ?, ?)', name, description, price, image_url, category)
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/update_item/<int:id>', methods=['POST'])
def update_item(id):
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    image_url = request.form['image_url']
    category = request.form['category']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE MenuItems SET name=?, description=?, price=?, image_url=?, category=? WHERE id=?', name, description, price, image_url, category, id)
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_item/<int:id>')
def delete_item(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM MenuItems WHERE id=?', id)
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)