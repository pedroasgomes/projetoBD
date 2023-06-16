#!/usr/bin/python3
import os
from logging.config import dictConfig

import psycopg
from flask import flash
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool
from collections import namedtuple


# postgres://{user}:{password}@{hostname}:{port}/{database-name}
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://projeto:projeto@postgres/projeto")

pool = ConnectionPool(conninfo=DATABASE_URL)
# the pool starts connecting immediately.

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)
app.secret_key = 'a722153ee1a56e595d8b86e5b15e8c8f'
log = app.logger



@app.route("/", methods=("GET",))
@app.route("/menu", methods=("GET",))
def menu():
    """Show the menu page, used to group actions based on user type"""
    return render_template("menu/menu.html")

@app.route("/manager", methods=("GET",))
def manager_menu():
    """Show the menu for managers page, used to group actions based on type"""
    return render_template("menu/manager_menu.html")

@app.route("/client", methods=("GET",))
def client_list():
    page_size = 5
    page = request.args.get('page', 1, type=int)

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            clients = cur.execute(
                """
                SELECT * FROM customer
                WHERE name != 'N/A'
                ORDER BY cust_no
                """
            )

            # Only skip products if we are not on the first page
            if page > 1:
                cur.fetchmany((page-1) * page_size)  # Skip the products from previous pages
            
            clients = cur.fetchmany(page_size + 1)  # Fetch one additional product

    # If we got page_size + 1 products, then there is a next page
    has_next_page = len(clients) > page_size

    # Drop the extra product, if it exists
    clients = clients[:page_size]
    
    return render_template('client/client_select.html', clients=clients, page=page, page_size=page_size, has_next_page=has_next_page)

@app.route("/client/<int:cust_no>/menu", methods=("GET",))
def client_menu(cust_no):
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            client = cur.execute(
                """
                SELECT * FROM customer
                WHERE cust_no = %s
                """, (cust_no,)
            ).fetchone()
    
    return render_template('client/client_menu.html', client = client, cust_no = cust_no)


@app.route("/client/<int:cust_no>/orders", methods=("GET",))
def my_orders(cust_no):
    page_size = 5
    page = request.args.get('page', 1, type=int)
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:

            cur.execute(
                """SELECT order_no FROM pay WHERE cust_no=%s ;""", (cust_no,)
            )
            pago = cur.fetchall()
    itens_pagos = []
    for pay in pago:
        itens_pagos.append(pay.order_no)
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:

            cur.execute(
                """SELECT o.order_no AS order_no, p.name AS name, p.price AS price, price*qty AS total_price, c.qty AS qty
                FROM product p
                JOIN contains c USING (sku)
                JOIN orders o USING (order_no)
                JOIN customer USING (cust_no)
                WHERE cust_no = %s
                ORDER BY o.order_no
                ;""", (cust_no,)
            )

            # Only skip products if we are not on the first page
            if page > 1:
                cur.fetchmany((page-1) * page_size)  # Skip the products from previous pages
            
            products = cur.fetchmany(page_size + 1)  # Fetch one additional product

    # If we got page_size + 1 products, then there is a next page
    has_next_page = len(products) > page_size

    # Drop the extra product, if it exists
    products = products[:page_size]
    orders = {}
    for product in products:
        if product.order_no in orders.keys():
            orders[product.order_no][0].append((product.name, product.price, product.total_price, product.qty))
            orders[product.order_no][2]+=int(product.total_price)
        else:
            if product.order_no in itens_pagos:
                status = "Paid"
            else:
                status = "Not Paid"
            orders[product.order_no] = [[[product.name, product.price, product.total_price, product.qty]], status, int(product.total_price)]
            

    return render_template('client/my_orders.html', orders=orders, page=page, page_size=page_size, has_next_page=has_next_page, cust_no=cust_no)


