from flask import session


def check_in_session(id):
    if "products" not in session:
        return False
    return id in session.get('products')

