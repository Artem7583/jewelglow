from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import random
from sqlalchemy import func
from config import Config
from extensions import db, login_manager
from models import User, Product, Cart, Order, OrderItem

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_vars():
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = Cart.query.filter_by(user_id=current_user.id).count()
        else:
            cart = session.get('cart', {})
            cart_count = sum(cart.values())
        
        return dict(
            current_user=current_user,
            categories=['rings', 'earrings', 'bracelets', 'pendants', 'watches'],
            cart_count=cart_count
        )

    @app.template_filter('format_currency')
    def format_currency(value):
        return "{:,.2f}".format(value).replace(",", " ")

    @app.route('/')
    def index():
        # Получаем случайные 10 товаров из всех категорий
        products = Product.query.order_by(func.random()).limit(10).all()
        return render_template('index.html', products=products)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                
                if 'cart' in session:
                    for product_id, quantity in session['cart'].items():
                        cart_item = Cart.query.filter_by(
                            user_id=user.id,
                            product_id=product_id
                        ).first()
                        
                        if cart_item:
                            cart_item.quantity += quantity
                        else:
                            cart_item = Cart(
                                user_id=user.id,
                                product_id=product_id,
                                quantity=quantity
                            )
                            db.session.add(cart_item)
                    
                    db.session.commit()
                    session.pop('cart', None)
                
                return redirect(url_for('index'))
            
        return render_template('auth/login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            if User.query.filter_by(username=username).first():
                flash('Это имя пользователя уже занято', 'error')
                return redirect(url_for('register'))
            
            if len(password) < 8 or not all(ord(c) < 128 for c in password):
                flash('Пароль должен содержать минимум 8 символов (только английские буквы)', 'error')
                return redirect(url_for('register'))
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=False,
                is_seller=False
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Регистрация прошла успешно. Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/category/<category_name>')
    def category(category_name):
        if category_name not in ['rings', 'earrings', 'bracelets', 'pendants', 'watches']:
            abort(404)
        
        products = Product.query.filter_by(category=category_name).all()
        template_map = {
            'rings': 'categories/rings.html',
            'earrings': 'categories/earrings.html',
            'bracelets': 'categories/bracelets.html',
            'pendants': 'categories/pendants.html',
            'watches': 'categories/watches.html'
        }
        
        show_add_button = False
        if current_user.is_authenticated and current_user.is_seller:
            show_add_button = (current_user.category_permission == category_name)
        
        return render_template(template_map[category_name], 
                            products=products,
                            current_category=category_name,
                            show_add_button=show_add_button)

    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)
        
        can_delete = False
        if current_user.is_authenticated:
            can_delete = (current_user.is_admin or 
                         (current_user.is_seller and current_user.category_permission == product.category))
        
        return render_template('product/detail.html',
                            product=product,
                            can_delete=can_delete)

    @app.route('/api/add_to_cart', methods=['POST'])
    def api_add_to_cart():
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Неверный запрос'}), 400
        
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'message': 'Не указан ID товара'}), 400
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Товар не найден'}), 404
        
        if current_user.is_authenticated:
            cart_item = Cart.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()
            
            if cart_item:
                cart_item.quantity += 1
            else:
                cart_item = Cart(
                    user_id=current_user.id,
                    product_id=product_id,
                    quantity=1
                )
                db.session.add(cart_item)
            
            db.session.commit()
            cart_count = Cart.query.filter_by(user_id=current_user.id).count()
        else:
            cart = session.get('cart', {})
            cart[str(product_id)] = cart.get(str(product_id), 0) + 1
            session['cart'] = cart
            cart_count = sum(cart.values())
        
        return jsonify({
            'success': True,
            'cart_count': cart_count,
            'message': f'{product.name} добавлен в корзину'
        })

    @app.route('/api/cart', methods=['GET'])
    def api_get_cart():
        cart_items = []
        total = 0
        
        if current_user.is_authenticated:
            items = db.session.query(Cart, Product).join(Product).filter(
                Cart.user_id == current_user.id
            ).all()
        
            for item in items:
                cart_items.append({
                    'id': item.Cart.id,
                    'product_id': item.Product.id,
                    'name': item.Product.name,
                    'quantity': item.Cart.quantity,
                    'image': item.Product.image,
                    'total': item.Product.price * item.Cart.quantity
                })
        else:
            cart = session.get('cart', {})
            for product_id, quantity in cart.items():
                product = Product.query.get(product_id)
                if product:
                    cart_items.append({
                        'product_id': product.id,
                        'name': product.name,
                        'quantity': quantity,
                        'image': product.image,
                        'total': product.price * quantity
                    })
        
        total = sum(item['total'] for item in cart_items)
        
        return jsonify({
            'items': cart_items,
            'total': total,
            'count': len(cart_items)
        })

    @app.route('/cart')
    def view_cart():
        cart_items = []
        total = 0
        
        if current_user.is_authenticated:
            items = db.session.query(Cart, Product).join(Product).filter(
                Cart.user_id == current_user.id
            ).all()
            
            for item in items:
                cart_items.append({
                    'id': item.Cart.id,
                    'name': item.Product.name,
                    'price': item.Product.price,
                    'quantity': item.Cart.quantity,
                    'image': item.Product.image,
                    'total': item.Product.price * item.Cart.quantity
                })
        else:
            cart = session.get('cart', {})
            for product_id, quantity in cart.items():
                product = Product.query.get(product_id)
                if product:
                    cart_items.append({
                        'id': product_id,
                        'name': product.name,
                        'price': product.price,
                        'quantity': quantity,
                        'image': product.image,
                        'total': product.price * quantity
                    })
        
        total = sum(item['total'] for item in cart_items)
        
        return render_template('cart.html', 
                            cart_items=cart_items,
                            total=total)

    @app.route('/api/update_cart', methods=['POST'])
    def api_update_cart():
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Неверный запрос'}), 400
        
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        
        if not product_id or not quantity or quantity < 1:
            return jsonify({'success': False, 'message': 'Неверные данные'}), 400
        
        if current_user.is_authenticated:
            cart_item = Cart.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()
            
            if cart_item:
                cart_item.quantity = quantity
                db.session.commit()
        else:
            cart = session.get('cart', {})
            cart[str(product_id)] = quantity
            session['cart'] = cart
        
        return jsonify({'success': True})

    @app.route('/api/remove_from_cart', methods=['POST'])
    def api_remove_from_cart():
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Неверный запрос'}), 400
        
        data = request.get_json()
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'message': 'Не указан ID товара'}), 400
        
        if current_user.is_authenticated:
            Cart.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).delete()
            db.session.commit()
        else:
            cart = session.get('cart', {})
            cart.pop(str(product_id), None)
            session['cart'] = cart
        
        return jsonify({'success': True})

    @app.route('/api/save_discount', methods=['POST'])
    @login_required
    def api_save_discount():
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Неверный запрос'}), 400
        
        data = request.get_json()
        discount = data.get('discount', 0)
        
        if discount <= 0:
            return jsonify({'success': False, 'message': 'Нет скидки для сохранения'}), 400
        
        if current_user.has_discount and not current_user.discount_used:
            return jsonify({'success': False, 'message': 'У вас уже есть неиспользованная скидка'}), 400
        
        current_user.has_discount = True
        current_user.discount_value = min(discount, 10)
        current_user.discount_used = False
        db.session.commit()
        
        return jsonify({'success': True})

    @app.route('/checkout', methods=['GET', 'POST'])
    @login_required
    def checkout():
        cart_items = db.session.query(Cart, Product).join(Product).filter(
            Cart.user_id == current_user.id
        ).all()
        
        if not cart_items:
            return redirect(url_for('view_cart'))
        
        subtotal = sum(item.Product.price * item.Cart.quantity for item in cart_items)
        
        if request.method == 'POST':
            try:
                required_fields = ['phone', 'city', 'street', 'house', 'payment']
                for field in required_fields:
                    if not request.form.get(field):
                        flash(f'Поле {field} обязательно для заполнения', 'error')
                        return redirect(url_for('checkout'))
                
                use_discount = request.form.get('use_discount') == 'on'
                discount = 0
                
                if use_discount and current_user.has_discount and not current_user.discount_used:
                    discount = current_user.discount_value
                    current_user.discount_used = True
                
                total_amount = subtotal * (1 - discount / 100)
                
                delivery_days = random.randint(3, 14)
                delivery_date = datetime.utcnow() + timedelta(days=delivery_days)
                
                city = request.form['city']
                street = request.form['street']
                house = request.form['house']
                apartment = request.form.get('apartment', '')
                shipping_address = f"{city}, {street}, д. {house}" + (f", кв. {apartment}" if apartment else "")
                
                order = Order(
                    user_id=current_user.id,
                    order_date=datetime.utcnow(),
                    delivery_date=delivery_date,
                    total_amount=total_amount,
                    shipping_address=shipping_address,
                    payment_method=request.form['payment'],
                    contact_phone=request.form['phone'],
                    notes=request.form.get('notes', ''),
                    status='Обрабатывается',
                    discount_applied=discount
                )
                db.session.add(order)
                db.session.flush()
                
                for item in cart_items:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item.Product.id,
                        quantity=item.Cart.quantity,
                        price=item.Product.price
                    )
                    db.session.add(order_item)
                
                Cart.query.filter_by(user_id=current_user.id).delete()
                db.session.commit()
                
                return redirect(url_for('order_details', order_id=order.id))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Checkout error: {str(e)}", exc_info=True)
                flash(f'Произошла ошибка при оформлении заказа: {str(e)}', 'error')
                return redirect(url_for('checkout'))
        
        return render_template('checkout.html',
                            cart_items=cart_items,
                            total=subtotal,
                            has_discount=current_user.has_discount and not current_user.discount_used,
                            discount_value=current_user.discount_value if current_user.has_discount else 0)

    @app.route('/orders')
    @login_required
    def orders():
        user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
        return render_template('orders.html', orders=user_orders)

    @app.route('/order/<int:order_id>')
    @login_required
    def order_details(order_id):
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id and not current_user.is_admin:
            abort(403)
        
        items = db.session.query(OrderItem, Product).join(Product).filter(
            OrderItem.order_id == order_id
        ).all()

        if not order.status:
            order.status = 'Обрабатывается'
        if not order.payment_method:
            order.payment_method = 'Не указан'
        if not order.shipping_address:
            order.shipping_address = 'Не указан'
        
        return render_template('order_details.html', 
                            order=order,
                            items=items)

    @app.route('/admin/add-product', methods=['GET', 'POST'])
    @login_required
    def admin_add_product():
        if not (current_user.is_admin or current_user.is_seller):
            abort(403)
        
        if request.method == 'POST':
            try:
                name = request.form['name']
                short_desc = request.form['short_desc']
                full_desc = request.form['full_desc']
                price = float(request.form['price'])
                
                if current_user.is_seller:
                    category = current_user.category_permission
                else:
                    category = request.form['category']
                
                image = request.files['image']
                image_url = None
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path)
                    image_url = f"uploads/{filename}"
                
                product = Product(
                    name=name,
                    short_desc=short_desc,
                    full_desc=full_desc,
                    price=price,
                    category=category,
                    image=image_url
                )
                db.session.add(product)
                db.session.commit()
                
                flash('Товар успешно добавлен', 'success')
                return redirect(url_for('product_detail', product_id=product.id))
            
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error adding product: {e}")
                flash('Произошла ошибка при добавлении товара', 'error')
                return redirect(url_for('admin_add_product'))
        
        return render_template('admin/add_product.html')

    @app.route('/admin/delete-product/<int:product_id>', methods=['POST'])
    @login_required
    def admin_delete_product(product_id):
        product = Product.query.get_or_404(product_id)
        
        if current_user.is_seller and product.category != current_user.category_permission:
            abort(403)
        
        try:
            Cart.query.filter_by(product_id=product_id).delete()
            OrderItem.query.filter_by(product_id=product_id).delete()
            
            if product.image:
                try:
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image.split('/')[-1])
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except OSError as e:
                    app.logger.error(f"Error deleting image file: {e}")
            
            db.session.delete(product)
            db.session.commit()
            
            flash('Товар успешно удален', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting product: {e}")
            flash('Произошла ошибка при удалении товара', 'error')
        
        if current_user.is_seller:
            return redirect(url_for('category', category_name=current_user.category_permission))
        return redirect(url_for('index'))

    @app.route('/seller')
    @login_required
    def seller_redirect():
        if not current_user.is_seller:
            abort(403)
        return redirect(url_for('category', category_name=current_user.category_permission))

    @app.route('/partner')
    def partner():
        return render_template('partner.html')

    @app.route('/brand1')
    def brand1():
        return render_template('brand/brand1.html')

    @app.route('/brand2')
    def brand2():
        return render_template('brand/brand2.html')

    @app.route('/brand3')
    def brand3():
        return render_template('brand/brand3.html')

    @app.route('/brand4')
    def brand4():
        return render_template('brand/brand4.html')

    @app.route('/brand5')
    def brand5():
        return render_template('brand/brand5.html')
    
    @app.route('/qr')
    def qr():
        return render_template('qr.html')
    
    @app.route('/bonus')
    def bonus():
        return render_template('bonus.html')

    @app.route('/search')
    def search():
        query = request.args.get('query', '').strip()
        if query:
            products = Product.query.filter(
                Product.name.ilike(f'%{query}%') | 
                Product.short_desc.ilike(f'%{query}%') |
                Product.full_desc.ilike(f'%{query}%')
            ).all()
        else:
            products = []
        
        return render_template('search_results.html', 
                            products=products, 
                            query=query)

    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@jewelglow.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True,
                is_seller=False
            )
            db.session.add(admin)
            
            sellers = [
                ('seller_ring', 'rings@jewelglow.com', 'rings'),
                ('seller_earring', 'earrings@jewelglow.com', 'earrings'),
                ('seller_bracelet', 'bracelets@jewelglow.com', 'bracelets'),
                ('seller_pendant', 'pendants@jewelglow.com', 'pendants'),
                ('seller_watch', 'watches@jewelglow.com', 'watches')
            ]
            
            for username, email, category in sellers:
                if not User.query.filter_by(username=username).first():
                    seller = User(
                        username=username,
                        email=email,
                        password_hash=generate_password_hash('seller123'),
                        is_admin=False,
                        is_seller=True,
                        category_permission=category
                    )
                    db.session.add(seller)
            
            db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)