@app.route("/client/<int:cust_no>/market", methods=("GET","POST"))
def market(cust_no):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """SELECT *
                FROM product ORDER BY sku;
                """
            )
            products = cur.fetchall()  # Fetch one additional product
            
    if request.method == "POST":
        pedido = []
        for produto in products:
            quantidade = int(request.form["quantity-"+produto.sku])
            if quantidade > 0:
                pedido.append((produto.sku, quantidade))
        if len(pedido)>0:
            order_no = get_order_no()
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute("START TRANSACTION;")
                    cur.execute( "INSERT INTO orders VALUES (%s, %s, CURRENT_DATE);", (order_no, cust_no,))
                    for ped in pedido:
                        cur.execute( "INSERT INTO contains VALUES (%s, %s, %s);", (order_no, ped[0], ped[1],))
                    cur.execute("COMMIT;")
            flash('Order submited!')
            return render_template('client/market.html', products=products,cust_no=cust_no)



    return render_template('client/market.html', products=products,cust_no=cust_no)




@app.route("/clients/<int:cust_no>/<int:order_no>/pay", methods=("GET", "POST"))
def confirm_payment(cust_no, order_no):
    if request.method == "POST":
        if "confirm" in request.form:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        INSERT INTO pay VALUES (%s, %s)
                        """,
                        (order_no, cust_no,)
                    )

        return redirect(url_for("client_menu", cust_no=cust_no))


    return render_template("client/pay_confirm.html", cust_no=cust_no, order_no=order_no)




@app.route("/products", methods=("GET",))
def products_index():
    page_size = 5
    page = request.args.get('page', 1, type=int)

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """SELECT *
                FROM product ORDER BY sku;
                """
            )

            # Only skip products if we are not on the first page
            if page > 1:
                cur.fetchmany((page-1) * page_size)  # Skip the products from previous pages
            
            products = cur.fetchmany(page_size + 1)  # Fetch one additional product

    # If we got page_size + 1 products, then there is a next page
    has_next_page = len(products) > page_size

    # Drop the extra product, if it exists
    products = products[:page_size]

    return render_template('products/products_index.html', products=products, page=page, page_size=page_size, has_next_page=has_next_page)

@app.route("/products/register", methods=("GET", "POST"))
def products_register():
    if request.method == "POST":

        sku = request.form["sku"]
        name = request.form["name"]
        price = request.form["price"]
        ean = request.form["ean"]
        description = request.form["description"]
        
        try:
            price, ean, description = verify_product(sku, name, price, ean, description)
        except Exception as e:
            flash(str(e))
            return render_template("products/products_register.html", sku=sku, name=name, description=description, price=price, ean=ean)
        
        try:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        INSERT INTO product (sku, name, description, price, ean)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (sku, name, description, price, ean)
                    )
        except psycopg.errors.UniqueViolation:
            flash('That SKU is already in use!')
            return render_template("products/products_register.html", sku=sku, name=name, description=description, price=price, ean=ean)

        return redirect(url_for("products_index"))

    return render_template("products/products_register.html")

@app.route("/products/<string:sku>/edit", methods=("GET", "POST"))
def products_edit(sku):
    if request.method == "POST":
        
        price = request.form["price"]
        description = request.form["description"]

        try:
            price, description = verify_edit_product(price, description)
        except Exception as e:
            flash(str(e))
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    product = cur.execute(
                        """
                        SELECT * FROM product
                        WHERE sku = %s
                        """,
                        (sku,)
                    ).fetchone()

            return render_template("products/products_edit.html", product=product)
                    
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                cur.execute("""
                    UPDATE product 
                    SET description = %s, price = %s
                    WHERE sku = %s
                    """, (description, price, sku))

        return redirect(url_for("products_index"))
    else:
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                product = cur.execute(
                    """
                    SELECT * FROM product
                    WHERE sku = %s
                    """,
                    (sku,)
                ).fetchone()
    
        return render_template("products/products_edit.html", product=product)

@app.route("/products/<string:sku>/remove", methods=("GET", "POST"))
def products_remove(sku):
    if request.method == "POST":
        if "confirm" in request.form:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute("START TRANSACTION;")
                    cur.execute("UPDATE supplier SET sku = %s WHERE sku = %s", (None, sku,))
                    cur.execute("DELETE FROM contains WHERE sku =%s;", (sku, ))
                    cur.execute(
                        """
                        DELETE FROM product WHERE sku = %s
                        """,
                        (sku, )
                    )
                    cur.execute("COMMIT;")
        return redirect(url_for("products_index"))

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            product = cur.execute(
                """SELECT *
                FROM product WHERE sku = %s
                """,
                (sku, )
            ).fetchone()

    return render_template("products/products_remove.html", product=product)



@app.route("/suppliers", methods=("GET",))
def suppliers_index():
    page_size = 5
    page = request.args.get('page', 1, type=int)

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute(
                """
                SELECT * FROM supplier
                ORDER BY tin
                """
            )

            # Only skip products if we are not on the first page
            if page > 1:
                cur.fetchmany((page-1) * page_size)  # Skip the products from previous pages
            
            suppliers = cur.fetchmany(page_size + 1)  # Fetch one additional product

    # If we got page_size + 1 products, then there is a next page
    has_next_page = len(suppliers) > page_size

    # Drop the extra product, if it exists
    suppliers = suppliers[:page_size]

    return render_template("suppliers/suppliers_index.html", suppliers=suppliers, page=page, page_size=page_size, has_next_page=has_next_page)

@app.route("/suppliers/register", methods=("GET", "POST"))
def suppliers_register():
    if request.method == "POST":
        
        error = None 

        tin = request.form["tin"]
        if not tin:
            error = 'TIN is required.'
        elif not tin.isnumeric():
            error = 'TIN should be numeric'
        elif len(tin) > 20:
            error = 'TIN should not exceed 20 digits'

        name = request.form["name"]
        if name and len(name) > 200:
            error = 'Name should not exceed 200 characters.'
        elif name == '':
            name = None

        address = request.form["address"]
        if address and len(address) > 255:
            error = 'Address should not exceed 255 characters.'
        elif address == '':
            address = None

        sku = request.form["sku"]
        if sku == '':
            sku = None
        elif not sku.isnumeric():
            error = 'SKU should be numeric.'
        elif len(sku) > 25:
            error = 'SKU should not exceed 25 digits'

        date = request.form.get("date")
        if date == '':
            date = None

        if error is not None:
            flash(error)
            return render_template("suppliers/suppliers_register.html", tin=tin, name=name, address=address, sku=sku, date=date)

        try:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    #TRY CATCH
                    cur.execute(
                        """
                        INSERT INTO supplier (tin, name, address, sku, date)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (tin, name, address, sku, date)
                    )
        except psycopg.errors.UniqueViolation:
            flash('That TIN is already in use!')
            return render_template("suppliers/suppliers_register.html", tin=tin, name=name, address=address, sku=sku, date=date)

        return redirect(url_for("suppliers_index"))

    return render_template("suppliers/suppliers_register.html")

