#!/usr/bin/env python3
"""
Custom actions for the Earphones Store Chatbot
Handles database interactions and business logic
"""

import sqlite3
import logging
from typing import Any, Text, Dict, List
from datetime import datetime

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, ActiveLoop, ActionExecuted

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "../data/earphones_store.db"

class DatabaseManager:
    """Helper class for database operations"""
    
    @staticmethod
    def get_connection():
        """Get database connection"""
        return sqlite3.connect(DB_PATH)
    
    @staticmethod
    def search_products(query=None, brand=None, price_range=None, product_type=None, features=None):
        """Search products based on criteria"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        base_query = "SELECT * FROM products WHERE 1=1"
        params = []
        
        if query:
            base_query += " AND (name LIKE ? OR brand LIKE ? OR tags LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        
        if brand and brand.lower() != "any":
            base_query += " AND LOWER(brand) LIKE ?"
            params.append(f"%{brand.lower()}%")
        
        if price_range:
            if "under" in price_range.lower():
                price_limit = float(price_range.split("$")[1]) if "$" in price_range else 100
                base_query += " AND price < ?"
                params.append(price_limit)
            elif "-" in price_range:
                price_parts = price_range.replace("$", "").split("-")
                if len(price_parts) == 2:
                    min_price = float(price_parts[0])
                    max_price = float(price_parts[1])
                    base_query += " AND price BETWEEN ? AND ?"
                    params.extend([min_price, max_price])
            elif "over" in price_range.lower():
                price_limit = float(price_range.split("$")[1]) if "$" in price_range else 400
                base_query += " AND price > ?"
                params.append(price_limit)
        
        if product_type and product_type.lower() != "any":
            base_query += " AND tags LIKE ?"
            params.append(f"%{product_type.lower()}%")
        
        if features and features.lower() != "any":
            feature_list = features.split(",") if "," in features else [features]
            for feature in feature_list:
                feature = feature.strip().lower()
                base_query += " AND tags LIKE ?"
                params.append(f"%{feature}%")
        
        base_query += " ORDER BY rating DESC LIMIT 5"
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    @staticmethod
    def get_order_status(order_id, email):
        """Get order status for given order ID and email"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT o.*, u.name, u.email 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        WHERE o.id = ? AND u.email = ?
        """
        
        cursor.execute(query, (order_id, email))
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    @staticmethod
    def create_complaint(order_id, user_email, topic, description):
        """Create a new complaint"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        # First, get user_id from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (user_email,))
        user_result = cursor.fetchone()
        
        if not user_result:
            conn.close()
            return None
        
        user_id = user_result[0]
        
        # Insert complaint
        query = """
        INSERT INTO complaints (order_id, user_id, status, topic, description, created_at)
        VALUES (?, ?, 'open', ?, ?, ?)
        """
        
        cursor.execute(query, (order_id, user_id, topic, description, datetime.now()))
        complaint_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return complaint_id


# class ActionSearchProducts(Action):
#     """Action to search for products"""
    
#     def name(self) -> Text:
#         return "action_search_products"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         # Get search parameters from slots
#         search_query = tracker.get_slot("search_query")
#         brand = tracker.get_slot("preferred_brand")
#         price_range = tracker.get_slot("price_range")
#         product_type = tracker.get_slot("product_type")
#         features = tracker.get_slot("features")
        
#         # Get entities from latest message
#         entities = tracker.latest_message.get("entities", [])
        
#         # Extract entities if not in slots
#         for entity in entities:
#             if entity["entity"] == "brand" and not brand:
#                 brand = entity["value"]
#             elif entity["entity"] == "feature" and not features:
#                 features = entity["value"]
#             elif entity["entity"] == "product_type" and not product_type:
#                 product_type = entity["value"]
        
#         try:
#             # Search products
#             products = DatabaseManager.search_products(
#                 query=search_query,
#                 brand=brand,
#                 price_range=price_range,
#                 product_type=product_type,
#                 features=features
#             )
            
#             if products:
#                 message = "Here are the earphones I found for you:\n\n"
#                 for product in products:
#                     message += f"🎧 **{product[1]}** by {product[2]}\n"
#                     message += f"   💰 Price: ${product[3]:.2f}\n"
#                     message += f"   ⭐ Rating: {product[5]}/5\n"
#                     message += f"   📦 Stock: {product[4]} units\n"
#                     message += f"   🏷️ Features: {product[6]}\n\n"
                
#                 message += "Would you like more details about any of these products or need help with something else?"
#             else:
#                 message = "I couldn't find any earphones matching your criteria. Let me help you with different options or you can ask for recommendations!"
            
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Error searching products: {str(e)}")
#             dispatcher.utter_message(text="I'm sorry, I encountered an error while searching for products. Please try again or contact our support team.")
        
#         return []

class ActionSearchProducts(Action):
    def name(self) -> Text:
        return "action_search_products"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        search_term = next(tracker.get_latest_entity_values("search_term"), None)
        results = []
        
        if not search_term:
            # Check if search_term slot exists
            search_term = tracker.get_slot("search_term")
            
        if not search_term:
            dispatcher.utter_message(response="utter_ask_search_term")
            return []
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            print(search_term)
            for term in search_term.split(" "):
                print(term)
                pattern = f"%{term}%"
                
                cursor.execute("""
                    SELECT *, 
                        (CASE WHEN name LIKE ? THEN 5 ELSE 0 END) +
                        (CASE WHEN brand LIKE ? THEN 3 ELSE 0 END) +
                        (CASE WHEN tags LIKE ? THEN 1 ELSE 0 END) AS relevance
                    FROM products
                    WHERE name LIKE ? OR brand LIKE ? OR tags LIKE ?
                    ORDER BY relevance DESC, name
                    LIMIT 5
                """, (pattern, pattern, pattern, pattern, pattern, pattern))
                
                # results += cursor.fetchall()
                for item in cursor.fetchall():
                    if sum([item[:7] == res[:7] for res in  results if len(results)>0])==0:
                        print(item, results)
                        print("======")
                        results.append(item)
                
            conn.close()
            print(results)
            # results = list(set(results))
            
            if results[:5]:
                message = "I found these products:\n"
                for product in results:
                    message += (
                        f"\n- {product[1]} by {product[2]} "
                        f"(Price: ${product[3]:.2f}, Stock: {product[4]}, "
                        f"Rating: {product[5]}/5)"
                    )
                dispatcher.utter_message(text=message)
            else:
                dispatcher.utter_message(response="utter_no_results")
                
        except sqlite3.Error:
            dispatcher.utter_message(text="Error searching products")
            
        return []


