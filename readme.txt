EQUIPMENT RENTAL MANAGEMENT SYSTEM - SPRINT 1

Flask REST API and MySQL database for an equipment rental business.

FILES
  setup.sql         Creates the tables and sample data
  main.py           The API
  requirements.txt  Packages to install

HOW TO RUN
  1. Run setup.sql in MySQL Workbench.
  2. Put your database login in Part 1 of main.py.
  3. pip install -r requirements.txt
  4. python main.py   (API runs at http://127.0.0.1:5000)

ENDPOINTS
  These support GET, POST, PUT and DELETE:
    /api/customer   /api/category   /api/equipment   /api/rental   /api/return

  GET with no id returns all rows. GET with ?id=1 returns one row.
  POST and PUT take a JSON body with the table's columns (PUT also needs "id").
  DELETE takes the id in the URL: ?id=1

  GET /api/customerrentals?customerid=1   A customer's rentals
  GET /api/inventory                      Current inventory

BUSINESS RULES
  - Equipment can't be rented if there isn't enough in stock.
  - A customer can't return more units than they currently have rented.