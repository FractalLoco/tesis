-- Base de prueba para la aplicación y las pruebas de integración / E2E.
-- Mismo esquema sintético tipo TPC-H del notebook de ml/ (escala 1), con datos
-- sesgados: 60% de clientes y proveedores en 5 naciones. Además tiene claves
-- foráneas para que el diagrama muestre las relaciones.
--
-- Uso (como superusuario, sobre una base vacía):
--   createdb optimizacion
--   psql -d optimizacion -f sql/base_de_prueba.sql
-- Después crear el usuario de solo lectura con sql/usuario_solo_lectura.sql.

CREATE TABLE region  (r_regionkey int PRIMARY KEY, r_name text);
CREATE TABLE nation  (n_nationkey int PRIMARY KEY, n_name text, n_regionkey int REFERENCES region);
CREATE TABLE supplier(s_suppkey int PRIMARY KEY, s_name text, s_nationkey int REFERENCES nation);
CREATE TABLE customer(c_custkey int PRIMARY KEY, c_name text, c_nationkey int REFERENCES nation, c_acctbal numeric);
CREATE TABLE part    (p_partkey int PRIMARY KEY, p_name text, p_brand text, p_size int);
CREATE TABLE orders  (o_orderkey int PRIMARY KEY, o_custkey int REFERENCES customer, o_orderdate date, o_totalprice numeric);
CREATE TABLE lineitem(l_id int PRIMARY KEY, l_orderkey int REFERENCES orders, l_partkey int REFERENCES part,
                      l_suppkey int REFERENCES supplier, l_quantity int, l_extendedprice numeric);

INSERT INTO region
SELECT i, (ARRAY['AMERICA','EUROPE','ASIA','AFRICA','MIDDLE EAST'])[i + 1]
FROM generate_series(0, 4) i;

INSERT INTO nation
SELECT i, (ARRAY['CHILE','ARGENTINA','BRAZIL','PERU','USA','CANADA','GERMANY','FRANCE','SPAIN','ITALY',
                 'UK','CHINA','JAPAN','INDIA','KOREA','EGYPT','MOROCCO','KENYA','NIGERIA','SAUDI',
                 'IRAN','MEXICO','COLOMBIA','RUSSIA','TURKEY'])[i + 1], i % 5
FROM generate_series(0, 24) i;

-- Sesgo: con 60% de probabilidad la nación sale de las 5 "grandes" (0, 1, 4, 6, 11).
INSERT INTO supplier
SELECT i, 'Sup_' || i,
       CASE WHEN random() < 0.6 THEN (ARRAY[0, 1, 4, 6, 11])[1 + floor(random() * 5)::int]
            ELSE floor(random() * 25)::int END
FROM generate_series(0, 999) i;

INSERT INTO customer
SELECT i, 'Cli_' || i,
       CASE WHEN random() < 0.6 THEN (ARRAY[0, 1, 4, 6, 11])[1 + floor(random() * 5)::int]
            ELSE floor(random() * 25)::int END,
       round((random() * 10499 - 500)::numeric, 2)
FROM generate_series(0, 14999) i;

INSERT INTO part
SELECT i, 'Parte_' || i, 'Marca#' || lpad((1 + floor(random() * 25))::int::text, 2, '0'),
       1 + floor(random() * 50)::int
FROM generate_series(0, 9999) i;

INSERT INTO orders
SELECT i, floor(random() * 15000)::int, date '2022-01-01' + floor(random() * 1000)::int,
       round((10 + random() * 89990)::numeric, 2)
FROM generate_series(0, 59999) i;

-- Cada orden tiene de 1 a 4 líneas. El "+ o * 0" hace que la cantidad se sortee
-- de nuevo para cada orden (si no, PostgreSQL la calcula una sola vez).
INSERT INTO lineitem
SELECT row_number() OVER () - 1, o, floor(random() * 10000)::int, floor(random() * 1000)::int,
       1 + floor(random() * 50)::int, round((100 + random() * 79900)::numeric, 2)
FROM generate_series(0, 59999) o,
     LATERAL generate_series(1, 1 + floor(random() * 4)::int + o * 0) k;

CREATE INDEX ON orders(o_custkey);
CREATE INDEX ON orders(o_orderdate);
CREATE INDEX ON lineitem(l_orderkey);
CREATE INDEX ON lineitem(l_partkey);
CREATE INDEX ON lineitem(l_suppkey);
CREATE INDEX ON customer(c_nationkey);
CREATE INDEX ON supplier(s_nationkey);
CREATE INDEX ON part(p_brand);
CREATE INDEX ON nation(n_regionkey);

ANALYZE;
