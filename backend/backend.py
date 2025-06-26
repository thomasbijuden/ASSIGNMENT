# #!/usr/bin/env python3
# """
# Flask Backend for Earphones Store Chatbot
# Handles database interactions and business logic
# """

# from flask import Flask, request, jsonify
# import sqlite3
# import logging
# from datetime import datetime

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = Flask(__name__)

# # Database path
# DB_PATH = "../data/earphones_store.db"

# class DatabaseManager:
#     """Helper class for database operations"""
    
#     @staticmethod
#     def get_connection():
#         """Get database connection"""
#         return sqlite3.connect(DB_PATH)
    
#     @staticmethod
#     def search_products(query=None, brand=None, price_range=None, product_type=None, features=None):
#         """Search products based on criteria"""
#         conn = DatabaseManager.get_connection()
#         cursor = conn.cursor()
        
#         base_query = "SELECT * FROM products WHERE 1=1"
#         params = []
        
#         if query:
#             base_query += " AND (name LIKE ? OR brand LIKE ? OR tags LIKE ?)"
#             params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        
#         if brand and brand.lower() != "any":
#             base_query += " AND LOWER(brand) LIKE ?"
#             params.append(f"%{brand.lower()}%")
        
#         if price_range:
#             if "under" in price_range.lower():
#                 price_limit = float(price_range.split("$")[1]) if "$" in price_range else 100
#                 base_query += " AND price < ?"
#                 params.append(price_limit)
#             elif "-" in price_range:
#                 price_parts = price_range.replace("$", "").split("-")
#                 if len(price_parts) == 2:
#                     min_price = float(price_parts[0])
#                     max_price = float(price_parts[1])
#                     base_query += " AND price BETWEEN ? AND ?"
#                     params.extend([min_price, max_price])
#             elif "over" in price_range.lower():
#                 price_limit = float(price_range.split("$")[1]) if "$" in price_range else 400
#                 base_query += " AND price > ?"
#                 params.append(price_limit)
        
#         if product_type and product_type.lower() != "any":
#             base_query += " AND tags LIKE ?"
#             params.append(f"%{product_type.lower()}%")
        
#         if features and features.lower() != "any":
#             feature_list = features.split(",") if "," in features else [features]
#             for feature in feature_list:
#                 feature = feature.strip().lower()
#                 base_query += " AND tags LIKE ?"
#                 params.append(f"%{feature}%")
        
#         base_query += " ORDER BY rating DESC LIMIT 5"
        
#         cursor.execute(base_query, params)
#         results = cursor.fetchall()
#         conn.close()
        
#         return results
    
#     @staticmethod
#     def get_order_status(order_id, email):
#         """Get order status for given order ID and email"""
#         conn = DatabaseManager.get_connection()
#         cursor = conn.cursor()
        
#         query = """
#         SELECT o.*, u.name, u.email 
#         FROM orders o 
#         JOIN users u ON o.user_id = u.id 
#         WHERE o.id = ? AND u.email = ?
#         """
        
#         cursor.execute(query, (order_id, email))
#         result = cursor.fetchone()
#         conn.close()
        
#         return result
    
#     @staticmethod
#     def create_complaint(order_id, user_email, topic, description):
#         """Create a new complaint"""
#         conn = DatabaseManager.get_connection()
#         cursor = conn.cursor()
        
#         # First, get user_id from email
#         cursor.execute("SELECT id FROM users WHERE email = ?", (user_email,))
#         user_result = cursor.fetchone()
        
#         if not user_result:
#             conn.close()
#             return None
        
#         user_id = user_result[0]
        
#         # Insert complaint
#         query = """
#         INSERT INTO complaints (order_id, user_id, status, topic, description, created_at)
#         VALUES (?, ?, 'open', ?, ?, ?)
#         """
        
#         cursor.execute(query, (order_id, user_id, topic, description, datetime.now()))
#         complaint_id = cursor.lastrowid
#         conn.commit()
#         conn.close()
        
#         return complaint_id

# # Flask API Endpoints
# @app.route('/search_products', methods=['POST'])
# def search_products():
#     """Endpoint for product search"""
#     data = request.json
#     logger.info(f"Received search request: {data}")
    
