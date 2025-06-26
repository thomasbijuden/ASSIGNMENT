#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
import sqlite3
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()
DB_PATH = "../data/earphones_store.db"

# Pydantic models for request/response validation
class ProductSearch(BaseModel):
    query: Optional[str] = None
    brand: Optional[str] = None
    price_range: Optional[str] = None
    product_type: Optional[str] = None
    features: Optional[str] = None

class OrderStatusRequest(BaseModel):
    order_id: int
    email: str

class ComplaintCreate(BaseModel):
    order_id: int
    user_email: str
    topic: str
    description: str

# Database helper functions
def get_connection():
    return sqlite3.connect(DB_PATH)

@app.post("/search_products")
def search_products(criteria: ProductSearch):
    conn = get_connection()
    cursor = conn.cursor()
    
    base_query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if criteria.query:
        base_query += " AND (name LIKE ? OR brand LIKE ? OR tags LIKE ?)"
        params.extend([f"%{criteria.query}%", f"%{criteria.query}%", f"%{criteria.query}%"])
    
    if criteria.brand and criteria.brand.lower() != "any":
        base_query += " AND LOWER(brand) LIKE ?"
        params.append(f"%{criteria.brand.lower()}%")
    
    if criteria.price_range:
        # Price range parsing logic (same as original)
        pass  # Implement your price parsing logic here
    
    if criteria.product_type and criteria.product_type.lower() != "any":
        base_query += " AND tags LIKE ?"
        params.append(f"%{criteria.product_type.lower()}%")
    
    if criteria.features and criteria.features.lower() != "any":
        # Features processing logic (same as original)
        pass  # Implement your features logic here
    
    base_query += " ORDER BY rating DESC LIMIT 5"
    cursor.execute(base_query, params)
    results = cursor.fetchall()
    conn.close()
    
    return {
        "products": [
            {
                "id": row[0],
                "name": row[1],
                "brand": row[2],
                "price": row[3],
                "stock": row[4],
                "rating": row[5],
                "features": row[6]
            }
            for row in results
        ]
    }

@app.get("/order_status")
def get_order_status(order_id: int, email: str):
    print(email, "@".join(email.split("ATSYMB")))
    # email = "@".join(email.split("ATSYMB"))
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT o.*, u.name, u.email 
    FROM orders o 
    JOIN users u ON o.user_id = u.id 
    WHERE o.id = ? AND u.email = ?
    """, (order_id, "@".join(email.split("ATSYMB"))))
    
    
    result = cursor.fetchone()
    print(result)
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": result[0],
        "user_id": result[1],
        "shipping_address": result[2],
        "order_amount": result[3],
        "status": result[4],
        "created_time": result[5]
    }

@app.post("/create_complaint")
def create_complaint(complaint: ComplaintCreate):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (complaint.user_email,))
        user_result = cursor.fetchone()
        
        if not user_result:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user_result[0]
        created_at = datetime.now()
        
        cursor.execute("""
        INSERT INTO complaints (order_id, user_id, status, topic, description, created_at)
        VALUES (?, ?, 'open', ?, ?, ?)
        """, (complaint.order_id, user_id, complaint.topic, complaint.description, created_at))
        
        conn.commit()
        complaint_id = cursor.lastrowid
        return {"complaint_id": complaint_id}
    
    finally:
        conn.close()

# if __name__ == "__main__":
#     app()