@app.route("/suppliers/<string:tin>/remove", methods=("GET", "POST"))
def suppliers_remove(tin):
    if request.method == "POST":
        if "confirm" in request.form:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute("START TRANSACTION;")
                    cur.execute("DELETE FROM delivery WHERE tin = %s", (tin,))
                    cur.execute(
                        """
                        DELETE FROM supplier WHERE tin = %s
                        """,
                        (tin, )
                    )
                    cur.execute("COMMIT;")

        return redirect(url_for("suppliers_index"))

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            supplier = cur.execute(
                """SELECT * FROM supplier
                WHERE tin = %s
                """,
                (tin, )
            ).fetchone()

    return render_template("suppliers/suppliers_remove.html", supplier=supplier)



@app.route("/clients", methods=("GET",))
def clients_index():
    page_size = 5
    page = request.args.get('page', 1, type=int)

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            clients = cur.execute(
                """
                SELECT * FROM customer
                WHERE name != 'N/A'
                ORDER BY cust_no
                """
            )

            # Only skip products if we are not on the first page
            if page > 1:
                cur.fetchmany((page-1) * page_size)  # Skip the products from previous pages
            
            clients = cur.fetchmany(page_size + 1)  # Fetch one additional product

    # If we got page_size + 1 products, then there is a next page
    has_next_page = len(clients) > page_size

    # Drop the extra product, if it exists
    clients = clients[:page_size]
    
    return render_template('clients/clients_index.html', clients=clients, page=page, page_size=page_size, has_next_page=has_next_page)

