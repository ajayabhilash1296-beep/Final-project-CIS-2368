# main.py
# Final Project, Sprint 1: Equipment Rental Management System (backend)
#
# Business rules (Part 3, marked "RULE"):
#   - Equipment can't be rented if there isn't enough in stock.
#   - A customer can never return more units than they currently have rented.
 
import math
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
 
import mysql.connector
import flask
from flask import jsonify, request
 
 
# ==============================================================
# PART 1: DATABASE LOGIN
# ==============================================================
DB_HOST = 'cis2368.cl6aeo2gck7p.us-east-1.rds.amazonaws.com'
DB_USER = 'admin'
DB_PASSWORD = 'your_password'
DB_NAME = 'equipmentrental'

# ==============================================================
# PART 2: HELPER FUNCTIONS
#   run_query()   -> for INSERT, UPDATE, DELETE (changes data)
#   read_query()  -> for SELECT (reads data)
#   transaction() -> for changes that need several SQL statements
#                    to all succeed or all fail together
# A %s inside a query is a placeholder.
# ==============================================================
 
def connect():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
 
 
def run_query(sql, values=()):
    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, values)
        connection.commit()
        return cursor.lastrowid 
    finally:
        connection.close()
 
 
def read_query(sql, values=()):
    # Each row is a dictionary, like {'id': 1, 'firstname': 'Maria', ...}
    connection = connect()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, values)
        return clean_rows(cursor.fetchall())
    finally:
        connection.close()
 
 
def clean_rows(rows):
    for row in rows:
        for key, value in row.items():
            if isinstance(value, Decimal):
                row[key] = float(value)
            elif isinstance(value, datetime):
                row[key] = value.strftime('%Y-%m-%d %H:%M:%S')
    return rows
 
 
@contextmanager
def transaction():
    # Renting and returning change TWO tables (equipment stock + a transaction row).
    # Everything inside "with transaction() as cursor:" is saved together at the end,
    # or, if anything goes wrong (like a broken rule), NOTHING is saved (rollback).
    # READ COMMITTED means each query sees the newest saved data.
    connection = connect()
    connection.start_transaction(isolation_level='READ COMMITTED')
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
 
 
class RuleError(Exception):
    # Raised when the input is invalid or a business rule is broken.
    pass
 
 
# ---------- input checks (validation) ----------
 
def check_text(value, field, max_length, required=True):
    # Must be non-empty text, no longer than the database column allows
    if value is None or (isinstance(value, str) and value.strip() == ''):
        if required:
            raise RuleError(f'{field} is required')
        return None
    if not isinstance(value, str):
        raise RuleError(f'{field} must be text')
    if len(value.strip()) > max_length:
        raise RuleError(f'{field} can be at most {max_length} characters')
    return value.strip()
 
 
def check_email(value):
    email = check_text(value, 'email', 100)
    name, at, domain = email.partition('@')
    if not name or not at or '.' not in domain or ' ' in email:
        raise RuleError('email must be a valid email address, like name@example.com')
    return email.lower()
 
 
def check_whole_number(value, field, minimum=0):
    # Accepts 3 or "3". Rejects 2.5, "abc", true, and anything below the minimum.
    if value is None or value == '':
        raise RuleError(f'{field} is required')
    if isinstance(value, bool) or not str(value).strip().isdecimal():
        raise RuleError(f'{field} must be a whole number (at least {minimum})')
    number = int(str(value).strip())
    if number < minimum:
        raise RuleError(f'{field} must be at least {minimum}')
    if number > 2147483647: 
        raise RuleError(f'{field} is too large')
    return number
 
 
def check_id(value, field='id'):
    # Ids start at 1
    return check_whole_number(value, field, minimum=1)
 
 
def check_money(value, field):
    if value is None or value == '':
        raise RuleError(f'{field} is required')
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise RuleError(f'{field} must be a number') from None
    if isinstance(value, bool) or not math.isfinite(number) or number < 0 or number >= 100000000:
        raise RuleError(f'{field} must be a number from 0 to 99999999.99')
    return round(number, 2)
 
 
