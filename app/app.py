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
            cur.execute("SELECT sku, name, description, price, ean FROM product ORDER BY sku;")
            
            # Only skip products if we are not on the first page
            if page > 1:
                cur.fetchmany((page-1) * page_size)  # Skip the products from previous pages
            
            products = cur.fetchmany(page_size + 1)  # Fetch one additional product

    # If we got page_size + 1 products, then there is a next page
    has_next_page = len(products) > page_size

    # Drop the extra product, if it exists
    products = products[:page_size]

    return render_template('products/products_index.html', products=products, page=page, page_size=page_size, has_next_page=has_next_page)



@app.route("/products/register", methods=["GET", "POST"])
def products_register():
    if request.method == "POST":
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                sku = request.form["sku"]
                name = request.form["name"]
                description = request.form["description"]
                price = float(request.form["price"])
                ean = request.form["ean"]

                ###### ERROS PARA OS INPUTSAIOJFWAHEFGUAHGAUHGAUHWGUAWHGUWAOGHUWO

                sql = "INSERT INTO product (sku, name, description, price, ean) VALUES (%s, %s, %s, %s, %s)"
                values = (sku, name, description, price, ean)
                cur.execute(sql, values)
            conn.commit()

        return redirect(url_for("products_index"))

    return render_template("products/products_register.html")



@app.route("/products/edit", methods=("GET",))
def products_edit():
    # your code here
    pass

@app.route("/products/remove", methods=("GET",))
def products_remove():
    # your code here
    pass



@app.route("/suppliers", methods=("GET",))
def suppliers_index():
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute("""
                SELECT * FROM supplier
                ORDER BY tin
            """)
            suppliers = cur.fetchall()
    return render_template("suppliers/suppliers_index.html", suppliers=suppliers)


@app.route("/suppliers/register", methods=("GET",))
def suppliers_register():
    # your code here
    pass

@app.route("/suppliers/remove", methods=("GET",))
def suppliers_remove():
    # your code here
    pass



@app.route("/clients", methods=("GET",))
def clients_index():
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            cur.execute("""
                SELECT * FROM customer
                ORDER BY cust_no
            """)
            clients = cur.fetchall()
    return render_template('clients/clients_index.html', clients=clients)


@app.route("/clients/register", methods=("GET",))
def clients_register():
    # your code here
    pass

@app.route("/clients/remove", methods=("GET",))
def clients_remove():
    # your code here
    pass

        











@app.route("/ping", methods=("GET",))
def ping():
    log.debug("ping!")
    return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
    app.run()
