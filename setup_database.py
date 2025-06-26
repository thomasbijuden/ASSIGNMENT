#!/usr/bin/env python3
"""
Database setup script for earphones store chatbot
Creates SQLite database with sample data for testing
"""

import sqlite3
import os

def setup_database():
    # Define paths
    data_dir = "data"
    db_path = os.path.join(data_dir, "earphones_store.db")
    
    # Create data directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")
    
    # Create database if it doesn't exist
    if not os.path.exists(db_path):
        # Connect to database (this creates the file)
        conn = sqlite3.connect(db_path)
        conn.close()
        print(f"Created database: {db_path}")
    else:
        print(f"Database already exists: {db_path}")


def create_database():
    """Create SQLite database with all required tables and sample data"""
    
    # Create database directory if it doesn't exist
    # os.makedirs('data', exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect('data/earphones_store.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT count(*) FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    table_count = cursor.fetchone()[0]
    
    # If database is empty, run initial query
    if table_count != 0:
        print(f"Database contains {table_count} tables - skipping initial query")
    else:
        # Create products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                rating REAL NOT NULL,
                tags TEXT NOT NULL
            )
        ''')
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                address TEXT NOT NULL
            )
        ''')
        
        # Create orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shipping_address TEXT NOT NULL,
                order_amount REAL NOT NULL,
                status TEXT NOT NULL,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create order_items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Create complaints table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                topic TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert sample products
        products_data = [
            ('Sony WH-1000XM4', 'Sony', 349.99, 50, 4.8, 'wireless,noise-cancelling,over-ear,premium'),
            ('Apple AirPods Pro', 'Apple', 249.99, 75, 4.7, 'wireless,noise-cancelling,in-ear,true-wireless'),
            ('Bose QuietComfort 35 II', 'Bose', 299.99, 30, 4.6, 'wireless,noise-cancelling,over-ear,premium'),
            ('Sennheiser HD 650', 'Sennheiser', 399.99, 20, 4.9, 'wired,over-ear,audiophile,premium'),
            ('JBL Tune 500BT', 'JBL', 49.99, 100, 4.2, 'wireless,on-ear,budget,portable'),
            ('Audio-Technica ATH-M50x', 'Audio-Technica', 149.99, 40, 4.5, 'wired,over-ear,studio,professional'),
            ('Samsung Galaxy Buds Pro', 'Samsung', 199.99, 60, 4.4, 'wireless,noise-cancelling,in-ear,true-wireless'),
            ('Beats Studio3 Wireless', 'Beats', 349.99, 35, 4.3, 'wireless,noise-cancelling,over-ear,premium'),
            ('Anker Soundcore Life Q30', 'Anker', 79.99, 80, 4.1, 'wireless,noise-cancelling,over-ear,budget'),
            ('Jabra Elite 85h', 'Jabra', 249.99, 25, 4.4, 'wireless,noise-cancelling,over-ear,premium')
        ]
        
        cursor.executemany('''
            INSERT INTO products (name, brand, price, quantity, rating, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', products_data)
        
        # Insert sample users
        users_data = [
            ('John Doe', 'john.doe@email.com', '123 Main St, New York, NY 10001'),
            ('Jane Smith', 'jane.smith@email.com', '456 Oak Ave, Los Angeles, CA 90210'),
            ('Mike Johnson', 'mike.johnson@email.com', '789 Pine Rd, Chicago, IL 60601'),
            ('Sarah Wilson', 'sarah.wilson@email.com', '321 Elm St, Houston, TX 77001'),
            ('David Brown', 'david.brown@email.com', '654 Maple Dr, Phoenix, AZ 85001')
        ]
        
        cursor.executemany('''
            INSERT INTO users (name, email, address)
            VALUES (?, ?, ?)
        ''', users_data)
        
        # Insert sample orders
        orders_data = [
            (111111, 1, '123 Main St, New York, NY 10001', 349.99, 'delivered', '2024-06-20 10:30:00'),
            (211111, 2, '456 Oak Ave, Los Angeles, CA 90210', 249.99, 'shipped', '2024-06-22 14:45:00'),
            (311111, 3, '789 Pine Rd, Chicago, IL 60601', 399.99, 'processing', '2024-06-24 09:15:00'),
            (411111, 4, '321 Elm St, Houston, TX 77001', 49.99, 'delivered', '2024-06-18 16:20:00'),
            (511111, 5, '654 Maple Dr, Phoenix, AZ 85001', 149.99, 'shipped', '2024-06-23 11:00:00')
        ]
        
        cursor.executemany('''
            INSERT INTO orders (id, user_id, shipping_address, order_amount, status, created_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', orders_data)
        
        # Insert sample order items
        order_items_data = [
            (111111, 1, 1, 349.99),  # Order 1: Sony WH-1000XM4
            (211111, 2, 1, 249.99),  # Order 2: Apple AirPods Pro
            (311111, 4, 1, 399.99),  # Order 3: Sennheiser HD 650
            (411111, 5, 1, 49.99),   # Order 4: JBL Tune 500BT
            (511111, 6, 1, 149.99),  # Order 5: Audio-Technica ATH-M50x
        ]
        
        cursor.executemany('''
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', order_items_data)
        
        # Insert sample complaints
        complaints_data = [
            (111111, 1, 'open', 'Product Quality', 'The headphones have crackling sound in the left ear.', '2024-06-21 10:00:00'),
            (211111, 2, 'resolved', 'Shipping Delay', 'Order was delayed by 3 days without notification.', '2024-06-23 15:30:00')
        ]
        
        cursor.executemany('''
            INSERT INTO complaints (order_id, user_id, status, topic, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', complaints_data)
        
        # Commit changes and close connection
        conn.commit()
        print("Database created successfully with sample data!")
        print("Database location: /workspace/data/earphones_store.db")
    conn.close()
    
    

if __name__ == "__main__":
    setup_database()
    create_database()