def count(sql, values):
    # Runs a "SELECT COUNT(*) AS total ..." query and returns the number
    return read_query(sql, values)[0]['total']

# ==============================================================
# PART 3: THE FEATURES AS NORMAL PYTHON FUNCTIONS
# get_... functions return None when the id doesn't exist (Part 4 sends a 404).
# ==============================================================
 
# ---------- CUSTOMERS ----------
 
def get_customers():
    return read_query("SELECT * FROM customer ORDER BY id")
 
 
def get_customer(customerid):
    customerid = check_id(customerid)
    rows = read_query("SELECT * FROM customer WHERE id = %s", [customerid])
    if len(rows) == 0:
        return None 
    return rows[0]
 
 
def check_email_is_free(email, customerid=0):
    # Two customers can't share an email (customerid = the customer being updated, if any)
    if count("SELECT COUNT(*) AS total FROM customer WHERE email = %s AND id <> %s", [email, customerid]) > 0:
        raise RuleError(f'Another customer already uses the email {email}')
 
 
def add_customer(firstname, lastname, email):
    firstname = check_text(firstname, 'firstname', 50)
    lastname = check_text(lastname, 'lastname', 50)
    email = check_email(email)
    check_email_is_free(email)
    sql = "INSERT INTO customer (firstname, lastname, email) VALUES (%s, %s, %s)"
    return run_query(sql, [firstname, lastname, email])
 
 
def update_customer(customerid, firstname, lastname, email):
    customerid = check_id(customerid)
    if get_customer(customerid) is None:
        return None
    firstname = check_text(firstname, 'firstname', 50)
    lastname = check_text(lastname, 'lastname', 50)
    email = check_email(email)
    check_email_is_free(email, customerid)
    sql = "UPDATE customer SET firstname = %s, lastname = %s, email = %s WHERE id = %s"
    run_query(sql, [firstname, lastname, email, customerid])
    return get_customer(customerid)
 
 
def delete_customer(customerid):
    customerid = check_id(customerid)
    if get_customer(customerid) is None:
        return False
    # A customer with rental history can't be deleted (the transactions point to them)
    used = count("""SELECT (SELECT COUNT(*) FROM rentaltransaction WHERE customerid = %s)
                         + (SELECT COUNT(*) FROM returntransaction WHERE customerid = %s) AS total""",
                 [customerid, customerid])
    if used > 0:
        raise RuleError(f'Customer {customerid} has {used} rental/return transaction(s). '
                        'Delete those transactions first.')
    run_query("DELETE FROM customer WHERE id = %s", [customerid])
    return True
 
 
# ---------- CATEGORIES ----------
 
def get_categories():
    return read_query("SELECT * FROM category ORDER BY id")
 
 
def get_category(categoryid):
    categoryid = check_id(categoryid)
    rows = read_query("SELECT * FROM category WHERE id = %s", [categoryid])
    if len(rows) == 0:
        return None
    return rows[0]
 
 
def check_categoryname_is_free(categoryname, categoryid=0):
    if count("SELECT COUNT(*) AS total FROM category WHERE categoryname = %s AND id <> %s",
             [categoryname, categoryid]) > 0:
        raise RuleError(f'A category named {categoryname} already exists')
 
 
def add_category(categoryname, description):
    categoryname = check_text(categoryname, 'categoryname', 50)
    description = check_text(description, 'description', 255, required=False)
    check_categoryname_is_free(categoryname)
    sql = "INSERT INTO category (categoryname, description) VALUES (%s, %s)"
    return run_query(sql, [categoryname, description])
 
 
def update_category(categoryid, categoryname, description):
    categoryid = check_id(categoryid)
    if get_category(categoryid) is None:
        return None
    categoryname = check_text(categoryname, 'categoryname', 50)
    description = check_text(description, 'description', 255, required=False)
    check_categoryname_is_free(categoryname, categoryid)
    sql = "UPDATE category SET categoryname = %s, description = %s WHERE id = %s"
    run_query(sql, [categoryname, description, categoryid])
    return get_category(categoryid)
 
 
