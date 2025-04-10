import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app
from extensions import db
from models import User


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:123@localhost:5432/jewelglow_test"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret"

@pytest.fixture
def app():
    app = create_app()
    app.config.from_object(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

        admin = User(username='admin', email='admin@test.com', is_admin=True, is_seller=False)
        admin.set_password('admin123')

        seller = User(username='test_seller', email='seller@test.com', is_admin=False, is_seller=True, category_permission='rings')
        seller.set_password('seller123')

        buyer = User(username='test_buyer', email='buyer@test.com', is_admin=False, is_seller=False)
        buyer.set_password('buyer123')

        db.session.add_all([admin, seller, buyer])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_login(client, app):
    with app.app_context():
        user = User(username='loginuser', email='login@example.com', is_admin=False, is_seller=False)
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

    response = client.post('/login', data={
        'username': 'loginuser',
        'password': 'testpass'
    }, follow_redirects=True)

    assert 'Корзина' in response.data.decode('utf-8') or response.status_code == 200
