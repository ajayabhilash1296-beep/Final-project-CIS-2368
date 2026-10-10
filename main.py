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