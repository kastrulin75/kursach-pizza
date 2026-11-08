var orderId = getParam('id');
var statusSteps = [['new', 'Новый'], ['cooking', 'Готовится'], ['delivering', 'В доставке'], ['done', 'Завершён']];
var timer = null;

function drawOrder(order) {
    document.title = 'Заказ #' + order.id + ' · Пиццерия';
    var html = '<div data-order="' + order.id + '" data-status="' + order.status + '">';
    html += '<a href="orders.html" class="back-link">Назад к заказам</a>';
    html += '<div class="page-head"><h1 class="page-title">Заказ #' + order.id + '</h1>';
    html += '<span class="badge badge--' + order.status + '" data-badge>' + order.status_display + '</span></div>';

    html += '<div class="panel"><div class="status-cancelled" data-cancelled hidden>Заказ отменён</div><ol class="timeline">';
    statusSteps.forEach(function (step) {
        html += '<li class="timeline__step is-todo" data-step-status="' + step[0] + '"><span class="timeline__dot"></span><span class="timeline__label">' + step[1] + '</span></li>';
    });
    html += '</ol><p class="muted timeline__hint" data-hint>Статус обновляется автоматически</p></div>';

    html += '<div class="layout-split"><div class="panel"><h2 class="summary__title">Состав заказа</h2>';
    order.items.forEach(function (item) {
        html += '<div class="summary__line"><span>' + safe(item.pizza_name) + ' × ' + item.quantity + '</span><span>' + formatPrice(item.subtotal) + '</span></div>';
    });
    html += '<div class="summary__row"><span>Итого</span><span class="price price--big">' + formatPrice(order.total_price) + '</span></div></div>';

    html += '<aside class="panel summary"><h2 class="summary__title">Доставка</h2><div class="details">';
    html += '<div><span class="muted">Адрес</span><br>' + safe(order.address) + '</div>';
    html += '<div><span class="muted">Телефон</span><br>' + safe(order.phone) + '</div>';
    html += '<div><span class="muted">Создан</span><br>' + formatDate(order.created_at) + '</div></div>';
    html += '<div class="order-cancel"><button type="button" class="btn btn--danger btn--block" id="cancel">Отменить заказ</button></div>';
    html += '</aside></div></div>';

    document.getElementById('order').innerHTML = html;
    showStatus(order.status, order.status_display, false);
    showReveal();

    document.getElementById('cancel').addEventListener('click', function () {
        if (!confirm('Отменить заказ #' + order.id + '?')) {
            return;
        }
        api('orders/' + order.id + '/cancel/', 'POST').then(function (answer) {
            if (answer.status == 200) {
                showStatus(answer.data.status, answer.data.status_display, true);
                showToast('Заказ #' + order.id + ' отменён', 'warning');
            } else {
                showToast(answer.data.error, 'error');
            }
        }).catch(showError);
    });
}

function showStatus(status, name, animate) {
    var box = document.querySelector('[data-order]');
    box.dataset.status = status;
    var badge = box.querySelector('[data-badge]');
    badge.className = 'badge badge--' + status;
    badge.textContent = name;
    if (animate) {
        pop(badge);
    }

    var current = -1;
    statusSteps.forEach(function (step, index) {
        if (step[0] == status) {
            current = index;
        }
    });
    box.querySelectorAll('[data-step-status]').forEach(function (step, index) {
        step.classList.remove('is-done', 'is-current', 'is-todo');
        if (status == 'cancelled' || index > current) {
            step.classList.add('is-todo');
        } else if (index == current) {
            step.classList.add('is-current');
        } else {
            step.classList.add('is-done');
        }
    });

    box.querySelector('.timeline').hidden = status == 'cancelled';
    box.querySelector('[data-cancelled]').hidden = status != 'cancelled';
    box.querySelector('[data-hint]').hidden = status == 'done' || status == 'cancelled';
    box.querySelector('.order-cancel').classList.toggle('is-gone', status != 'new' && status != 'cooking');
    if ((status == 'done' || status == 'cancelled') && timer) {
        clearInterval(timer);
    }
}

function checkStatus() {
    if (document.hidden) {
        return;
    }
    api('orders/' + orderId + '/status/').then(function (answer) {
        var box = document.querySelector('[data-order]');
        if (answer.status == 200 && box.dataset.status != answer.data.status) {
            showStatus(answer.data.status, answer.data.status_display, true);
            showToast('Заказ #' + orderId + ': ' + answer.data.status_display.toLowerCase(), answer.data.status == 'cancelled' ? 'warning' : 'success');
        }
    }).catch(function () {});
}

if (!needLogin()) {
    api('orders/' + orderId + '/').then(function (answer) {
        if (answer.status != 200) {
            document.getElementById('order').innerHTML = '<div class="empty"><h2>Заказ не найден</h2><p>Возможно, это не ваш заказ.</p><a href="orders.html" class="btn">К моим заказам</a></div>';
            showReveal();
            return;
        }
        drawOrder(answer.data);
        if (answer.data.status != 'done' && answer.data.status != 'cancelled') {
            timer = setInterval(checkStatus, 3000);
        }
    }).catch(showError);
}