def delete_category(categoryid):
    categoryid = check_id(categoryid)
    if get_category(categoryid) is None:
        return False
    used = count("SELECT COUNT(*) AS total FROM equipment WHERE categoryid = %s", [categoryid])
    if used > 0:
        raise RuleError(f'Category {categoryid} still has {used} piece(s) of equipment. '
                        'Move or delete that equipment first.')
    run_query("DELETE FROM category WHERE id = %s", [categoryid])
    return True
 
 
# ---------- EQUIPMENT ----------
 
# Equipment rows also show the category name (JOIN), which is handy for the frontend
EQUIPMENT_SQL = """SELECT equipment.*, category.categoryname
                   FROM equipment JOIN category ON category.id = equipment.categoryid"""
 
 
def get_all_equipment():
    return read_query(EQUIPMENT_SQL + " ORDER BY equipment.id")
 
 
def get_equipment(equipmentid):
    equipmentid = check_id(equipmentid)
    rows = read_query(EQUIPMENT_SQL + " WHERE equipment.id = %s", [equipmentid])
    if len(rows) == 0:
        return None
    return rows[0]
 
 
def check_equipment_input(equipmentname, categoryid, dailyrate, quantityavailable):
    # Checks all equipment fields and returns the cleaned-up values
    equipmentname = check_text(equipmentname, 'equipmentname', 100)
    categoryid = check_id(categoryid, 'categoryid')
    if get_category(categoryid) is None:
        raise RuleError(f'categoryid {categoryid} does not exist')
    dailyrate = check_money(dailyrate, 'dailyrate')
    quantityavailable = check_whole_number(quantityavailable, 'quantityavailable', minimum=0)
    return equipmentname, categoryid, dailyrate, quantityavailable
 
 
def add_equipment(equipmentname, categoryid, dailyrate, quantityavailable):
    values = check_equipment_input(equipmentname, categoryid, dailyrate, quantityavailable)
    sql = """INSERT INTO equipment (equipmentname, categoryid, dailyrate, quantityavailable)
             VALUES (%s, %s, %s, %s)"""
    return run_query(sql, list(values))
 
 
def update_equipment(equipmentid, equipmentname, categoryid, dailyrate, quantityavailable):
    equipmentid = check_id(equipmentid)
    if get_equipment(equipmentid) is None:
        return None
    values = check_equipment_input(equipmentname, categoryid, dailyrate, quantityavailable)
    sql = """UPDATE equipment SET equipmentname = %s, categoryid = %s, dailyrate = %s, quantityavailable = %s
             WHERE id = %s"""
    run_query(sql, list(values) + [equipmentid])
    return get_equipment(equipmentid)
 
 
def delete_equipment(equipmentid):
    equipmentid = check_id(equipmentid)
    if get_equipment(equipmentid) is None:
        return False
    used = count("""SELECT (SELECT COUNT(*) FROM rentaltransaction WHERE equipmentid = %s)
                         + (SELECT COUNT(*) FROM returntransaction WHERE equipmentid = %s) AS total""",
                 [equipmentid, equipmentid])
    if used > 0:
        raise RuleError(f'Equipment {equipmentid} has {used} rental/return transaction(s). '
                        'Delete those transactions first.')
    run_query("DELETE FROM equipment WHERE id = %s", [equipmentid])
    return True
 
 
# ---------- helpers for rentals and returns ----------
 
def lock_equipment(cursor, equipmentid):
    # FOR UPDATE locks this equipment row until we commit, so two requests
    # can't rent the last unit at the same moment.
    cursor.execute("SELECT * FROM equipment WHERE id = %s FOR UPDATE", [equipmentid])
    equipment = cursor.fetchone()
    if equipment is None:
        raise RuleError(f'equipmentid {equipmentid} does not exist')
    return equipment
 
 