@app.route("/clients/register", methods=("GET", "POST"))
def clients_register():
    if request.method == "POST":

        error = None 

        cust_no = request.form["cust_no"]
        if not cust_no:
            error = 'Customer Number is required.'
        
        name = request.form["name"]
        if not name:
            error = 'Name is required.'
        elif len(name) > 80:
            error = 'Name should not exceed 80 characters.'

        email = request.form["email"]
        if not email:
            error = 'Email is required.'
        if len(email) > 254:
            error = 'Email should not exceed 254 characters.'
        
        phone = request.form["phone"]
        if phone and len(phone) > 15:
            error = 'Phone number should not exceed 15 digits.'
        elif phone == '':
            phone = None

        address = request.form["address"]
        if address and len(address) > 255:
            error = 'Address should not exceed 255 characters.'
        elif address == '':
            address = None

        if error is not None:
            flash(error)
            return render_template("clients/clients_register.html", cust_no=cust_no, name=name, email=email, phone=phone, address=address)

        try:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        INSERT INTO customer (cust_no, name, email, phone, address)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (cust_no, name, email, phone, address, )
                    )
        except psycopg.errors.UniqueViolation:
            flash('Customer number or email duplicated!')
            return render_template("clients/clients_register.html", cust_no=cust_no, name=name, email=email, phone=phone, address=address)



        return redirect(url_for("clients_index"))

    return render_template("clients/clients_register.html")

@app.route("/clients/<int:cust_no>/remove", methods=("GET", "POST"))
def clients_remove(cust_no):
    if request.method == "POST":
        if "confirm" in request.form:
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        UPDATE customer
                        SET name = 'N/A', email = 'N/A', phone = %s, address = %s
                        WHERE cust_no = %s
                        """,
                        (None, None, cust_no,)
                    )

        return redirect(url_for("clients_index"))

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            client = cur.execute(
                """SELECT * FROM customer 
                WHERE cust_no = %s
                """,
                (cust_no, )
            ).fetchone()

    return render_template("clients/clients_remove.html", client=client)

        

#------------------------HELPER-------------------------

def is_float(n):
    try:
        float_n = float(n)
    except ValueError:
        return None
    else:
        return float_n

def verify_product(sku, name, price, ean, description):
    # Trata do SKU
    if not sku:
        raise Exception('SKU is required!')
    elif len(sku) > 25:
        raise Exception('SKU should not exceed 25 characters.')

    # Trata do nome
    if not name:
        raise Exception('Name is required!')
    elif len(name) > 200:
        raise Exception('Name should not exceed 200 characters.')
    
    # Trata do preço
    try:
        price = float(price)
    except ValueError:
        raise Exception('Price should be a number!')
    if price < 0:
        raise Exception('Price should be positive!')
    elif price > 9999999999.99:
        raise Exception('Price should be less than 10000000000!')

    # Trata do ean
    if ean and not ean.isdigit():
        raise Exception('EAN should be a number!')
    elif len(ean) > 13:
        raise Exception('EAN should not exceed 13 digits!')
    elif ean == '':
        ean = None

    # trata da descrição
    if description and len(description) > 255:
        raise Exception('Description can\'t exceed 255 characters!')
    elif description == '':
        description = None

    return price, ean, description

def verify_edit_product(price,description):
    # Trata do preço
    try:
        price = float(price)
    except ValueError:
        raise Exception('Price should be a number!')
    if price < 0:
        raise Exception('Price should be positive!')
    elif price > 9999999999.99:
        raise Exception('Price should be less than 10000000000!')

    # trata da descrição
    if description and len(description) > 255:
        raise Exception('Description can\'t exceed 255 characters!')
    elif description == '':
        description = None

    return price, description



def get_order_no():
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            value = cur.execute("SELECT MAX(order_no) FROM orders;")

            
            value = cur.fetchone()  #
    return int(value.max)+1
#-------------------------------------------------------




@app.route("/ping", methods=("GET",))
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
    app.run()
