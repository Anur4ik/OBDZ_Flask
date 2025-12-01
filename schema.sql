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
    movie_id INT REFERENCES movies(id) ON DELETE CASCADE,
    row_num INT NOT NULL,
    seat_num INT NOT NULL
);
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    movie_id INT REFERENCES movies(id),
    seat_id INT REFERENCES seats(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(movie_id, seat_id)
);
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(50),
    details TEXT,
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE OR REPLACE PROCEDURE register_user_proc(p_username VARCHAR, p_password VARCHAR)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO users (username, password, balance) VALUES (p_username, p_password, 5000.00);
END;
$$;



CREATE OR REPLACE PROCEDURE buy_ticket_proc(p_user_id INT, p_movie_id INT, p_seat_id INT)
LANGUAGE plpgsql AS $$
DECLARE
    v_price DECIMAL;
    v_balance DECIMAL;
    v_exists INT;
BEGIN
    SELECT 1 INTO v_exists FROM bookings
    WHERE movie_id = p_movie_id AND seat_id = p_seat_id;

    IF v_exists IS NOT NULL THEN
        RAISE EXCEPTION 'Це місце вже куплено!';
    END IF;

    SELECT price INTO v_price FROM movies WHERE id = p_movie_id;
    SELECT balance INTO v_balance FROM users WHERE id = p_user_id;

    IF v_balance >= v_price THEN
        UPDATE users SET balance = balance - v_price WHERE id = p_user_id;
        INSERT INTO bookings (user_id, movie_id, seat_id)
        VALUES (p_user_id, p_movie_id, p_seat_id);
    ELSE
        RAISE EXCEPTION 'Недостатньо грошей!';
    END IF;
END;
$$;

CREATE OR REPLACE PROCEDURE add_movie_proc(
    p_title VARCHAR,
    p_poster TEXT,
    p_price DECIMAL,
    p_rows INT,
    p_seats_per_row INT
)
LANGUAGE plpgsql AS $$
DECLARE
    new_movie_id INT;
BEGIN
    INSERT INTO movies (title, poster_url, price)
    VALUES (p_title, p_poster, p_price)
    RETURNING id INTO new_movie_id;
    FOR r IN 1..p_rows LOOP
        FOR s IN 1..p_seats_per_row LOOP
            INSERT INTO seats (movie_id, row_num, seat_num)
            VALUES (new_movie_id, r, s);
        END LOOP;
    END LOOP;
END;
$$;
CREATE OR REPLACE PROCEDURE delete_movie_proc(p_movie_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM bookings WHERE movie_id = p_movie_id;

    DELETE FROM seats WHERE movie_id = p_movie_id;


    DELETE FROM movies WHERE id = p_movie_id;
END;
$$;
CREATE OR REPLACE PROCEDURE edit_movie_proc(
    p_id INT,
    p_title VARCHAR,
    p_poster TEXT,
    p_price DECIMAL
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE movies
    SET title = p_title,
        poster_url = p_poster,
        price = p_price
    WHERE id = p_id;
END;
$$;


CREATE OR REPLACE FUNCTION log_booking_func() RETURNS TRIGGER AS $$
DECLARE
    v_movie_title VARCHAR;
BEGIN
SELECT title INTO v_movie_title FROM movies WHERE id = NEW.movie_id;
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO audit_log (action_type, details)
       VALUES ('PURCHASE', 'Фільм: ' || COALESCE(v_movie_title, 'Невідомий ID:' || NEW.movie_id) || ', Місце ID: ' || NEW.seat_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_bookings AFTER INSERT OR UPDATE ON bookings FOR EACH ROW EXECUTE FUNCTION log_booking_func();


CREATE OR REPLACE FUNCTION log_movies_func() RETURNS TRIGGER AS $$
DECLARE
    change_details TEXT;
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO audit_log (action_type, details)
        VALUES ('MOVIE_ADD', 'Додано фільм: "' || NEW.title || '"');
    ELSIF (TG_OP = 'UPDATE') THEN
        change_details := 'Змінено фільм "' || OLD.title || '":';
        IF OLD.title <> NEW.title THEN
            change_details := change_details || ' [Назва: ' || OLD.title || ' -> ' || NEW.title || ']';
        END IF;
        IF OLD.price <> NEW.price THEN
            change_details := change_details || ' [Ціна: ' || OLD.price || ' -> ' || NEW.price || ']';
        END IF;
        IF OLD.poster_url <> NEW.poster_url THEN
            change_details := change_details || ' [Постер оновлено]';
        END IF;
        INSERT INTO audit_log (action_type, details)
        VALUES ('MOVIE_EDIT', change_details);
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO audit_log (action_type, details)
        VALUES ('MOVIE_DEL', 'Видалено фільм: "' || OLD.title || '" (ID: ' || OLD.id || ')');
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_audit_movies
AFTER INSERT OR UPDATE OR DELETE ON movies
FOR EACH ROW
EXECUTE FUNCTION log_movies_func();