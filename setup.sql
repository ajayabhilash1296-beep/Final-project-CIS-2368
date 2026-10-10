-- setup.sql
-- Final Project, Sprint 1: Equipment Rental Management System
-- Tables:
--   customer           people who rent equipment
--   category           groups of equipment (Power Tools, Party & Events, ...)
--   equipment          each item; quantityavailable = units on the shelf right now
--   rentaltransaction  a customer renting units of a piece of equipment
--   returntransaction  a customer bringing units back

CREATE DATABASE IF NOT EXISTS equipmentrental;
USE equipmentrental;

-- Drop the tables that point to other tables first, so the foreign keys don't block it
DROP TABLE IF EXISTS returntransaction;
DROP TABLE IF EXISTS rentaltransaction;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS customer;


-- ========== CUSTOMER ==========
CREATE TABLE customer (
    id        INT          NOT NULL AUTO_INCREMENT,
    firstname VARCHAR(50)  NOT NULL,
    lastname  VARCHAR(50)  NOT NULL,
    email     VARCHAR(100) NOT NULL UNIQUE,
    PRIMARY KEY (id)
);


-- ========== CATEGORY ==========
CREATE TABLE category (
    id           INT          NOT NULL AUTO_INCREMENT,
    categoryname VARCHAR(50)  NOT NULL UNIQUE,
    description  VARCHAR(255),
    PRIMARY KEY (id)
);


-- ========== EQUIPMENT ==========
CREATE TABLE equipment (
    id                INT           NOT NULL AUTO_INCREMENT,
    equipmentname     VARCHAR(100)  NOT NULL,
    categoryid        INT           NOT NULL,
    dailyrate         DECIMAL(10,2) NOT NULL,
    quantityavailable INT           NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    FOREIGN KEY (categoryid) REFERENCES category(id),
    CHECK (dailyrate >= 0),
    CHECK (quantityavailable >= 0)
);


-- ========== RENTAL TRANSACTION ==========
CREATE TABLE rentaltransaction (
    id          INT      NOT NULL AUTO_INCREMENT,
    `date`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    customerid  INT      NOT NULL,
    equipmentid INT      NOT NULL,
    quantity    INT      NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (customerid)  REFERENCES customer(id),
    FOREIGN KEY (equipmentid) REFERENCES equipment(id),
    CHECK (quantity > 0)
);


-- ========== RETURN TRANSACTION ==========
CREATE TABLE returntransaction (
    id          INT      NOT NULL AUTO_INCREMENT,
    `date`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    customerid  INT      NOT NULL,
    equipmentid INT      NOT NULL,
    quantity    INT      NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (customerid)  REFERENCES customer(id),
    FOREIGN KEY (equipmentid) REFERENCES equipment(id),
    CHECK (quantity > 0)
);


-- ========== SAMPLE DATA ==========

INSERT INTO category (categoryname, description) VALUES
    ('Power Tools',      'Drills, saws and other powered hand tools'),
    ('Ladders & Access', 'Ladders, scaffolding and work platforms'),
    ('Lawn & Garden',    'Mowers, tillers and yard equipment'),
    ('Party & Events',   'Tables, chairs and tents for events');

INSERT INTO equipment (equipmentname, categoryid, dailyrate, quantityavailable) VALUES
    ('Cordless Drill',          1,  15.00,  8),
    ('Circular Saw',            1,  22.50,  6),
    ('24 ft Extension Ladder',  2,  18.00,  5),
    ('Scaffold Set',            2,  45.00,  3),
    ('Lawn Mower',              3,  35.00,  3),
    ('Garden Tiller',           3,  55.00,  2),
    ('Folding Table',           4,   8.00, 24),
    ('20x20 Party Tent',        4, 120.00,  1);

INSERT INTO customer (firstname, lastname, email) VALUES
    ('Maria', 'Garcia', 'maria.garcia@example.com'),
    ('James', 'Nguyen', 'james.nguyen@example.com'),
    ('Aisha', 'Patel',  'aisha.patel@example.com'),
    ('David', 'Kim',    'david.kim@example.com'),
    ('Sofia', 'Lopez',  'sofia.lopez@example.com');

INSERT INTO rentaltransaction (`date`, customerid, equipmentid, quantity) VALUES
    ('2026-10-01 09:15:00', 1, 1,  2), 
    ('2026-10-02 10:30:00', 1, 7, 10),
    ('2026-10-03 14:00:00', 2, 5,  1), 
    ('2026-10-05 11:45:00', 3, 8,  1);

INSERT INTO returntransaction (`date`, customerid, equipmentid, quantity) VALUES
    ('2026-10-04 16:20:00', 1, 7,  4);