async function addToCart(event, productId) {
    event.preventDefault();
    event.stopPropagation();
    
    try {
        const response = await fetch('/api/add_to_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                product_id: productId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showCartNotification(data.message);
            updateCartCounter(data.cart_count);
        } else {
            showCartNotification(data.message || 'Ошибка при добавлении');
            if (response.status === 401) {
                window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
            }
        }
    } catch (error) {
        showCartNotification('Ошибка соединения');
        console.error('Error:', error);
    }
}

async function updateCartItem(cartItemId, quantity) {
    try {
        const response = await fetch('/api/update_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                product_id: cartItemId,
                quantity: quantity
            })
        });
        
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return { success: false, message: 'Ошибка соединения' };
    }
}

async function removeFromCart(cartItemId) {
    try {
        const response = await fetch('/api/remove_from_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                product_id: cartItemId
            })
        });
        
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return { success: false, message: 'Ошибка соединения' };
    }
}

function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

function showCartNotification(message) {
    document.querySelectorAll('.cart-notification').forEach(el => el.remove());
    
    const notification = document.createElement('div');
    notification.className = 'cart-notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function updateCartCounter(count) {
    const counter = document.querySelector('.cart-count');
    if (counter) {
        counter.textContent = count;
        counter.classList.add('pulse');
        setTimeout(() => counter.classList.remove('pulse'), 500);
    }
}

// Инициализация обработчиков для корзины
document.addEventListener('DOMContentLoaded', function() {
    // Обработчики изменения количества
    document.querySelectorAll('.cart-item-quantity').forEach(input => {
        input.addEventListener('change', async function() {
            const cartItemId = this.dataset.cartItemId;
            const quantity = parseInt(this.value);
            
            if (quantity > 0) {
                const result = await updateCartItem(cartItemId, quantity);
                if (result.success) {
                    location.reload(); // Обновляем страницу для отображения новых сумм
                } else {
                    showCartNotification(result.message || 'Ошибка обновления');
                }
            }
        });
    });
    
    // Обработчики удаления товаров
    document.querySelectorAll('.remove-from-cart').forEach(button => {
        button.addEventListener('click', async function() {
            const cartItemId = this.dataset.cartItemId;
            const result = await removeFromCart(cartItemId);
            if (result.success) {
                this.closest('.cart-item').remove();
                updateCartCounter(result.cart_count);
                showCartNotification('Товар удален из корзины');
                
                // Обновляем итоговую сумму
                updateCartTotal();
            } else {
                showCartNotification(result.message || 'Ошибка удаления');
            }
        });
    });
    
    // Функция обновления итоговой суммы
    function updateCartTotal() {
        let total = 0;
        document.querySelectorAll('.cart-item').forEach(item => {
            const price = parseFloat(item.dataset.price);
            const quantity = parseInt(item.querySelector('.cart-item-quantity').value);
            total += price * quantity;
        });
        
        document.querySelector('.cart-total').textContent = total.toFixed(2);
    }
});