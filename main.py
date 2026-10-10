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