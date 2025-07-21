import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# MySQL database configuration
db_config = {
    'user': 'root',
    'password': 'root',
    'host': 'localhost',
    'database': 'bus_reservation'
}

# Helper function to connect to the database
def get_db_connection():
    connection = mysql.connector.connect(**db_config)
    return connection

# Initialize the MySQL database tables if they don't exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        phone VARCHAR(20) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL
    )''')

    # Create buses table
    cursor.execute('''CREATE TABLE IF NOT EXISTS buses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        bus_name VARCHAR(255) NOT NULL,
        source VARCHAR(255) NOT NULL,
        destination VARCHAR(255) NOT NULL,
        available_seats INT NOT NULL,
        cost_per_seat DECIMAL(10, 2) NOT NULL,
        total_kms INT,
        start_time TIME,
        end_time TIME,
        travel_time VARCHAR(10)
    )''')

    # Create seats table
    cursor.execute('''CREATE TABLE IF NOT EXISTS seats (
        seat_no INT,
        bus_id INT,
        status ENUM('Available', 'Booked') DEFAULT 'Available',
        price DECIMAL(10,2),
        gender ENUM('Male', 'Female') DEFAULT 'Male',
        column_no INT,
        row_no INT,
        PRIMARY KEY (seat_no, bus_id),
        FOREIGN KEY (bus_id) REFERENCES buses(id)
    )''')

    # Create reservations table
    cursor.execute('''CREATE TABLE IF NOT EXISTS reservations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        bus_id INT,
        seat_no INT,
        cost DECIMAL(10, 2),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (bus_id) REFERENCES buses(id)
    )''')

    # Insert dummy bus if table is empty
    cursor.execute("SELECT COUNT(*) FROM buses")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''INSERT INTO buses (bus_name, source, destination, available_seats, cost_per_seat, total_kms, start_time, end_time, travel_time)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                       ("Subash Express", "Tiruvannamalai", "Chennai", 40, 120.00, 190, "07:00:00", "11:00:00", "4h"))

        # Insert 40 seats for the bus
        for seat_no in range(1, 41):
            cursor.execute('''INSERT INTO seats (seat_no, bus_id, status, price, gender, column_no, row_no)
                              VALUES (%s, %s, 'Available', %s, 'Male', %s, %s)''',
                           (seat_no, 1, 120.00, (seat_no - 1) % 4, (seat_no - 1) // 4))

    conn.commit()
    cursor.close()
    conn.close()


# -------------------- Routes --------------------

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data['name']
    email = data['email']
    phone = data['phone']
    password = data['password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if email or phone already exists
    cursor.execute('SELECT * FROM users WHERE email=%s OR phone=%s', (email, phone))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        return jsonify({"message": "Email or phone number already exists!"}), 400

    # Insert new user
    cursor.execute('INSERT INTO users (name, email, phone, password) VALUES (%s, %s, %s, %s)', 
                   (name, email, phone, password))
    conn.commit()

    cursor.close()
    conn.close()
    
    return jsonify({"message": "Registration successful!"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    phone = data['phone']
    password = data['password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check login credentials
    cursor.execute('SELECT id, name, wallet_amount FROM users WHERE phone=%s AND password=%s', (phone, password))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        return jsonify({
            "message": "Login successful",
            "user_id": user[0],
            "name": user[1],
            "wallet_amount": float(user[2])
        }), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401


@app.route('/buses', methods=['GET'])
def get_buses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Update the column names to match the actual database schema
        cursor.execute('''SELECT id, bus_name, from_location, to_location, 
                          total_seats AS available_seats,  distance_km, 
                          start_time, end_time, duration FROM buses''')
        buses = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify([{
            'id': bus[0],
            'bus_name': bus[1],
            'start_location': bus[2],
            'end_location': bus[3],
            'available_seats': bus[4],
            'distance_km': bus[5],
            'start_time': str(bus[6]),
            'end_time': str(bus[7]),
            'travel_time': bus[8]
        } for bus in buses])

    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())
        return jsonify({"message": "An error occurred while fetching buses."}), 500


@app.route('/seats/<int:bus_id>', methods=['GET'])
def get_seats(bus_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT seat_no, status, price, gender, column_no, row_no FROM seats WHERE bus_id=%s', (bus_id,))
    seats = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify([{
        'seat_no': seat[0],
        'status': seat[1],
        'price': float(seat[2]),
        'gender': seat[3],
        'column_no': seat[4],
        'row_no': seat[5]
    } for seat in seats])


@app.route('/reserve', methods=['POST'])
def reserve_seat():
    data = request.get_json()
    user_id = data['user_id']
    bus_id = data['bus_id']
    seat_no = data['seat_no']
    cost = data['cost']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT status FROM seats WHERE bus_id=%s AND seat_no=%s', (bus_id, seat_no))
    seat = cursor.fetchone()

    if not seat or seat[0] == 'Booked':
        cursor.close()
        conn.close()
        return jsonify({'message': 'Seat is already booked or does not exist'}), 400

    cursor.execute('INSERT INTO reservations (user_id, bus_id, seat_no, cost) VALUES (%s, %s, %s, %s)', 
                   (user_id, bus_id, seat_no, cost))
    cursor.execute('UPDATE seats SET status=%s WHERE bus_id=%s AND seat_no=%s', 
                   ('Booked', bus_id, seat_no))
    cursor.execute('UPDATE buses SET available_seats = available_seats - 1 WHERE id=%s', (bus_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Seat reserved successfully'}), 200


@app.route('/myreservations/<int:user_id>', methods=['GET'])
def get_user_reservations(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Adjust the query to include bus_id
        cursor.execute('''
            SELECT r.id, r.seat_no, r.cost, r.bus_id, b.bus_name, b.from_location, b.to_location, b.start_time, b.end_time
            FROM reservations r
            JOIN buses b ON r.bus_id = b.id
            WHERE r.user_id = %s
        ''', (user_id,))
        reservations = cursor.fetchall()

        if not reservations:
            return jsonify({"message": "No reservations found for this user."}), 404

        cursor.close()
        conn.close()

        return jsonify([{
            'reservation_id': res[0],
            'seat_no': res[1],
            'cost': float(res[2]),
            'bus_id': res[3],
            'bus_name': res[4],
            'from_location': res[5],
            'to_location': res[6],
            'start_time': str(res[7]),
            'end_time': str(res[8])
        } for res in reservations])

    except mysql.connector.Error as db_err:
        print(f"Database error in /myreservations/{user_id}: {db_err}")
        print(traceback.format_exc())
        return jsonify({"message": "A database error occurred."}), 500

    except Exception as e:
        print(f"Error in /myreservations/{user_id}: {e}")
        print(traceback.format_exc())
        return jsonify({"message": "An unexpected error occurred."}), 500


@app.route('/cancel', methods=['POST'])
def cancel_reservation():
    try:
        data = request.get_json()
        seat_no = data.get('seat_no')
        bus_id = data.get('bus_id')

        if not seat_no or not bus_id:
            return jsonify({'message': 'seat_no and bus_id are required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the reservation exists
        cursor.execute('SELECT id FROM reservations WHERE seat_no = %s AND bus_id = %s', (seat_no, bus_id))
        reservation = cursor.fetchone()

        if not reservation:
            cursor.close()
            conn.close()
            return jsonify({'message': 'Reservation not found'}), 404

        reservation_id = reservation[0]

        # Delete the reservation
        cursor.execute('DELETE FROM reservations WHERE id = %s', (reservation_id,))

        # Update the seat status to 'Available'
        cursor.execute('UPDATE seats SET status = %s WHERE bus_id = %s AND seat_no = %s', 
                       ('Available', bus_id, seat_no))

        # Increment the total seats in the buses table (if applicable)
        # Note: This assumes total_seats represents available seats
        cursor.execute('UPDATE buses SET total_seats = total_seats + 1 WHERE id = %s', (bus_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Reservation cancelled successfully'}), 200

    except mysql.connector.Error as db_err:
        print(f"Database error in /cancel: {db_err}")
        print(traceback.format_exc())
        return jsonify({"message": "A database error occurred."}), 500

    except Exception as e:
        print(f"Error in /cancel: {e}")
        print(traceback.format_exc())
        return jsonify({"message": "An unexpected error occurred."}), 500


@app.route('/book-seats', methods=['POST'])
def book_seats():
    try:
        data = request.get_json()
        user_id = data['user_id']
        bus_id = data['bus_id']
        seat_ids = data['seat_ids']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if all seats are available
        cursor.execute('SELECT seat_no, status FROM seats WHERE bus_id=%s AND seat_no IN (%s)' % (
            bus_id, ','.join(map(str, seat_ids))))
        seats = cursor.fetchall()

        for seat in seats:
            if seat[1] == 'Booked':
                return jsonify({"message": f"Seat {seat[0]} is already booked."}), 400

        # Reserve the seats
        total_cost = 0
        for seat_no in seat_ids:
            cursor.execute('UPDATE seats SET status="Booked" WHERE bus_id=%s AND seat_no=%s', (bus_id, seat_no))
            cursor.execute('INSERT INTO reservations (user_id, bus_id, seat_no, cost) VALUES (%s, %s, %s, %s)',
                           (user_id, bus_id, seat_no, 150))  # Assuming cost is 150 per seat
            total_cost += 150

        conn.commit()

        # Fetch the total number of booked seats and total cost for the bus
        cursor.execute('SELECT COUNT(*), SUM(cost) FROM reservations WHERE bus_id=%s', (bus_id,))
        result = cursor.fetchone()
        total_seats_booked = result[0]
        total_amount = float(result[1]) if result[1] else 0.0

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Seats booked successfully!",
            "total_seats_booked": total_seats_booked,
            "total_amount": total_amount
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())
        return jsonify({"message": "An error occurred while booking seats."}), 500


@app.route('/user/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user details
        cursor.execute('''
            SELECT id, name, email, phone, wallet_amount
            FROM users
            WHERE id = %s
        ''', (user_id,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if not user:
            return jsonify({"message": "User not found"}), 404

        return jsonify({
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "phone": user[3],
            "wallet_amount": float(user[4])
        }), 200

    except mysql.connector.Error as db_err:
        print(f"Database error in /user/{user_id}: {db_err}")
        print(traceback.format_exc())
        return jsonify({"message": "A database error occurred."}), 500

    except Exception as e:
        print(f"Error in /user/{user_id}: {e}")
        print(traceback.format_exc())
        return jsonify({"message": "An unexpected error occurred."}), 500


# Run the app
if __name__ == '__main__':
    init_db()  # Initialize the database on first run
    app.run(debug=True)