def check_customer_exists(cursor, customerid):
    cursor.execute("SELECT id FROM customer WHERE id = %s", [customerid])
    if cursor.fetchone() is None:
        raise RuleError(f'customerid {customerid} does not exist')
 
 
def units_rented_now(cursor, customerid, equipmentid):
    # How many units of this equipment the customer has right now:
    # everything they rented minus everything they returned
    cursor.execute("""SELECT
        (SELECT COALESCE(SUM(quantity), 0) FROM rentaltransaction WHERE customerid = %s AND equipmentid = %s)
      - (SELECT COALESCE(SUM(quantity), 0) FROM returntransaction WHERE customerid = %s AND equipmentid = %s)
        AS units""", [customerid, equipmentid, customerid, equipmentid])
    return int(cursor.fetchone()['units'])
 
 
def change_stock(cursor, equipmentid, amount):
    # amount > 0 puts units back on the shelf, amount < 0 takes them off
    cursor.execute("UPDATE equipment SET quantityavailable = quantityavailable + %s WHERE id = %s",
                   [amount, equipmentid])
 
 
def lock_transaction_row(cursor, table, transactionid):
    # table is always 'rentaltransaction' or 'returntransaction' (never user input)
    cursor.execute(f"SELECT * FROM {table} WHERE id = %s FOR UPDATE", [transactionid])
    return cursor.fetchone()
 
 
def transaction_sql(table):
    # Transaction rows also show the customer's name and the equipment name
    return f"""SELECT t.id, t.`date`, t.customerid,
                      CONCAT(customer.firstname, ' ', customer.lastname) AS customername,
                      t.equipmentid, equipment.equipmentname, t.quantity
               FROM {table} t
               JOIN customer ON customer.id = t.customerid
               JOIN equipment ON equipment.id = t.equipmentid"""
 
 
# ---------- RENTALS (rentaltransaction table) ----------
 
def get_rentals():
    return read_query(transaction_sql('rentaltransaction') + " ORDER BY t.`date` DESC, t.id DESC")
 
 
def get_rental(rentalid):
    rentalid = check_id(rentalid)
    rows = read_query(transaction_sql('rentaltransaction') + " WHERE t.id = %s", [rentalid])
    if len(rows) == 0:
        return None
    return rows[0]
 
 
def create_rental(customerid, equipmentid, quantity):
    customerid = check_id(customerid, 'customerid')
    equipmentid = check_id(equipmentid, 'equipmentid')
    quantity = check_whole_number(quantity, 'quantity', minimum=1)
    with transaction() as cursor:
        equipment = lock_equipment(cursor, equipmentid)
        check_customer_exists(cursor, customerid)
        # RULE: equipment can't be rented if there isn't enough in stock
        if quantity > equipment['quantityavailable']:
            raise RuleError(f"Not enough {equipment['equipmentname']} in stock: "
                            f"{equipment['quantityavailable']} available, {quantity} requested")
        change_stock(cursor, equipmentid, -quantity) 
        cursor.execute("INSERT INTO rentaltransaction (customerid, equipmentid, quantity) VALUES (%s, %s, %s)",
                       [customerid, equipmentid, quantity])
        return cursor.lastrowid
 
 