#     try:
#         products = DatabaseManager.search_products(
#             query=data.get('search_query'),
#             brand=data.get('preferred_brand'),
#             price_range=data.get('price_range'),
#             product_type=data.get('product_type'),
#             features=data.get('features')
#         )
        
#         if products:
#             formatted_products = []
#             for product in products:
#                 formatted_products.append({
#                     'id': product[0],
#                     'name': product[1],
#                     'brand': product[2],
#                     'price': product[3],
#                     'stock': product[4],
#                     'rating': product[5],
#                     'features': product[6]
#                 })
#             return jsonify({"results": formatted_products}), 200
#         else:
#             return jsonify({"message": "No products found"}), 404
            
#     except Exception as e:
#         logger.error(f"Search error: {str(e)}")
#         return jsonify({"error": "Internal server error"}), 500

# @app.route('/get_recommendations', methods=['POST'])
# def get_recommendations():
#     """Endpoint for product recommendations"""
#     data = request.json
    
#     try:
#         products = DatabaseManager.search_products(
#             brand=data.get('preferred_brand'),
#             price_range=data.get('price_range'),
#             product_type=data.get('product_type'),
#             features=data.get('features')
#         )
        
#         if products:
#             recommendations = []
#             for product in products:
#                 recommendations.append({
#                     'name': product[1],
#                     'brand': product[2],
#                     'price': product[3],
#                     'rating': product[5],
#                     'features': product[6]
#                 })
#             return jsonify({"recommendations": recommendations}), 200
#         else:
#             return jsonify({"message": "No recommendations available"}), 404
            
#     except Exception as e:
#         logger.error(f"Recommendation error: {str(e)}")
#         return jsonify({"error": "Internal server error"}), 500

# @app.route('/track_order', methods=['POST'])
# def track_order():
#     """Endpoint for order tracking"""
#     data = request.json
#     order_id = data.get('order_id')
#     user_email = data.get('user_email')
    
#     if not order_id or not user_email:
#         return jsonify({"error": "Missing order ID or email"}), 400
    
#     try:
#         order = DatabaseManager.get_order_status(order_id, user_email)
        
#         if order:
#             return jsonify({
#                 "order_id": order_id,
#                 "status": order[4],
#                 "amount": order[3],
#                 "created_time": order[5],
#                 "shipping_address": order[2]
#             }), 200
#         else:
#             return jsonify({"message": "Order not found"}), 404
            
#     except Exception as e:
#         logger.error(f"Order tracking error: {str(e)}")
#         return jsonify({"error": "Internal server error"}), 500

# @app.route('/lodge_complaint', methods=['POST'])
# def lodge_complaint():
#     """Endpoint for lodging complaints"""
#     data = request.json
#     required_fields = ['order_id', 'user_email', 'topic', 'description']
    
#     if not all(field in data for field in required_fields):
#         return jsonify({"error": "Missing required fields"}), 400
    
#     try:
#         complaint_id = DatabaseManager.create_complaint(
#             order_id=data['order_id'],
#             user_email=data['user_email'],
#             topic=data['topic'],
#             description=data['description']
#         )
        
#         if complaint_id:
#             return jsonify({
#                 "complaint_id": complaint_id,
#                 "message": "Complaint registered successfully"
#             }), 201
#         else:
#             return jsonify({"error": "Failed to create complaint"}), 400
            
#     except Exception as e:
#         logger.error(f"Complaint error: {str(e)}")
#         return jsonify({"error": "Internal server error"}), 500

# @app.route('/escalate', methods=['POST'])
# def escalate():
#     """Endpoint for human escalation"""
#     data = request.json
#     context = {
#         "user_email": data.get('user_email'),
#         "order_id": data.get('order_id'),
#         "conversation_history": data.get('conversation_history', [])
#     }
    
#     # In a real implementation, this would trigger a handoff system
#     logger.info(f"Escalation requested with context: {context}")
#     return jsonify({
#         "message": "You've been escalated to a human agent",
#         "support_contact": "1-800-EARPHONES",
#         "email": "support@earphonesstore.com",
#         "context": context
#     }), 200

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=3000, debug=True)


#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################  ACTIONS AFTER FastAPI  #######################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################

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