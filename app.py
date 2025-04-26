from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import mysql.connector

app = Flask(__name__)
app.secret_key = '1234'  # Needed for session handling

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'ASt14@20',
    'database': 'restaurant_management'
}

# Test database connection at startup
def test_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        connection.close()
        print("Database connection successful!")
        return True
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return False

@app.route('/')
def home():
    return render_template('signup.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/veg')
def veg():
    return render_template('veg.html')

@app.route('/nonveg')
def nonveg():
    return render_template('nonveg.html')

@app.route('/snacks')
def snacks():
    return render_template('snacks.html')

@app.route('/beverages')
def beverages():
    return render_template('beverages.html')

@app.route('/menu')
def menu():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items")
        items = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('menu.html', items=items)
    except mysql.connector.Error as err:
        return f"Database error: {err}", 500

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
        
    try:
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
        if not all([username, email, password]):
            return "All fields are required", 400
            
        password_hash = generate_password_hash(password)

        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM user WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            error_msg = "Username or email already exists"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            return error_msg, 400
        
        # Insert new user
        cursor.execute(
            "INSERT INTO user (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        connection.commit()
        
        if request.is_json:
            return jsonify({"success": "Signup successful"}), 200
        return redirect(url_for('index'))
        
    except mysql.connector.Error as err:
        error_msg = f"Database error: {str(err)}"
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        return error_msg, 500
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        return error_msg, 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        username = request.form.get('username')
        password_input = request.form.get('password')
        
        if not all([username, password_input]):
            return "Username and password are required", 400
        
        # Connect to database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        # Query the user table
        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        # Check if user exists and password matches
        if user and check_password_hash(user['password'], password_input):
            # Store user info in session
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            return "Invalid username or password", 401
            
    except mysql.connector.Error as err:
        return f"Database error: {str(err)}", 500
    except Exception as err:
        return f"Error: {str(err)}", 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    try:
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])

        # Validate inputs
        if item_id <= 0 or quantity <= 0:
            return "Invalid item ID or quantity", 400

        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
        item = cursor.fetchone()
        
        if item:
            # Initialize cart if it doesn't exist
            if 'cart' not in session:
                session['cart'] = []
                
            cart = session['cart']
            
            # Check if item already exists in cart
            item_exists = False
            for cart_item in cart:
                if cart_item.get('item_id') == item_id:
                    cart_item['quantity'] += quantity
                    item_exists = True
                    break
                    
            # Add new item to cart if it doesn't exist
            if not item_exists:
                cart.append({
                    'item_id': item['item_id'],
                    'name': item['item_name'],
                    'price': float(item['price']),
                    'quantity': quantity
                })
                
            session['cart'] = cart
            print(f"Updated cart: {session['cart']}")  # Debugging
            
            return redirect(url_for('menu'))
        else:
            return f"Item with ID {item_id} not found", 404
            
    except ValueError as e:
        return f"Invalid input: {str(e)}", 400
    except mysql.connector.Error as err:
        return f"Database error: {str(err)}", 500
    except Exception as e:
        return f"Error: {str(e)}", 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route("/cart")
def cart():
    return render_template("cart.html")

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    return render_template("checkout.html")