class ActionGetRecommendations(Action):
    """Action to provide product recommendations"""
    
    def name(self) -> Text:
        return "action_get_recommendations"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get preference parameters from slots
        brand = tracker.get_slot("preferred_brand")
        price_range = tracker.get_slot("price_range")
        product_type = tracker.get_slot("product_type")
        features = tracker.get_slot("features")
        
        try:
            # Get recommendations based on preferences
            products = DatabaseManager.search_products(
                brand=brand,
                price_range=price_range,
                product_type=product_type,
                features=features
            )
            
            if products:
                message = "Based on your preferences, here are my top recommendations:\n\n"
                for i, product in enumerate(products, 1):
                    message += f"{i}. **{product[1]}** by {product[2]}\n"
                    message += f"   💰 ${product[3]:.2f} | ⭐ {product[5]}/5 stars\n"
                    message += f"   🔖 {product[6]}\n\n"
                
                message += "These products match your criteria perfectly! Would you like more details about any of them?"
            else:
                message = "I couldn't find products matching all your preferences. Let me suggest some popular alternatives or you can adjust your criteria!"
                
                # Suggest popular products as fallback
                popular_products = DatabaseManager.search_products()
                if popular_products:
                    message += "\n\nHere are some of our most popular earphones:\n\n"
                    for product in popular_products[:3]:
                        message += f"🎧 **{product[1]}** - ${product[3]:.2f} (⭐ {product[5]}/5)\n"
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            dispatcher.utter_message(text="I'm sorry, I encountered an error while getting recommendations. Please try again or contact our support team.")
        
        return []


class ActionTrackOrder(Action):
    """Action to track order status"""
    
    def name(self) -> Text:
        return "action_track_order"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        order_id = tracker.get_slot("order_id")
        if not order_id:
            dispatcher.utter_message(text="I need your order ID to track your order.")
            return []
        
        print("hello")
        
        user_email = next(tracker.get_latest_entity_values("user_email"), None)
        # results = []
        
        if not user_email:
            # Check if search_term slot exists
            user_email = tracker.get_slot("user_email")
            
        if not user_email:
            dispatcher.utter_message(response="utter_ask_email")
            return []


        # user_email = tracker.get_slot("user_email")
        # if not user_email:
        #     dispatcher.utter_message(text="I need your email address to track your order.")
        #     return []
        
        try:
            # Get order status
            order = DatabaseManager.get_order_status(order_id, user_email)
            
            if order:
                status = order[4]  # status column
                order_amount = order[3]  # order_amount column
                created_time = order[5]  # created_time column
                shipping_address = order[2]  # shipping_address column
                
                status_emoji = {
                    "processing": "⏳",
                    "shipped": "🚚",
                    "delivered": "✅",
                    "cancelled": "❌"
                }.get(status.lower(), "📦")
                
                message = f"📋 **Order Status Update**\n\n"
                message += f"🆔 Order ID: {order_id}\n"
                message += f"{status_emoji} Status: **{status.upper()}**\n"
                message += f"💰 Amount: ${order_amount:.2f}\n"
                message += f"📅 Order Date: {created_time}\n"
                message += f"🏠 Shipping Address: {shipping_address}\n\n"
                
                if status.lower() == "processing":
                    message += "Your order is being prepared and will ship soon!"
                elif status.lower() == "shipped":
                    message += "Your order is on its way! You should receive it in 2-3 business days."
                elif status.lower() == "delivered":
                    message += "Your order has been delivered! We hope you enjoy your new earphones!"
                elif status.lower() == "cancelled":
                    message += "Your order has been cancelled. If you have questions, please contact our support team."
                
            else:
                message = f"I couldn't find an order with ID {order_id} associated with email {user_email}. Please check your order ID and email address, or contact our support team for assistance."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            logger.error(f"Error tracking order: {str(e)}")
            dispatcher.utter_message(text="I'm sorry, I encountered an error while tracking your order. Please contact our support team for assistance.")
        
        return [
            SlotSet("order_id", None),
            SlotSet("user_email", None),
        ]


class ActionLodgeComplaint(Action):
    """Action to lodge a complaint"""
    
    def name(self) -> Text:
        return "action_lodge_complaint"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        order_id = tracker.get_slot("order_id")
        dispatcher.utter_message(response="utter_ask_email")
        user_email = tracker.get_slot("user_email")
        complaint_topic = tracker.get_slot("complaint_topic")
        complaint_description = tracker.get_slot("complaint_description")
        
        if not all([order_id, user_email, complaint_topic, complaint_description]):
            dispatcher.utter_message(text="I need all the complaint details to process your request.")
            return []
        
        try:
            # Create complaint
            complaint_id = DatabaseManager.create_complaint(
                order_id=order_id,
                user_email=user_email,
                topic=complaint_topic,
                description=complaint_description
            )
            
            if complaint_id:
                message = f"✅ **Complaint Registered Successfully**\n\n"
                message += f"🆔 Complaint ID: {complaint_id}\n"
                message += f"📋 Order ID: {order_id}\n"
                message += f"📧 Email: {user_email}\n"
                message += f"🏷️ Topic: {complaint_topic}\n"
                message += f"📝 Description: {complaint_description}\n\n"
                message += "Your complaint has been registered and our customer service team will review it within 24 hours. "
                message += "You will receive an email update once we have a resolution.\n\n"
                message += "Is there anything else I can help you with today?"
            else:
                message = "I couldn't create your complaint. This might be because the order ID or email doesn't match our records. "
                message += "Please verify your information or contact our support team directly."
            
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            logger.error(f"Error lodging complaint: {str(e)}")
            dispatcher.utter_message(text="I'm sorry, I encountered an error while registering your complaint. Please contact our support team directly.")
        
        return [
            SlotSet("order_id", None),
            SlotSet("user_email", None),
            SlotSet("complaint_topic", None),
            SlotSet("complaint_description", None),
        ]


