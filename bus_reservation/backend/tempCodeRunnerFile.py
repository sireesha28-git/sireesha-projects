import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Request Sharing

# MySQL database configuration
db_config = {
    'user': 'root',
    'password': 'root',
    'host': 'localhost',
    'database': 'reservation_system'
}

# Helper function to connect to the database
def get_db_connection():
    connection = mysql.connector.connect(**db_config)
    return connection

# Initialize the MySQL database tables if they don't exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create the users table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL
    )''')
    
    # Create the buses table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS buses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        bus_name VARCHAR(255) NOT NULL,
        source VARCHAR(255) NOT NULL,
        destination VARCHAR(255) NOT NULL,
        available_seats INT NOT NULL,
        cost_per_seat DECIMAL(10, 2) NOT NULL
    )''')

    # Create the seats table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS seats (
        seat_no INT PRIMARY KEY,
        bus_id INT,
        status ENUM('Available', 'Booked') DEFAULT 'Available',
        FOREIGN KEY (bus_id) REFERENCES buses(id)
    )''')

    # Create the reservations table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        bus_id INT,
        seat_no INT,
        cost DECIMAL(10, 2),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (bus_id) REFERENCES buses(id)
    )''')

    conn.commit()
    cursor.close()
    conn.close()

# Route to fetch available buses
@app.route('/buses', methods=['GET'])
def get_buses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, bus_name, source, destination, available_seats, cost_per_seat FROM buses')
    buses = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([{
        'id': bus[0],
        'bus_name': bus[1],
        'source': bus[2],
        'destination': bus[3],
        'available_seats': bus[4],
        'cost_per_seat': bus[5]
    } for bus in buses])

# Route to register a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data['name']
    email = data['email']
    password = data['password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email=%s', (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        return jsonify({"message": "Email already exists!"}), 400

    cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', (name, email, password))
    conn.commit()

    cursor.close()
    conn.close()
    
    return jsonify({"message": "Registration successful!"}), 201

# Route to log in a user
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email=%s AND password=%s', (email, password))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        return jsonify({"message": "Login successful", "user_id": user[0]}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401

# Route to fetch available seats for a specific bus
@app.route('/seats/<int:bus_id>', methods=['GET'])
def get_seats(bus_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT seat_no, status FROM seats WHERE bus_id=%s', (bus_id,))
    seats = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        'seats': [{'seat_no': seat[0], 'status': seat[1]} for seat in seats]
    })

# Route to reserve a seat
@app.route('/reserve', methods=['POST'])
def reserve_seat():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        print("Request Data:", data)  # Debugging line
        user_id = data['user_id']
        bus_id = data['bus_id']
        seat_no = data['seat_no']
        cost = data['cost']

        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the seat exists and is available
        cursor.execute('SELECT status FROM seats WHERE bus_id=%s AND seat_no=%s', (bus_id, seat_no))
        seat = cursor.fetchone()
        print("Seat Data:", seat)  # Debugging line

        if seat is None:
            return jsonify({"message": "Seat does not exist."}), 400
        if seat[0] == 'Booked':
            return jsonify({"message": "Seat is already booked."}), 400

        # Proceed to reserve the seat
        cursor.execute('UPDATE seats SET status = "Booked" WHERE bus_id=%s AND seat_no=%s', (bus_id, seat_no))
        cursor.execute('INSERT INTO reservations (user_id, bus_id, seat_no, cost) VALUES (%s, %s, %s, %s)',
                    (user_id, bus_id, seat_no, cost))
        
        conn.commit()
        print("Reservation successful")  # Debugging line

        return jsonify({"message": "Reservation successful!"}), 200

    except Exception as e:
        print(f"Error: {e}")
        print(f"Stack Trace: {traceback.format_exc()}")
        return jsonify({"message": "An error occurred during reservation."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    init_db()  # Initialize the database tables if needed
    app.run(debug=True) 