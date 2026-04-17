import sqlite3
import os
import tempfile

db_path = os.path.join(tempfile.gettempdir(), 'database.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Update image URLs
updates = [
    ('images/chapati-motors.png', 'https://res.cloudinary.com/dn72tcyi3/image/upload/v1776413712/chapati-motors_exyke6.png'),
    ('images/chapati-logo.jpg', 'https://res.cloudinary.com/dn72tcyi3/image/upload/v1776413691/chapati-logo_ihsxn1.jpg'),
    ('images/chapati-img1.png', 'https://res.cloudinary.com/dn72tcyi3/image/upload/v1776403357/chapati-img1_a6cs3t.png'),
]

for old_url, new_url in updates:
    c.execute('UPDATE MenuItems SET image_url = ? WHERE image_url = ?', (new_url, old_url))

conn.commit()

# Print updated items
c.execute('SELECT name, image_url FROM MenuItems ORDER BY id')
rows = c.fetchall()
print('Updated Menu Items:')
for row in rows:
    print(f'Name: {row[0]}, Image: {row[1]}')

conn.close()