def update_rental(rentalid, customerid, equipmentid, quantity):
    rentalid = check_id(rentalid)
    customerid = check_id(customerid, 'customerid')
    equipmentid = check_id(equipmentid, 'equipmentid')
    quantity = check_whole_number(quantity, 'quantity', minimum=1)
    with transaction() as cursor:
        old = lock_transaction_row(cursor, 'rentaltransaction', rentalid)
        if old is None:
            return None
        # Lock both pieces of equipment (lowest id first, so two requests never wait on each other)
        names = {}
        for eid in sorted({old['equipmentid'], equipmentid}):
            names[eid] = lock_equipment(cursor, eid)['equipmentname']
        check_customer_exists(cursor, customerid)
 
        # Undo the old rental: its units go back on the shelf
        change_stock(cursor, old['equipmentid'], old['quantity'])
        # RULE: there must be enough in stock for the new amount
        equipment = lock_equipment(cursor, equipmentid)
        if quantity > equipment['quantityavailable']:
            raise RuleError(f"Not enough {equipment['equipmentname']} in stock: "
                            f"{equipment['quantityavailable']} available, {quantity} requested")
        change_stock(cursor, equipmentid, -quantity)
        cursor.execute("UPDATE rentaltransaction SET customerid = %s, equipmentid = %s, quantity = %s WHERE id = %s",
                       [customerid, equipmentid, quantity, rentalid])
 
        # RULE: the change can't leave the old customer having returned more than they rented
        left = units_rented_now(cursor, old['customerid'], old['equipmentid'])
        if left < 0:
            raise RuleError(f"Can't make this change: customer {old['customerid']} would have returned more "
                            f"{names[old['equipmentid']]} than they rented. Delete or change the return first.")
        return True
 
 
def delete_rental(rentalid):
    rentalid = check_id(rentalid)
    with transaction() as cursor:
        rental = lock_transaction_row(cursor, 'rentaltransaction', rentalid)
        if rental is None:
            return False
        equipment = lock_equipment(cursor, rental['equipmentid'])
        # RULE: deleting a rental can't leave the customer with more returns than rentals
        rented_now = units_rented_now(cursor, rental['customerid'], rental['equipmentid'])
        if rental['quantity'] > rented_now:
            raise RuleError(f"Can't delete this rental: customer {rental['customerid']} has already returned "
                            f"some of these units (only {rented_now} {equipment['equipmentname']} still rented). "
                            "Delete the return first.")
        change_stock(cursor, rental['equipmentid'], rental['quantity']) 
        cursor.execute("DELETE FROM rentaltransaction WHERE id = %s", [rentalid])
        return True
 
 
# ---------- RETURNS (returntransaction table) ----------
 
def get_returns():
    return read_query(transaction_sql('returntransaction') + " ORDER BY t.`date` DESC, t.id DESC")
 
 
def get_return(returnid):
    returnid = check_id(returnid)
    rows = read_query(transaction_sql('returntransaction') + " WHERE t.id = %s", [returnid])
    if len(rows) == 0:
        return None
    return rows[0]
 
 
def create_return(customerid, equipmentid, quantity):
    customerid = check_id(customerid, 'customerid')
    equipmentid = check_id(equipmentid, 'equipmentid')
    quantity = check_whole_number(quantity, 'quantity', minimum=1)
    with transaction() as cursor:
        equipment = lock_equipment(cursor, equipmentid)
        check_customer_exists(cursor, customerid)
        # RULE: a customer can't return more units than they currently have rented
        rented_now = units_rented_now(cursor, customerid, equipmentid)
        if quantity > rented_now:
            raise RuleError(f"Customer {customerid} currently has {rented_now} {equipment['equipmentname']} "
                            f"rented, so they can't return {quantity}")
        change_stock(cursor, equipmentid, quantity) 
        cursor.execute("INSERT INTO returntransaction (customerid, equipmentid, quantity) VALUES (%s, %s, %s)",
                       [customerid, equipmentid, quantity])
        return cursor.lastrowid
 
 
