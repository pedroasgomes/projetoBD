DROP DATABASE IF EXISTS postgres;

CREATE DATABASE postgres;

DROP TABLE IF EXISTS delivery;
DROP TABLE IF EXISTS supplier;
DROP TABLE IF EXISTS contains;
DROP TABLE IF EXISTS pay;
DROP TABLE IF EXISTS sale;
DROP TABLE IF EXISTS processes;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS works;
DROP TABLE IF EXISTS warehouse;
DROP TABLE IF EXISTS office;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS workplace;
DROP TABLE IF EXISTS department;
DROP TABLE IF EXISTS employee;
DROP TABLE IF EXISTS customer;


CREATE TABLE customer(
	cust_no NUMERIC(9) PRIMARY KEY,
	name VARCHAR(50),
	email VARCHAR(50) NOT NULL UNIQUE,
	phone NUMERIC(9),
	address VARCHAR(100)
);

CREATE TABLE employee(
	ssn NUMERIC(9) PRIMARY KEY,
	tin NUMERIC(9) NOT NULL UNIQUE,
	bdate DATE,
	name VARCHAR(50)
);

CREATE TABLE department(
	name VARCHAR(50) PRIMARY KEY
);

CREATE TABLE workplace(
	address VARCHAR(100) PRIMARY KEY,
	lat NUMERIC(11,6) NOT NULL,
	long NUMERIC(11,6) NOT NULL,
	UNIQUE (lat, long)
);

CREATE TABLE product(
	sku NUMERIC(9) PRIMARY KEY,
	name VARCHAR(50),
	description VARCHAR(100),
	price NUMERIC(5,2),
	ean NUMERIC(13)
);

CREATE TABLE office(
	address VARCHAR(100),
	PRIMARY KEY (address),
	FOREIGN KEY (address) REFERENCES workplace ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE warehouse(
	address VARCHAR(100),
	PRIMARY KEY (address),
	FOREIGN KEY (address) REFERENCES workplace ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE works(
	ssn NUMERIC(9),
	name VARCHAR(50),
	address VARCHAR(100),
	PRIMARY KEY (ssn,name,address),

	FOREIGN KEY (ssn) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (name) REFERENCES department ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (address) REFERENCES workplace ON DELETE CASCADE ON UPDATE CASCADE
); -- Cada employee tem pelo menos 1 entrada na tabela works

CREATE TABLE orders(
	order_no NUMERIC(9) PRIMARY KEY,
	date DATE,
	cust_no NUMERIC(9) NOT NULL,
	FOREIGN KEY (cust_no) REFERENCES customer ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE processes(
	ssn NUMERIC(9),
	order_no NUMERIC(9),
	PRIMARY KEY (ssn,order_no),
	FOREIGN KEY (ssn) REFERENCES employee ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (order_no) REFERENCES orders ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE sale(
	order_no NUMERIC(9),
	PRIMARY KEY (order_no),
	FOREIGN KEY (order_no) REFERENCES orders ON DELETE CASCADE ON UPDATE CASCADE);

CREATE TABLE pay(
	order_no NUMERIC(9),
	cust_no NUMERIC(9),
	PRIMARY KEY (order_no),
	FOREIGN KEY (order_no) REFERENCES orders ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (cust_no) REFERENCES customer ON DELETE CASCADE ON UPDATE CASCADE
);
-- o tuplo (order_no,cust_no) tem de estar presente tambem em orders


CREATE TABLE contains(
	order_no NUMERIC(9),
	sku NUMERIC(9),
	qty NUMERIC(3),
	PRIMARY KEY (order_no, sku),
	FOREIGN KEY (order_no) REFERENCES orders ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (sku) REFERENCES product ON DELETE CASCADE ON UPDATE CASCADE
); -- todos os order_no de orders tem pelo menos 1 entrada em contains

CREATE TABLE supplier(
	tin NUMERIC(9) PRIMARY KEY,
	name VARCHAR(50),
	address VARCHAR(100),
	sku NUMERIC(9) NOT NULL,
	date DATE,
	FOREIGN KEY (sku) REFERENCES product ON DELETE CASCADE ON UPDATE CASCADE
); -- cada sku em product tem pelo menos 1 entrada em supplier

CREATE TABLE delivery(
	tin NUMERIC(9),
	address VARCHAR(100),
	PRIMARY KEY (tin,address),
	FOREIGN KEY (tin) REFERENCES supplier ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (address) REFERENCES warehouse ON DELETE CASCADE ON UPDATE CASCADE
);