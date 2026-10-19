-- Esquema de la base de datos PostgreSQL de Groove Records
-- Uso:  psql -U tienda_user -d tienda -f schema.sql

DROP TABLE IF EXISTS compras;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS mensajes;
DROP TABLE IF EXISTS discos;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(50)  NOT NULL,
    email     VARCHAR(100) NOT NULL UNIQUE,
    password  VARCHAR(255) NOT NULL,
    creado    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE discos (
    id           SERIAL PRIMARY KEY,
    artista      VARCHAR(100)  NOT NULL,
    titulo       VARCHAR(150)  NOT NULL,
    genero       VARCHAR(50)   NOT NULL,
    anio         INTEGER       NOT NULL,
    formato      VARCHAR(10)   NOT NULL CHECK (formato IN ('Vinilo', 'CD')),
    descripcion  TEXT,
    precio       NUMERIC(8, 2) NOT NULL CHECK (precio >= 0),
    stock        INTEGER       NOT NULL DEFAULT 0 CHECK (stock >= 0),
    -- NULL = portada sin buscar, '' = no encontrada, otro valor = URL de la imagen
    portada_url  TEXT
);

-- Un pedido agrupa todos los discos que el usuario compra a la vez (carrito)
CREATE TABLE pedidos (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER        NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    total       NUMERIC(10, 2) NOT NULL,
    fecha       TIMESTAMP      NOT NULL DEFAULT NOW()
);

-- Cada fila de "compras" es una línea del pedido (un disco y su cantidad)
CREATE TABLE compras (
    id               SERIAL PRIMARY KEY,
    pedido_id        INTEGER        NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    disco_id         INTEGER        NOT NULL REFERENCES discos(id),
    cantidad         INTEGER        NOT NULL CHECK (cantidad > 0),
    precio_unitario  NUMERIC(8, 2)  NOT NULL,
    total            NUMERIC(10, 2) NOT NULL
);

CREATE TABLE mensajes (
    id       SERIAL PRIMARY KEY,
    nombre   VARCHAR(50)  NOT NULL,
    email    VARCHAR(100) NOT NULL,
    mensaje  TEXT         NOT NULL,
    fecha    TIMESTAMP    NOT NULL DEFAULT NOW()
);

INSERT INTO discos (artista, titulo, genero, anio, formato, descripcion, precio, stock) VALUES
    ('Pink Floyd', 'The Dark Side of the Moon', 'Rock', 1973, 'Vinilo',
     'Álbum conceptual de rock progresivo. Prensado en vinilo de 180 g.', 28.90, 10),
    ('Miles Davis', 'Kind of Blue', 'Jazz', 1959, 'Vinilo',
     'Referencia absoluta del jazz modal. Edición en vinilo de 180 g.', 24.50, 8),
    ('Daft Punk', 'Random Access Memories', 'Electrónica', 2013, 'Vinilo',
     'Doble vinilo con funk, disco y electrónica de estudio.', 32.00, 6),
    ('Nirvana', 'Nevermind', 'Rock', 1991, 'CD',
     'El disco que popularizó el grunge, en edición CD remasterizada.', 11.90, 20),
    ('Rosalía', 'El mal querer', 'Pop', 2018, 'Vinilo',
     'Fusión de flamenco y pop contemporáneo en formato vinilo.', 27.00, 9),
    ('Radiohead', 'OK Computer', 'Rock', 1997, 'CD',
     'Clásico del rock alternativo, edición CD con libreto.', 12.50, 14),
    ('Michael Jackson', 'Thriller', 'Pop', 1982, 'CD',
     'Uno de los discos más vendidos de la historia, en CD.', 9.95, 25),
    ('Bob Marley & The Wailers', 'Legend', 'Reggae', 1984, 'Vinilo',
     'Recopilatorio con los grandes éxitos de Bob Marley.', 26.90, 7),
    ('Amy Winehouse', 'Back to Black', 'Soul', 2006, 'Vinilo',
     'Soul y R&B con aire retro. Edición en vinilo.', 25.90, 12),
    ('Kendrick Lamar', 'To Pimp a Butterfly', 'Hip hop', 2015, 'CD',
     'Hip hop con jazz y funk. Edición CD.', 13.90, 10),
    ('Camarón de la Isla', 'La leyenda del tiempo', 'Flamenco', 1979, 'Vinilo',
     'Álbum que renovó el flamenco. Reedición en vinilo.', 23.90, 5),
    ('The Strokes', 'Is This It', 'Indie', 2001, 'CD',
     'Debut del garage rock revival, edición CD.', 10.90, 15);
