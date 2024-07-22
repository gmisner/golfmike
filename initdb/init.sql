CREATE USER airplane WITH SUPERUSER PASSWORD 'airplane';
CREATE USER postgres WITH SUPERUSER PASSWORD 'airplane';

CREATE DATABASE golfmike
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;