function drawCart(cart) {
    var place = document.getElementById('cart');
    if (cart.items.length == 0) {
        place.innerHTML = '<div class="empty"><h2>Корзина пуста</h2><p>Загляните в меню и выберите что-нибудь вкусное.</p><a href="index.html" class="btn">Перейти в меню</a></div>';
        showReveal();
        return;
    }
    var html = '<div class="layout-split"><div class="panel">';
    cart.items.forEach(function (item) {
        html += '<div class="cart-row" data-item="' + item.id + '">';
        html += '<div class="cart-row__thumb">';
        if (item.pizza.image) {
            html += '<img src="' + item.pizza.image + '" alt="">';
        } else {
            html += safe(item.pizza.name.charAt(0));
        }
        html += '</div>';
        html += '<div class="cart-row__info"><div class="cart-row__name">' + safe(item.pizza.name) + '</div>';
        html += '<div class="muted">' + formatPrice(item.pizza.price) + ' за шт.</div></div>';
        html += '<div class="qty">';
        html += '<button type="button" class="qty__btn" data-step="-1" aria-label="Уменьшить">−</button>';
        html += '<span class="qty__value">' + item.quantity + '</span>';
        html += '<button type="button" class="qty__btn" data-step="1" aria-label="Увеличить">+</button></div>';
        html += '<div class="cart-row__sum" data-subtotal>' + formatPrice(item.subtotal) + '</div>';
        html += '<div class="cart-row__remove"><button type="button" class="link-button link-button--danger">Удалить</button></div>';
        html += '</div>';
    });
    html += '</div><aside class="panel summary">';
    html += '<div class="summary__row"><span>Итого</span><span class="price price--big" data-cart-total>' + formatPrice(cart.total_price) + '</span></div>';
    html += '<a href="checkout.html" class="btn btn--block">Оформить заказ</a>';
    html += '<a href="index.html" class="btn btn--ghost btn--block">Продолжить покупки</a>';
    html += '</aside></div>';
    place.innerHTML = html;
    showReveal();
}

function loadCart() {
    api('cart/').then(function (answer) {
        if (answer.status != 200) {
            location.href = 'login.html?next=cart.html';
            return;
        }
        drawCart(answer.data);
    }).catch(function () {
        document.getElementById('cart').innerHTML = '<div class="empty"><h2>Сервер не отвечает</h2><p>Проверьте, что бэкенд запущен.</p></div>';
    });
}

function applyItem(row, data) {
    updateCount(data.count);
    var total = document.querySelector('[data-cart-total]');
    total.textContent = formatPrice(data.total);
    pop(total);

    if (data.quantity > 0) {
        var value = row.querySelector('.qty__value');
        value.textContent = data.quantity;
        pop(value);
        var subtotal = row.querySelector('[data-subtotal]');
        subtotal.textContent = formatPrice(data.subtotal);
        pop(subtotal);
        return;
    }
    row.style.height = row.offsetHeight + 'px';
    void row.offsetHeight;
    row.classList.add('is-removing');
    setTimeout(function () {
        row.remove();
        if (!document.querySelector('.cart-row')) {
            loadCart();
        }
    }, 400);
}

document.addEventListener('click', function (event) {
    var row = event.target.closest('.cart-row');
    if (!row) {
        return;
    }
    if (event.target.closest('.cart-row__remove')) {
        api('cart/remove/', 'POST', {item_id: Number(row.dataset.item)}).then(function (answer) {
            applyItem(row, answer.data);
        }).catch(showError);
        return;
    }
    var button = event.target.closest('[data-step]');
    if (!button || row.classList.contains('is-busy')) {
        return;
    }
    var quantity = parseInt(row.querySelector('.qty__value').textContent) + parseInt(button.dataset.step);
    if (quantity > 99) {
        return;
    }
    row.classList.add('is-busy');
    api('cart/update_item/', 'POST', {item_id: Number(row.dataset.item), quantity: quantity}).then(function (answer) {
        applyItem(row, answer.data);
    }).catch(showError).finally(function () {
        row.classList.remove('is-busy');
    });
});

if (!needLogin()) {
    loadCart();
}
