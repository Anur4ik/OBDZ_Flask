INSERT INTO users (username, password, balance, is_admin) VALUES
 ('admin', 'admin', 99999.00, TRUE);
 CALL add_movie_proc(
    'Зоотрополіс 2',
    'https://multiplex.ua/images/65/f5/65f57bfb1f869d37bf5e384263baaa1b.jpeg',
    120.00,
    5, 8
);
CALL add_movie_proc(
    'Ілюзія обману 3',
    'https://multiplex.ua/images/38/65/386547296be4aa9bcc6b97c8a30e66e8.jpeg',
    200.00,
    8, 10
);

CALL add_movie_proc(
    'МАГІЧНА БИТВА',
    'https://multiplex.ua/images/11/87/118719db638eb075f9ed0a705ec4105e.jpeg',
    150.00,
    3, 5
);