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
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://postgres:postgres@postgres/postgres")

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
    """Show the menu page, used to group actions based on type"""
    return render_template("menu/menu.html")



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
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:

                error = None 

                sku = request.form["sku"]
                if not sku:
                    error = 'SKU is required'
                else:
                    existing_sku = cur.execute(
                        """
                        SELECT sku FROM product 
                        WHERE sku = %s
                        """,
                        (sku,)
                    ).fetchone()

                    if existing_sku is not None:
                        error = 'The SKU already exists. Please choose a different one.'

                name = request.form["name"]
                if not name:
                    error = 'Name is required.'
                elif len(name) > 200:
                    error = 'Name should not exceed 200 characters.'

                price = request.form["price"]
                if not is_float(price):
                    error = 'Price should be a number.'
                elif float(price) < 0 or float(price) > 9999999999.99 :
                    error = 'Price should be positive and less than 10000000000.'

                ean = request.form["ean"]
                if ean and not ean.isdigit():
                    error = 'EAN should be a number.'
                elif ean == '':
                    ean = None

                description = request.form["description"]
                if description and len(description) > 255:
                    error = 'Description should not exceed 255 characters.'
                elif description == '':
                    description = None

                if error is not None:
                    flash(error)
                    return render_template("products/products_register.html", sku=sku, name=name, description=description, price=price, ean=ean)


                else:
                    cur.execute(
                    """
                    INSERT INTO product (sku, name, description, price, ean)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (sku, name, description, price, ean))

                conn.commit()

            return redirect(url_for("products_index"))

    return render_template("products/products_register.html")

@app.route("/products/<string:old_sku>/edit", methods=("GET", "POST"))
def products_edit(old_sku):
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:

            if request.method == "POST":
                error = None 

                new_sku = request.form["sku"]
                if not new_sku:
                    error = 'SKU is required'
                elif int(new_sku) != int(old_sku):
                    existing_sku = cur.execute(
                        """
                        SELECT sku FROM product 
                        WHERE sku = %s
                        """,
                        (new_sku,)
                    ).fetchone()

                    if existing_sku is not None:
                        error = 'The SKU already exists. Please choose a different one.'

                name = request.form["name"]
                if not name:
                    error = 'Name is required.'
                elif len(name) > 200:
                    error = 'Name should not exceed 200 characters.'

                price = request.form["price"]
                if not is_float(price):
                    error = 'Price should be a number.'
                elif float(price) < 0 or float(price) > 9999999999.99 :
                    error = 'Price should be positive and less than 10000000000.'

                ean = request.form["ean"]
                if ean and not ean.isdigit():
                    error = 'EAN should be a number.'
                elif ean == '':
                    ean = None

                description = request.form["description"]
                if description and len(description) > 255:
                    error = 'Description should not exceed 255 characters.'
                elif description == '':
                    description = None

                if error is not None:
                    flash(error)
                    Product = namedtuple('Product', ['sku', 'name', 'description', 'price', 'ean'])
                    product = Product(sku=new_sku, name=name, description=description, price=price, ean=ean)
                    return render_template("products/products_edit.html", product=product)


                else:
                    cur.execute(
                        """
                        UPDATE product 
                        SET sku = %s, name = %s, description = %s, price = %s, ean = %s
                        WHERE sku = %s
                        """,
                        (new_sku, name, description, price, ean, old_sku)
                    )

                conn.commit()
                return redirect(url_for("products_index"))
        

            cur.execute(
                """
                SELECT * FROM product
                WHERE sku = %s
                """,
                (old_sku, )
                )
            product = cur.fetchone()
    return render_template("products/products_edit.html", product=product)

@app.route("/products/<string:sku>/remove", methods=("GET", "POST"))
def products_remove(sku):
    if request.method == "POST":
        if "confirm" in request.form:
            # product deletion code here
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        DELETE FROM product WHERE sku = %s
                        """,
                        (sku, )
                    )

                conn.commit()
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
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            suppliers = cur.execute(
                """
                SELECT * FROM supplier
                ORDER BY tin
                """
            ).fetchall()

    return render_template("suppliers/suppliers_index.html", suppliers=suppliers)

@app.route("/suppliers/register", methods=("GET",))
def suppliers_register():
    # your code here
    pass

@app.route("/suppliers/<string:tin>/remove", methods=("GET", "POST"))
def suppliers_remove(tin):
    if request.method == "POST":
        if "confirm" in request.form:
            # product deletion code here
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        DELETE FROM supplier WHERE tin = %s
                        """,
                        (tin, )
                    )

                conn.commit()
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
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            clients = cur.execute(
                """
                SELECT * FROM customer
                ORDER BY cust_no
                """
            ).fetchall()
    
    return render_template('clients/clients_index.html', clients=clients)

@app.route("/clients/register", methods=("GET",))
def clients_register():
    # your code here
    pass

@app.route("/clients/<int:cust_no>/remove", methods=("GET", "POST"))
def clients_remove(cust_no):
    if request.method == "POST":
        if "confirm" in request.form:
            # product deletion code here
            with pool.connection() as conn:
                with conn.cursor(row_factory=namedtuple_row) as cur:
                    cur.execute(
                        """
                        DELETE FROM customer 
                        WHERE cust_no = %s
                        """,
                        (cust_no, )
                    )
                conn.commit()

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
        return False
    else:
        return True


#-------------------------------------------------------




@app.route("/ping", methods=("GET",))
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
    app.run()
