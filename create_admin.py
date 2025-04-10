from app import app
from models import User
from extensions import db

def create_admin_and_sellers():
    """Создает администратора и продавцов при первом запуске"""
    with app.app_context():
        db.create_all()
        
        # Главный администратор
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@jewelglow.com',
                is_admin=True,
                is_seller=False
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("Главный администратор создан")
        
        # Продавцы для категорий
        sellers_data = [
            {'username': 'seller_rings', 'category': 'rings', 'email': 'rings@jewelglow.com'},
            {'username': 'seller_earrings', 'category': 'earrings', 'email': 'earrings@jewelglow.com'},
            {'username': 'seller_bracelets', 'category': 'bracelets', 'email': 'bracelets@jewelglow.com'},
            {'username': 'seller_pendants', 'category': 'pendants', 'email': 'pendants@jewelglow.com'},
            {'username': 'seller_watches', 'category': 'watches', 'email': 'watches@jewelglow.com'}
        ]
        
        for data in sellers_data:
            seller = User.query.filter_by(username=data['username']).first()
            if not seller:
                seller = User(
                    username=data['username'],
                    email=data['email'],
                    is_admin=False,
                    is_seller=True,
                    category_permission=data['category']
                )
                seller.set_password('seller123')
                db.session.add(seller)
                print(f"Продавец {data['username']} создан")
        
        db.session.commit()

if __name__ == '__main__':
    create_admin_and_sellers()