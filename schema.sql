CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(50) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    balance DECIMAL(10, 2) DEFAULT 1000.00
);
CREATE TABLE movies (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    poster_url TEXT,
    price DECIMAL(10, 2) DEFAULT 100.00
);
CREATE TABLE seats (
    id SERIAL PRIMARY KEY,
    row_num INT NOT NULL,
    seat_num INT NOT NULL
);
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    movie_id INT REFERENCES movies(id),
    seat_id INT REFERENCES seats(id),
    is_paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(movie_id, seat_id)
);
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(50),
    details TEXT,
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);