@app.route('/submit_customer', methods=['POST'])
def submit_customer():
    try:
        # Get data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data received'
            }), 400
            
        # Extract required fields
        name = data.get('name')
        address = data.get('address')
        phone_no = data.get('phone_no')
        email = data.get('email')
        delivery_option = data.get('delivery_option')
        payment_method = data.get('payment_method')  # Store for session, not DB
        
        # Validate required fields
        if not all([name, address, phone_no, email, delivery_option]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

        # Validate email format (basic check)
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400

        # Validate phone number (basic check for digits and length)
        if not phone_no.isdigit() or len(phone_no) < 10:
            return jsonify({
                'success': False,
                'error': 'Invalid phone number'
            }), 400

        # Validate delivery_option
        if delivery_option not in ['standard', 'express']:
            return jsonify({
                'success': False,
                'error': 'Invalid delivery option'
            }), 400

        # Get user_id if logged in
        user_id = session.get('user_id')
        
        # Create database connection
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        # Build the query based on whether user_id exists
        if user_id:
            query = """
                INSERT INTO customer 
                (name, address, phone_no, email, delivery_option, user_id) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (name, address, phone_no, email, delivery_option, user_id)
        else:
            query = """
                INSERT INTO customer 
                (name, address, phone_no, email, delivery_option) 
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (name, address, phone_no, email, delivery_option)
        
        cursor.execute(query, values)
        connection.commit()
        
        customer_id = cursor.lastrowid
        
        # Store customer details in session
        customer_details = {
            'customer_id': customer_id,
            'name': name,
            'address': address, 
            'phone_no': phone_no,
            'email': email,
            'delivery_option': delivery_option,
            'payment_method': payment_method  # Include payment_method
        }
        session['customer_details'] = customer_details
        
        return jsonify({
            'success': True,
            'customer_id': customer_id
        })
        
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        return jsonify({
            'success': False,
            'error': f"Database error: {str(err)}"
        }), 500
    
    except Exception as e: 
        print(f"General exception in submit_customer: {e}")
        return jsonify({
            'success': False, 
            'error': f"Error: {str(e)}"
        }), 500
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/place-order', methods=['POST'])
def place_order():
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if data is None:
            return jsonify({"success": False, "error": "Invalid JSON data"}), 400
        
        # Extract data
        user_id = session.get('user_id')
        customer_id = data.get('customer_id')
        total_amount = data.get('total_amount')
        cart_items = data.get('cart_items', [])

        print(f"Received cart items: {cart_items}")  # Debugging
    
        if not customer_id:
            return jsonify({"success": False, "error": "Customer information is missing"}), 400
            
        # Create database connection
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Insert into orders table
        current_date = datetime.now()
        
        # If user_id is None, insert NULL
        if user_id is None:
            cursor.execute("""
                INSERT INTO orders (bill_amt, order_date)
                VALUES (%s, %s)
            """, (total_amount, current_date))
        else:
            cursor.execute("""
                INSERT INTO orders (user_id, bill_amt, order_date)
                VALUES (%s, %s, %s)
            """, (user_id, total_amount, current_date))
        
        # Get the generated order_id
        order_id = cursor.lastrowid
        connection.commit()
        
        # Insert order details for each item
        for item in cart_items:
            # Properly extract item_id and validate it's not None
            item_id = item.get('item_id')
            
            if item_id is None:
                print(f"Warning: Skipping order detail with missing item_id: {item}")
                continue
                
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)
            
            cursor.execute("""
                INSERT INTO order_details (order_id, item_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item_id, quantity, price))
            print(f"Inserted order detail: order_id={order_id}, item_id={item_id}, quantity={quantity}, price={price}")
        
        connection.commit()
        
        # Store order ID in session for confirmation page
        session['order_id'] = order_id
        
        return jsonify({"success": True, "orderId": order_id})
    except mysql.connector.Error as err:
        print(f"Database error in place_order: {str(err)}")  # Log the error
        return jsonify({"success": False, "error": f"Database error: {str(err)}"}), 500
    except Exception as e:
        print(f"Order placement error: {str(e)}")  # Log the error
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.route('/order-confirmation')
def order_confirmation():
    order_id = request.args.get('orderId', session.get('order_id'))
    
    # Use customer details from session or fetch from DB
    customer_details = session.get('customer_details', {})
    
    # You could also fetch order details from database
    try:
        if order_id:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            
            # Get order info
            cursor.execute("""
                SELECT o.*, c.name, c.address, c.phone_no, c.email, c.delivery_option, c.payment_method
                FROM orders o
                JOIN customer c ON o.user_id = c.user_id
                WHERE o.order_id = %s
                ORDER BY c.customer_id DESC LIMIT 1
            """, (order_id,))
            
            order_data = cursor.fetchone()
            
            if order_data:
                # Merge any additional data
                for key, value in order_data.items():
                    if key not in customer_details:
                        customer_details[key] = value
    except Exception as e:
        print(f"Error fetching order details: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    return render_template('order-confirmation.html', 
                           customer=customer_details,
                           order_id=order_id)

if __name__ == '__main__':
    # Test database connection before starting the app
    if test_db_connection():
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Error: Could not connect to database. Please check your database configuration.")