def update_return(returnid, customerid, equipmentid, quantity):
    returnid = check_id(returnid)
    customerid = check_id(customerid, 'customerid')
    equipmentid = check_id(equipmentid, 'equipmentid')
    quantity = check_whole_number(quantity, 'quantity', minimum=1)
    with transaction() as cursor:
        old = lock_transaction_row(cursor, 'returntransaction', returnid)
        if old is None:
            return None
        names = {}
        for eid in sorted({old['equipmentid'], equipmentid}):
            names[eid] = lock_equipment(cursor, eid)['equipmentname']
        check_customer_exists(cursor, customerid)
 
        # The new return puts its units on the shelf...
        change_stock(cursor, equipmentid, quantity)
        equipment = lock_equipment(cursor, old['equipmentid'])
        if old['quantity'] > equipment['quantityavailable']:
            raise RuleError(f"Can't change this return: only {equipment['quantityavailable']} "
                            f"{equipment['equipmentname']} in stock because the returned units were rented out again")
        change_stock(cursor, old['equipmentid'], -old['quantity'])
        cursor.execute("UPDATE returntransaction SET customerid = %s, equipmentid = %s, quantity = %s WHERE id = %s",
                       [customerid, equipmentid, quantity, returnid])
 
        # RULE: a customer can't return more units than they currently have rented
        left = units_rented_now(cursor, customerid, equipmentid)
        if left < 0:
            raise RuleError(f"Customer {customerid} only has {left + quantity} {names[equipmentid]} rented, "
                            f"so the return can't be {quantity}")
        return True
 
 
def delete_return(returnid):
    returnid = check_id(returnid)
    with transaction() as cursor:
        ret = lock_transaction_row(cursor, 'returntransaction', returnid)
        if ret is None:
            return False
        equipment = lock_equipment(cursor, ret['equipmentid'])
        # Deleting a return means the customer has those units again, so they leave the shelf
        if ret['quantity'] > equipment['quantityavailable']:
            raise RuleError(f"Can't delete this return: only {equipment['quantityavailable']} "
                            f"{equipment['equipmentname']} in stock because the returned units were rented out again")
        change_stock(cursor, ret['equipmentid'], -ret['quantity'])
        cursor.execute("DELETE FROM returntransaction WHERE id = %s", [returnid])
        return True
 
 
# ---------- REPORTS ----------
 
def get_customer_rentals(customerid):
    # What one customer has out right now, plus their full rental and return history
    customer = get_customer(customerid)
    if customer is None:
        return None
    currently_rented = read_query("""
        SELECT equipment.id AS equipmentid, equipment.equipmentname, equipment.dailyrate,
               CAST(r.rented - COALESCE(t.returned, 0) AS SIGNED) AS quantityrented
        FROM (SELECT equipmentid, SUM(quantity) AS rented FROM rentaltransaction
              WHERE customerid = %s GROUP BY equipmentid) r
        JOIN equipment ON equipment.id = r.equipmentid
        LEFT JOIN (SELECT equipmentid, SUM(quantity) AS returned FROM returntransaction
                   WHERE customerid = %s GROUP BY equipmentid) t ON t.equipmentid = r.equipmentid
        WHERE r.rented - COALESCE(t.returned, 0) > 0
        ORDER BY equipment.equipmentname""", [customer['id'], customer['id']])
    order = " WHERE t.customerid = %s ORDER BY t.`date` DESC, t.id DESC"
    return {
        'customer': customer,
        'currentlyrented': currently_rented,
        'rentals': read_query(transaction_sql('rentaltransaction') + order, [customer['id']]),
        'returns': read_query(transaction_sql('returntransaction') + order, [customer['id']])
    }
 
 
def get_inventory():
    # Every piece of equipment: how many are on the shelf, how many are rented out, and the total
    return read_query("""
        SELECT equipment.id AS equipmentid, equipment.equipmentname, category.categoryname,
               equipment.dailyrate, equipment.quantityavailable,
               CAST(COALESCE(r.rented, 0) - COALESCE(t.returned, 0) AS SIGNED) AS quantityrentedout,
               CAST(equipment.quantityavailable + COALESCE(r.rented, 0) - COALESCE(t.returned, 0) AS SIGNED)
                   AS totalunits
        FROM equipment
        JOIN category ON category.id = equipment.categoryid
        LEFT JOIN (SELECT equipmentid, SUM(quantity) AS rented FROM rentaltransaction
                   GROUP BY equipmentid) r ON r.equipmentid = equipment.id
        LEFT JOIN (SELECT equipmentid, SUM(quantity) AS returned FROM returntransaction
                   GROUP BY equipmentid) t ON t.equipmentid = equipment.id
        ORDER BY category.categoryname, equipment.equipmentname""")