class ActionEscalateToHuman(Action):
    """Action to escalate conversation to human agent"""
    
    def name(self) -> Text:
        return "action_escalate_to_human"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        events = []
        if tracker.active_loop:
            events.append(ActiveLoop(None))  # Deactivate form
            events.append(SlotSet("requested_slot", None))  # Clear form slot
            # events.append(SlotSet("escalate_to_human", False))

        
        # Get conversation context
        user_email = tracker.get_slot("user_email")
        order_id = tracker.get_slot("order_id")
        
        message = "🤝 **Connecting you to a human agent...**\n\n"
        message += "I'm transferring your conversation to our customer service team. "
        message += "A human agent will be with you shortly to provide personalized assistance.\n\n"
        
        if user_email or order_id:
            message += "**Context being transferred:**\n"
            if user_email:
                message += f"📧 Email: {user_email}\n"
            if order_id:
                message += f"🆔 Order ID: {order_id}\n"
            message += "\n"
        
        message += "⏱️ Average wait time: 2-3 minutes\n"
        message += "📞 Alternatively, you can call us at: 1-800-EARPHONES\n"
        message += "📧 Or email: support@earphonesstore.com"
        
        dispatcher.utter_message(text=message)
        
        # In a real implementation, this would trigger the handoff to a human agent system
        # For now, we'll just log the escalation
        logger.info(f"Human escalation requested for user: {user_email}, order: {order_id}")
        
        return events
    
class ActionDefaultFallback(Action):
    def name(self):
        return "action_default_fallback"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message("Sorry, I didn't understand that.")
        dispatcher.utter_message("Could you rephrase or ask something else?")
        return []


# Form validation actions

