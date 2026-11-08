function loadCheckout() {
    Promise.all([api('cart/'), api('auth/me/')]).then(function (answers) {
        var cart = answers[0].data;
        if (answers[0].status != 200) {
            location.href = 'login.html?next=checkout.html';
            return;
        }
        if (cart.items.length == 0) {
            toastNextPage('Корзина пуста');
            location.href = 'index.html';
            return;
        }
        var html = '<h2 class="summary__title">Ваш заказ</h2>';
        cart.items.forEach(function (item) {
            html += '<div class="summary__line"><span>' + safe(item.pizza.name) + ' × ' + item.quantity + '</span><span>' + formatPrice(item.subtotal) + '</span></div>';
        });
        html += '<div class="summary__row"><span>Итого</span><span class="price price--big">' + formatPrice(cart.total_price) + '</span></div>';
        html += '<a href="cart.html" class="btn btn--ghost btn--block">Изменить корзину</a>';
        document.getElementById('summary').innerHTML = html;

        document.getElementById('address').value = answers[1].data.last_address || '';
        document.getElementById('phone').value = answers[1].data.last_phone || '';
        showReveal();
    }).catch(showError);
}

document.getElementById('checkout-form').addEventListener('submit', function (event) {
    event.preventDefault();
    var data = {
        address: document.getElementById('address').value.trim(),
        phone: document.getElementById('phone').value.trim()
    };
    api('orders/', 'POST', data).then(function (answer) {
        if (answer.status == 201) {
            toastNextPage('Заказ #' + answer.data.id + ' оформлен!');
            location.href = 'order.html?id=' + answer.data.id;
        } else {
            showMessages(document.getElementById('errors'), answer.data.errors || ['Не удалось оформить заказ']);
        }
    }).catch(showError);
});

if (!needLogin()) {
    loadCheckout();
}