class ValidateOrderTrackingForm(FormValidationAction):
    """Validates the order tracking form"""
    
    def name(self) -> Text:
        return "validate_order_tracking_form"
    
    def validate_order_id(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate order_id slot"""
        if slot_value and len(str(slot_value)) >= 3:
            dispatcher.utter_message(response="utter_ask_email")
            return {"order_id": slot_value}
        else:
            dispatcher.utter_message(text="Please provide a valid order ID (at least 3 characters).")
            return {"order_id": None}
    
    def validate_user_email(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate user_email slot"""
        if slot_value and "@" in slot_value and "." in slot_value:
            return {"user_email": slot_value}
        else:
            dispatcher.utter_message(text="Please provide a valid email address.")
            return {"user_email": None}


class ValidateRecommendationForm(FormValidationAction):
    """Validates the recommendation form"""
    
    def name(self) -> Text:
        return "validate_recommendation_form"
    
    def validate_preferred_brand(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate preferred_brand slot"""
        valid_brands = ["sony", "apple", "bose", "sennheiser", "jbl", "audio-technica", "samsung", "beats", "anker", "jabra", "any", "no preference"]
        
        if slot_value:
            if slot_value.lower() in valid_brands or "any" in slot_value.lower() or "no" in slot_value.lower():
                return {"preferred_brand": slot_value}
        
        return {"preferred_brand": "any"}
    
    def validate_price_range(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate price_range slot"""
        if slot_value:
            price_keywords = ["under", "$", "budget", "cheap", "expensive", "premium", "-"]
            if any(keyword in slot_value.lower() for keyword in price_keywords):
                return {"price_range": slot_value}
        
        return {"price_range": "any"}
    
    def validate_product_type(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate product_type slot"""
        valid_types = ["over-ear", "in-ear", "on-ear", "any"]
        
        if slot_value:
            if any(valid_type in slot_value.lower() for valid_type in valid_types):
                return {"product_type": slot_value}
        
        return {"product_type": "any"}
    
    def validate_features(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate features slot"""
        if slot_value:
            return {"features": slot_value}
        return {"features": "any"}


class ValidateComplaintForm(FormValidationAction):
    """Validates the complaint form"""
    
    def name(self) -> Text:
        return "validate_complaint_form"
    
    def validate_order_id(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate order_id slot"""
        if slot_value and len(str(slot_value)) >= 3:
            dispatcher.utter_message(response="utter_ask_email")
            return {"order_id": slot_value}
        else:
            dispatcher.utter_message(text="Please provide a valid order ID.")
            return {"order_id": None}
    
    def validate_user_email(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate user_email slot"""
        if slot_value and "@" in slot_value and "." in slot_value:
            return {"user_email": slot_value}
        else:
            dispatcher.utter_message(text="Please provide a valid email address.")
            return {"user_email": None}
    
    def validate_complaint_topic(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate complaint_topic slot"""
        valid_topics = ["product quality", "shipping", "customer service", "billing", "returns", "technical issue"]
        
        if slot_value:
            if any(topic in slot_value.lower() for topic in valid_topics):
                return {"complaint_topic": slot_value}
        
        return {"complaint_topic": slot_value if slot_value else None}
    
    def validate_complaint_description(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate complaint_description slot"""
        if slot_value and len(slot_value) >= 10:
            return {"complaint_description": slot_value}
        else:
            dispatcher.utter_message(text="Please provide more details about your complaint (at least 10 characters).")
            return {"complaint_description": None}


class ValidateSearchForm(FormValidationAction):
    """Validates the search form"""
    
    def name(self) -> Text:
        return "validate_search_form"
    
    def validate_search_query(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate search_query slot"""
        if slot_value and len(slot_value) >= 2:
            return {"search_query": slot_value}
        else:
            dispatcher.utter_message(text="Please provide a search term (at least 2 characters).")
            return {"search_query": None}


#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################  ACTIONS AFTER FLASK  #########################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################

# #!/usr/bin/env python3
# """
# Custom actions for the Earphones Store Chatbot
# Handles conversation flow and API interactions with file logging
# """

# import logging
# import requests
# import os
# import json
# from typing import Any, Text, Dict, List
# from datetime import datetime

# from rasa_sdk import Action, Tracker, FormValidationAction
# from rasa_sdk.executor import CollectingDispatcher
# from rasa_sdk.types import DomainDict
# from rasa_sdk.events import SlotSet, ActiveLoop, ActionExecuted

# # Configure logging to file
# log_file = "actions.log"
# log_dir = "logs"

# # Create logs directory if it doesn't exist
# if not os.path.exists(log_dir):
#     os.makedirs(log_dir)

# # Full path to log file
# log_path = os.path.join(log_dir, log_file)

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler(log_path),  # Log to file
#         logging.StreamHandler()         # Also log to console
#     ]
# )
# logger = logging.getLogger(__name__)
# logger.info("====== Starting Rasa Actions Server ======")

# # Backend API URL
# API_URL = "http://localhost:5055"

# class ApiClient:
#     """Client for interacting with backend API"""
    
#     @staticmethod
#     def search_products(params: Dict) -> Dict:
#         """Search products via API"""
#         try:
#             logger.info(f"Searching products with params: {params}")
#             response = requests.post(f"{API_URL}/search_products", json=params)
#             logger.debug(f"Search API response: {response.status_code}")
#             return response.json() if response.status_code == 200 else None
#         except Exception as e:
#             logger.error(f"API search error: {str(e)}", exc_info=True)
#             return None
    
#     @staticmethod
#     def get_recommendations(params: Dict) -> Dict:
#         """Get recommendations via API"""
#         try:
#             logger.info(f"Getting recommendations with params: {params}")
#             response = requests.post(f"{API_URL}/get_recommendations", json=params)
#             logger.debug(f"Recommendations API response: {response.status_code}")
#             return response.json() if response.status_code == 200 else None
#         except Exception as e:
#             logger.error(f"API recommendation error: {str(e)}", exc_info=True)
#             return None
    
#     @staticmethod
#     def track_order(order_id: Text, user_email: Text) -> Dict:
#         """Track order via API"""
#         try:
#             logger.info(f"Tracking order: {order_id} for {user_email}")
#             response = requests.post(
#                 f"{API_URL}/track_order",
#                 json={"order_id": order_id, "user_email": user_email}
#             )
#             logger.debug(f"Track order API response: {response.status_code}")
#             return response.json() if response.status_code == 200 else None
#         except Exception as e:
#             logger.error(f"API tracking error: {str(e)}", exc_info=True)
#             return None
    
#     @staticmethod
#     def lodge_complaint(data: Dict) -> Dict:
#         """Lodge complaint via API"""
#         try:
#             logger.info(f"Lodging complaint: {data}")
#             response = requests.post(f"{API_URL}/lodge_complaint", json=data)
#             logger.debug(f"Lodge complaint API response: {response.status_code}")
#             return response.json() if response.status_code == 201 else None
#         except Exception as e:
#             logger.error(f"API complaint error: {str(e)}", exc_info=True)
#             return None
    
#     @staticmethod
#     def escalate(data: Dict) -> Dict:
#         """Escalate to human via API"""
#         try:
#             logger.info(f"Escalating to human: {data}")
#             response = requests.post(f"{API_URL}/escalate", json=data)
#             logger.debug(f"Escalation API response: {response.status_code}")
#             return response.json() if response.status_code == 200 else None
#         except Exception as e:
#             logger.error(f"API escalation error: {str(e)}", exc_info=True)
#             return None


# class ActionSearchProducts(Action):
#     """Action to search for products"""
    
#     def name(self) -> Text:
#         return "action_search_products"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         # Log action start
#         logger.info(f"Executing {self.name()} for session {tracker.sender_id}")
        
#         # Prepare API parameters
#         params = {
#             "search_query": tracker.get_slot("search_query"),
#             "preferred_brand": tracker.get_slot("preferred_brand"),
#             "price_range": tracker.get_slot("price_range"),
#             "product_type": tracker.get_slot("product_type"),
#             "features": tracker.get_slot("features")
#         }
#         logger.debug(f"Search parameters: {params}")
        
#         try:
#             # Call API
#             api_response = ApiClient.search_products(params)
            
#             if api_response and api_response.get("results"):
#                 products = api_response["results"]
#                 logger.info(f"Found {len(products)} products")
                
#                 message = "Here are the earphones I found for you:\n\n"
#                 for product in products:
#                     message += f"🎧 **{product['name']}** by {product['brand']}\n"
#                     message += f"   💰 Price: ${product['price']:.2f}\n"
#                     message += f"   ⭐ Rating: {product['rating']}/5\n"
#                     message += f"   📦 Stock: {product['stock']} units\n"
#                     message += f"   🏷️ Features: {product['features']}\n\n"
                
#                 message += "Would you like more details about any of these products or need help with something else?"
#                 logger.debug("Sending product results to user")
#             else:
#                 message = "I couldn't find any earphones matching your criteria. Let me help you with different options or you can ask for recommendations!"
#                 logger.info("No products found matching criteria")
            
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Error in {self.name()}: {str(e)}", exc_info=True)
#             dispatcher.utter_message(text="I'm sorry, I encountered an error while searching for products. Please try again or contact our support team.")
        
#         return []


# class ActionGetRecommendations(Action):
#     """Action to provide product recommendations"""
    
#     def name(self) -> Text:
#         return "action_get_recommendations"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         # Log action start
#         logger.info(f"Executing {self.name()} for session {tracker.sender_id}")
        
#         # Prepare API parameters
#         params = {
#             "preferred_brand": tracker.get_slot("preferred_brand"),
#             "price_range": tracker.get_slot("price_range"),
#             "product_type": tracker.get_slot("product_type"),
#             "features": tracker.get_slot("features")
#         }
#         logger.debug(f"Recommendation parameters: {params}")
        
#         try:
#             # Call API
#             api_response = ApiClient.get_recommendations(params)
            
#             if api_response and api_response.get("recommendations"):
#                 recommendations = api_response["recommendations"]
#                 logger.info(f"Found {len(recommendations)} recommendations")
                
#                 message = "Based on your preferences, here are my top recommendations:\n\n"
#                 for i, product in enumerate(recommendations, 1):
#                     message += f"{i}. **{product['name']}** by {product['brand']}\n"
#                     message += f"   💰 ${product['price']:.2f} | ⭐ {product['rating']}/5 stars\n"
#                     message += f"   🔖 {product['features']}\n\n"
                
#                 message += "These products match your criteria perfectly! Would you like more details about any of them?"
#                 logger.debug("Sending recommendations to user")
#             else:
#                 message = "I couldn't find products matching all your preferences. Let me suggest some popular alternatives or you can adjust your criteria!"
#                 logger.info("No recommendations found, falling back to popular products")
                
#                 # Fallback to general search
#                 fallback_response = ApiClient.search_products({})
#                 if fallback_response and fallback_response.get("results"):
#                     popular_products = fallback_response["results"][:3]
#                     message += "\n\nHere are some of our most popular earphones:\n\n"
#                     for product in popular_products:
#                         message += f"🎧 **{product['name']}** - ${product['price']:.2f} (⭐ {product['rating']}/5)\n"
#                     logger.debug("Included popular products in response")
            
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Error in {self.name()}: {str(e)}", exc_info=True)
#             dispatcher.utter_message(text="I'm sorry, I encountered an error while getting recommendations. Please try again or contact our support team.")
        
#         return []


# class ActionTrackOrder(Action):
#     """Action to track order status"""
    
#     def name(self) -> Text:
#         return "action_track_order"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         # Log action start
#         logger.info(f"Executing {self.name()} for session {tracker.sender_id}")
        
#         order_id = tracker.get_slot("order_id")
#         user_email = tracker.get_slot("user_email")
        
#         if not order_id:
#             logger.warning("Order ID missing in track order request")
#             dispatcher.utter_message(text="I need your order ID to track your order.")
#             return []
        
#         if not user_email:
#             logger.warning("User email missing in track order request")
#             dispatcher.utter_message(text="I need your email address to track your order.")
#             return []
        
#         logger.debug(f"Tracking order: ID={order_id}, Email={user_email}")
        
#         try:
#             # Call API
#             api_response = ApiClient.track_order(order_id, user_email)
            
#             if api_response:
#                 status = api_response.get("status", "unknown")
#                 amount = api_response.get("amount", 0)
#                 created_time = api_response.get("created_time", "unknown")
#                 shipping_address = api_response.get("shipping_address", "unknown")
                
#                 status_emoji = {
#                     "processing": "⏳",
#                     "shipped": "🚚",
#                     "delivered": "✅",
#                     "cancelled": "❌"
#                 }.get(status.lower(), "📦")
                
#                 message = f"📋 **Order Status Update**\n\n"
#                 message += f"🆔 Order ID: {order_id}\n"
#                 message += f"{status_emoji} Status: **{status.upper()}**\n"
#                 message += f"💰 Amount: ${amount:.2f}\n"
#                 message += f"📅 Order Date: {created_time}\n"
#                 message += f"🏠 Shipping Address: {shipping_address}\n\n"
                
#                 if status.lower() == "processing":
#                     message += "Your order is being prepared and will ship soon!"
#                 elif status.lower() == "shipped":
#                     message += "Your order is on its way! You should receive it in 2-3 business days."
#                 elif status.lower() == "delivered":
#                     message += "Your order has been delivered! We hope you enjoy your new earphones!"
#                 elif status.lower() == "cancelled":
#                     message += "Your order has been cancelled. If you have questions, please contact our support team."
                
#                 logger.info(f"Order status: {status}")
#             else:
#                 message = f"I couldn't find an order with ID {order_id} associated with email {user_email}. Please check your order ID and email address, or contact our support team for assistance."
#                 logger.warning(f"Order not found: ID={order_id}, Email={user_email}")
            
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Error in {self.name()}: {str(e)}", exc_info=True)
#             dispatcher.utter_message(text="I'm sorry, I encountered an error while tracking your order. Please contact our support team for assistance.")
        
#         return [
#             SlotSet("order_id", None),
#             SlotSet("user_email", None),
#         ]


# class ActionLodgeComplaint(Action):
#     """Action to lodge a complaint"""
    
#     def name(self) -> Text:
#         return "action_lodge_complaint"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         # Log action start
#         logger.info(f"Executing {self.name()} for session {tracker.sender_id}")
        
#         data = {
#             "order_id": tracker.get_slot("order_id"),
#             "user_email": tracker.get_slot("user_email"),
#             "topic": tracker.get_slot("complaint_topic"),
#             "description": tracker.get_slot("complaint_description")
#         }
        
#         # Check for missing fields
#         missing_fields = [field for field, value in data.items() if not value]
#         if missing_fields:
#             logger.warning(f"Missing complaint fields: {missing_fields}")
#             dispatcher.utter_message(text="I need all the complaint details to process your request.")
#             return []
        
#         logger.debug(f"Complaint data: {data}")
        
#         try:
#             # Call API
#             api_response = ApiClient.lodge_complaint(data)
            
#             if api_response:
#                 complaint_id = api_response.get("complaint_id")
#                 message = f"✅ **Complaint Registered Successfully**\n\n"
#                 message += f"🆔 Complaint ID: {complaint_id}\n"
#                 message += f"📋 Order ID: {data['order_id']}\n"
#                 message += f"📧 Email: {data['user_email']}\n"
#                 message += f"🏷️ Topic: {data['topic']}\n"
#                 message += f"📝 Description: {data['description']}\n\n"
#                 message += "Your complaint has been registered and our customer service team will review it within 24 hours. "
#                 message += "You will receive an email update once we have a resolution.\n\n"
#                 message += "Is there anything else I can help you with today?"
                
#                 logger.info(f"Complaint registered: ID={complaint_id}")
#             else:
#                 message = "I couldn't create your complaint. This might be because the order ID or email doesn't match our records. "
#                 message += "Please verify your information or contact our support team directly."
#                 logger.warning("Complaint creation failed")
            
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Error in {self.name()}: {str(e)}", exc_info=True)
#             dispatcher.utter_message(text="I'm sorry, I encountered an error while registering your complaint. Please contact our support team directly.")
        
#         return [
#             SlotSet("order_id", None),
#             SlotSet("user_email", None),
#             SlotSet("complaint_topic", None),
#             SlotSet("complaint_description", None),
#         ]


# class ActionEscalateToHuman(Action):
#     """Action to escalate conversation to human agent"""
    
#     def name(self) -> Text:
#         return "action_escalate_to_human"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
#         # Log action start
#         logger.info(f"Executing {self.name()} for session {tracker.sender_id}")
        
#         events = []
#         if tracker.active_loop:
#             events.append(ActiveLoop(None))  # Deactivate form
#             events.append(SlotSet("requested_slot", None))  # Clear form slot
#             logger.debug("Deactivated active form")
        
#         # Get conversation context
#         data = {
#             "user_email": tracker.get_slot("user_email"),
#             "order_id": tracker.get_slot("order_id"),
#             "conversation_history": [
#                 {"event": e.as_dict().get("event"), "text": e.as_dict().get("text")}
#                 for e in tracker.events
#                 if e.get("event") in ["user", "bot"]
#             ]
#         }
#         logger.debug(f"Escalation context: {json.dumps(data, indent=2)}")
        
#         try:
#             # Call API
#             api_response = ApiClient.escalate(data)
            
#             if api_response:
#                 message = "🤝 **Connecting you to a human agent...**\n\n"
#                 message += "I'm transferring your conversation to our customer service team. "
#                 message += "A human agent will be with you shortly to provide personalized assistance.\n\n"
                
#                 if data.get("user_email") or data.get("order_id"):
#                     message += "**Context being transferred:**\n"
#                     if data.get("user_email"):
#                         message += f"📧 Email: {data['user_email']}\n"
#                     if data.get("order_id"):
#                         message += f"🆔 Order ID: {data['order_id']}\n"
#                     message += "\n"
                
#                 message += "⏱️ Average wait time: 2-3 minutes\n"
#                 message += "📞 Alternatively, you can call us at: 1-800-EARPHONES\n"
#                 message += "📧 Or email: support@earphonesstore.com"
                
#                 logger.info("Successfully escalated to human agent")
#             else:
#                 message = "I'm having trouble connecting you to a human agent right now. "
#                 message += "Please contact our support team directly at:\n"
#                 message += "📞 Phone: 1-800-EARPHONES\n"
#                 message += "📧 Email: support@earphonesstore.com"
                
#                 logger.warning("Escalation API call failed")
            
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Error in {self.name()}: {str(e)}", exc_info=True)
#             dispatcher.utter_message(text="I encountered an issue while trying to connect you to a human agent. Please contact us directly at 1-800-EARPHONES.")
        
#         return events


# # Form validation actions with logging
# class ValidateOrderTrackingForm(FormValidationAction):
#     """Validates the order tracking form"""
    
#     def name(self) -> Text:
#         return "validate_order_tracking_form"
    
#     def validate_order_id(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate order_id slot"""
#         logger.info(f"Validating order_id: {slot_value}")
        
#         if slot_value and len(str(slot_value)) >= 3:
#             logger.debug("order_id validation passed")
#             return {"order_id": slot_value}
#         else:
#             logger.warning("Invalid order_id provided")
#             dispatcher.utter_message(text="Please provide a valid order ID (at least 3 characters).")
#             return {"order_id": None}
    
#     def validate_user_email(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate user_email slot"""
#         logger.info(f"Validating email: {slot_value}")
        
#         if slot_value and "@" in slot_value and "." in slot_value:
#             logger.debug("Email validation passed")
#             return {"user_email": slot_value}
#         else:
#             logger.warning("Invalid email provided")
#             dispatcher.utter_message(text="Please provide a valid email address.")
#             return {"user_email": None}


# class ValidateRecommendationForm(FormValidationAction):
#     """Validates the recommendation form"""
    
#     def name(self) -> Text:
#         return "validate_recommendation_form"
    
#     def validate_preferred_brand(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate preferred_brand slot"""
#         logger.info(f"Validating preferred_brand: {slot_value}")
#         valid_brands = ["sony", "apple", "bose", "sennheiser", "jbl", "audio-technica", "samsung", "beats", "anker", "jabra", "any", "no preference"]
        
#         if slot_value:
#             if slot_value.lower() in valid_brands or "any" in slot_value.lower() or "no" in slot_value.lower():
#                 logger.debug("preferred_brand validation passed")
#                 return {"preferred_brand": slot_value}
        
#         logger.debug("Using default 'any' for preferred_brand")
#         return {"preferred_brand": "any"}
    
#     def validate_price_range(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate price_range slot"""
#         logger.info(f"Validating price_range: {slot_value}")
#         if slot_value:
#             price_keywords = ["under", "$", "budget", "cheap", "expensive", "premium", "-"]
#             if any(keyword in slot_value.lower() for keyword in price_keywords):
#                 logger.debug("price_range validation passed")
#                 return {"price_range": slot_value}
        
#         logger.debug("Using default 'any' for price_range")
#         return {"price_range": "any"}
    
#     def validate_product_type(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate product_type slot"""
#         logger.info(f"Validating product_type: {slot_value}")
#         valid_types = ["over-ear", "in-ear", "on-ear", "any"]
        
#         if slot_value:
#             if any(valid_type in slot_value.lower() for valid_type in valid_types):
#                 logger.debug("product_type validation passed")
#                 return {"product_type": slot_value}
        
#         logger.debug("Using default 'any' for product_type")
#         return {"product_type": "any"}
    
#     def validate_features(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate features slot"""
#         logger.info(f"Validating features: {slot_value}")
#         if slot_value:
#             logger.debug("features validation passed")
#             return {"features": slot_value}
#         logger.debug("Using default 'any' for features")
#         return {"features": "any"}


# class ValidateComplaintForm(FormValidationAction):
#     """Validates the complaint form"""
    
#     def name(self) -> Text:
#         return "validate_complaint_form"
    
#     def validate_order_id(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate order_id slot"""
#         logger.info(f"Validating complaint order_id: {slot_value}")
#         if slot_value and len(str(slot_value)) >= 3:
#             logger.debug("order_id validation passed")
#             return {"order_id": slot_value}
#         else:
#             logger.warning("Invalid complaint order_id provided")
#             dispatcher.utter_message(text="Please provide a valid order ID.")
#             return {"order_id": None}
    
#     def validate_user_email(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate user_email slot"""
#         logger.info(f"Validating complaint email: {slot_value}")
#         if slot_value and "@" in slot_value and "." in slot_value:
#             logger.debug("Email validation passed")
#             return {"user_email": slot_value}
#         else:
#             logger.warning("Invalid complaint email provided")
#             dispatcher.utter_message(text="Please provide a valid email address.")
#             return {"user_email": None}
    
#     def validate_complaint_topic(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate complaint_topic slot"""
#         logger.info(f"Validating complaint_topic: {slot_value}")
#         valid_topics = ["product quality", "shipping", "customer service", "billing", "returns", "technical issue"]
        
#         if slot_value:
#             if any(topic in slot_value.lower() for topic in valid_topics):
#                 logger.debug("complaint_topic validation passed")
#                 return {"complaint_topic": slot_value}
        
#         logger.debug("Using provided complaint_topic without validation")
#         return {"complaint_topic": slot_value if slot_value else None}
    
#     def validate_complaint_description(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate complaint_description slot"""
#         logger.info(f"Validating complaint_description: {slot_value}")
#         if slot_value and len(slot_value) >= 10:
#             logger.debug("complaint_description validation passed")
#             return {"complaint_description": slot_value}
#         else:
#             logger.warning("Invalid complaint_description provided")
#             dispatcher.utter_message(text="Please provide more details about your complaint (at least 10 characters).")
#             return {"complaint_description": None}


# class ValidateSearchForm(FormValidationAction):
#     """Validates the search form"""
    
#     def name(self) -> Text:
#         return "validate_search_form"
    
#     def validate_search_query(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate search_query slot"""
#         logger.info(f"Validating search_query: {slot_value}")
#         if slot_value and len(slot_value) >= 2:
#             logger.debug("search_query validation passed")
#             return {"search_query": slot_value}
#         else:
#             logger.warning("Invalid search_query provided")
#             dispatcher.utter_message(text="Please provide a search term (at least 2 characters).")
#             return {"search_query": None}


# # Add a shutdown handler to log when the actions server stops
# import atexit

# @atexit.register
# def shutdown_log():
#     logger.info("====== Stopping Rasa Actions Server ======")


#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
###############################  ACTIONS AFTER FASTAPI  #########################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################

# import logging
# from typing import Any, Text, Dict, List
# import requests
# from rasa_sdk import Action, Tracker, FormValidationAction
# from rasa_sdk.executor import CollectingDispatcher
# from rasa_sdk.types import DomainDict
# from rasa_sdk.events import SlotSet, ActiveLoop, ActionExecuted

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# FASTAPI_URL = "http://localhost:8000"  # Update with your deployment URL

# class ActionSearchProducts(Action):    
#     def name(self) -> Text:
#         return "action_search_products"
    
#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         params = {
#             "query": tracker.get_slot("search_query"),
#             "brand": tracker.get_slot("preferred_brand"),
#             "price_range": tracker.get_slot("price_range"),
#             "product_type": tracker.get_slot("product_type"),
#             "features": tracker.get_slot("features")
#         }
        
#         try:
#             response = requests.post(f"{FASTAPI_URL}/search_products", json=params)
#             response.raise_for_status()
#             products = response.json().get("products", [])
            
#             if products:
#                 message = "Here are the earphones I found for you:\n\n"
#                 for product in products:
#                     message += f"🎧 **{product['name']}** by {product['brand']}\n"
#                     message += f"   💰 Price: ${product['price']:.2f}\n"
#                     message += f"   ⭐ Rating: {product['rating']}/5\n"
#                     message += f"   📦 Stock: {product['stock']} units\n"
#                     message += f"   🏷️ Features: {product['features']}\n\n"
#                 message += "Would you like more details about any of these products?"
#             else:
#                 message = "No matching products found. Try different criteria?"
                
#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Search error: {str(e)}")
#             dispatcher.utter_message(text="I'm having trouble searching right now. Please try again later.")
#         finally:
#             return [
#                 SlotSet("search_query", None),
#                 SlotSet("preferred_brand", None),
#                 SlotSet("price_range", None),
#                 SlotSet("product_type", None),
#                 SlotSet("features", None)
#             ]

# class ActionTrackOrder(Action):
#     def name(self) -> Text:
#         return "action_track_order"
    
#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         order_id = tracker.get_slot("order_id")
#         email = tracker.get_slot("user_email")
        
#         if not order_id or not email:
#             dispatcher.utter_message(text="I need both order ID and email to track your order.")
#             return []
        
#         try:
#             email = "ATSYMB".join(email.split("@"))
#             response = requests.get(
#                 f"{FASTAPI_URL}/order_status",
#                 params={"order_id": order_id, "email": email}
#             )
            
#             if response.status_code == 404:
#                 dispatcher.utter_message(text="Order not found. Please check your details.")
#                 return [SlotSet("order_id", None), SlotSet("user_email", None)]
                
#             response.raise_for_status()
#             order = response.json()
            
#             status = order[4]  # status column
#             order_amount = order[3]  # order_amount column
#             created_time = order[5]  # created_time column
#             shipping_address = order[2]  # shipping_address column
            
#             status_emoji = {
#                 "processing": "⏳",
#                 "shipped": "🚚",
#                 "delivered": "✅",
#                 "cancelled": "❌"
#             }.get(status.lower(), "📦")
            
#             message = f"📋 **Order Status Update**\n\n"
#             message += f"🆔 Order ID: {order_id}\n"
#             message += f"{status_emoji} Status: **{status.upper()}**\n"
#             message += f"💰 Amount: ${order_amount:.2f}\n"
#             message += f"📅 Order Date: {created_time}\n"
#             message += f"🏠 Shipping Address: {shipping_address}\n\n"
            
#             if status.lower() == "processing":
#                 message += "Your order is being prepared and will ship soon!"
#             elif status.lower() == "shipped":
#                 message += "Your order is on its way! You should receive it in 2-3 business days."
#             elif status.lower() == "delivered":
#                 message += "Your order has been delivered! We hope you enjoy your new earphones!"
#             elif status.lower() == "cancelled":
#                 message += "Your order has been cancelled. If you have questions, please contact our support team."
#             else:
#                 message = f"I couldn't find an order with ID {order_id} associated with email {email}. Please check your order ID and email address, or contact our support team for assistance."
                
# #             dispatcher.utter_message(text=message)

#             dispatcher.utter_message(text=message)
            
#         except Exception as e:
#             logger.error(f"Tracking error: {str(e)}")
#             dispatcher.utter_message(text=f"I'm having trouble accessing your order details.{str(e)}")
        
#         return [SlotSet("order_id", None), SlotSet("user_email", None)]

# class ActionLodgeComplaint(Action):
#     def name(self) -> Text:
#         return "action_lodge_complaint"
    
#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         complaint_data = {
#             "order_id": tracker.get_slot("order_id"),
#             "user_email": tracker.get_slot("user_email"),
#             "topic": tracker.get_slot("complaint_topic"),
#             "description": tracker.get_slot("complaint_description")
#         }
        
#         try:
#             response = requests.post(
#                 f"{FASTAPI_URL}/create_complaint",
#                 json=complaint_data
#             )
#             response.raise_for_status()
            
#             comp_id = response.json().get("complaint_id")
#             dispatcher.utter_message(
#                 text=f"Complaint #{comp_id} registered successfully! Our team will contact you soon."
#             )
            
#         except Exception as e:
#             logger.error(f"Complaint error: {str(e)}")
#             dispatcher.utter_message(text="Failed to register complaint. Please try again later.")
        
#         return [
#             SlotSet("order_id", None),
#             SlotSet("user_email", None),
#             SlotSet("complaint_topic", None),
#             SlotSet("complaint_description", None)
#         ]

# # Keep all FormValidationActions and other actions unchanged below
# # [Include all your FormValidationAction classes here without changes]

# # Form validation actions

# class ValidateOrderTrackingForm(FormValidationAction):
#     """Validates the order tracking form"""
    
#     def name(self) -> Text:
#         return "validate_order_tracking_form"
    
#     def validate_order_id(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate order_id slot"""
#         if slot_value and len(str(slot_value)) >= 3:
#             return {"order_id": slot_value}
#         else:
#             dispatcher.utter_message(text="Please provide a valid order ID (at least 3 characters).")
#             return {"order_id": None}
    
#     def validate_user_email(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate user_email slot"""
#         if slot_value and "@" in slot_value and "." in slot_value:
#             return {"user_email": slot_value}
#         else:
#             dispatcher.utter_message(text="Please provide a valid email address.")
#             return {"user_email": None}


# class ValidateRecommendationForm(FormValidationAction):
#     """Validates the recommendation form"""
    
#     def name(self) -> Text:
#         return "validate_recommendation_form"
    
#     def validate_preferred_brand(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate preferred_brand slot"""
#         valid_brands = ["sony", "apple", "bose", "sennheiser", "jbl", "audio-technica", "samsung", "beats", "anker", "jabra", "any", "no preference"]
        
#         if slot_value:
#             if slot_value.lower() in valid_brands or "any" in slot_value.lower() or "no" in slot_value.lower():
#                 return {"preferred_brand": slot_value}
        
#         return {"preferred_brand": "any"}
    
#     def validate_price_range(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate price_range slot"""
#         if slot_value:
#             price_keywords = ["under", "$", "budget", "cheap", "expensive", "premium", "-"]
#             if any(keyword in slot_value.lower() for keyword in price_keywords):
#                 return {"price_range": slot_value}
        
#         return {"price_range": "any"}
    
#     def validate_product_type(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate product_type slot"""
#         valid_types = ["over-ear", "in-ear", "on-ear", "any"]
        
#         if slot_value:
#             if any(valid_type in slot_value.lower() for valid_type in valid_types):
#                 return {"product_type": slot_value}
        
#         return {"product_type": "any"}
    
#     def validate_features(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate features slot"""
#         if slot_value:
#             return {"features": slot_value}
#         return {"features": "any"}


# class ValidateComplaintForm(FormValidationAction):
#     """Validates the complaint form"""
    
#     def name(self) -> Text:
#         return "validate_complaint_form"
    
#     def validate_order_id(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate order_id slot"""
#         if slot_value and len(str(slot_value)) >= 3:
#             return {"order_id": slot_value}
#         else:
#             dispatcher.utter_message(text="Please provide a valid order ID.")
#             return {"order_id": None}
    
#     def validate_user_email(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate user_email slot"""
#         if slot_value and "@" in slot_value and "." in slot_value:
#             return {"user_email": slot_value}
#         else:
#             dispatcher.utter_message(text="Please provide a valid email address.")
#             return {"user_email": None}
    
#     def validate_complaint_topic(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate complaint_topic slot"""
#         valid_topics = ["product quality", "shipping", "customer service", "billing", "returns", "technical issue"]
        
#         if slot_value:
#             if any(topic in slot_value.lower() for topic in valid_topics):
#                 return {"complaint_topic": slot_value}
        
#         return {"complaint_topic": slot_value if slot_value else None}
    
#     def validate_complaint_description(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate complaint_description slot"""
#         if slot_value and len(slot_value) >= 10:
#             return {"complaint_description": slot_value}
#         else:
#             dispatcher.utter_message(text="Please provide more details about your complaint (at least 10 characters).")
#             return {"complaint_description": None}


# class ValidateSearchForm(FormValidationAction):
#     """Validates the search form"""
    
#     def name(self) -> Text:
#         return "validate_search_form"
    
#     def validate_search_query(
#         self,
#         slot_value: Any,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: DomainDict,
#     ) -> Dict[Text, Any]:
#         """Validate search_query slot"""
#         if slot_value and len(slot_value) >= 2:
#             return {"search_query": slot_value}
#         else:
#             dispatcher.utter_message(text="Please provide a search term (at least 2 characters).")
#             return {"search_query": None}

