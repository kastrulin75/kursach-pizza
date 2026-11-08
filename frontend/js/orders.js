var timer = null;

function isFinished(status) {
    return status == 'done' || status == 'cancelled';
}

function drawOrders(orders) {
    var place = document.getElementById('orders');
    if (orders.length == 0) {
        place.innerHTML = '<div class="empty"><h2>Заказов пока нет</h2><p>Самое время оформить первый.</p><a href="index.html" class="btn">Перейти в меню</a></div>';
        showReveal();
        return;
    }
    var html = '<div class="order-list">';
    orders.forEach(function (order) {
        html += '<a href="order.html?id=' + order.id + '" class="panel order-card" data-order="' + order.id + '" data-status="' + order.status + '">';
        html += '<div><div class="order-card__number">Заказ #' + order.id + '</div>';
        html += '<div class="muted">' + formatDate(order.created_at) + ' · ' + order.items.length + ' поз.</div></div>';
        html += '<span class="badge badge--' + order.status + '" data-badge>' + order.status_display + '</span>';
        html += '<span class="price">' + formatPrice(order.total_price) + '</span></a>';
    });
    html += '</div>';
    place.innerHTML = html;
    showReveal();
}

function checkOrders() {
    if (document.hidden) {
        return;
    }
    api('orders/').then(function (answer) {
        var waiting = false;
        answer.data.forEach(function (order) {
            var box = document.querySelector('[data-order="' + order.id + '"]');
            if (box && box.dataset.status != order.status) {
                box.dataset.status = order.status;
                var badge = box.querySelector('[data-badge]');
                badge.className = 'badge badge--' + order.status;
                badge.textContent = order.status_display;
                pop(badge);
                showToast('Заказ #' + order.id + ': ' + order.status_display.toLowerCase(), order.status == 'cancelled' ? 'warning' : 'success');
            }
            if (!isFinished(order.status)) {
                waiting = true;
            }
        });
        if (!waiting) {
            clearInterval(timer);
        }
    }).catch(function () {});
}

if (!needLogin()) {
    api('orders/').then(function (answer) {
        if (answer.status != 200) {
            location.href = 'login.html?next=orders.html';
            return;
        }
        drawOrders(answer.data);
        timer = setInterval(checkOrders, 3000);
    }).catch(function () {
        document.getElementById('orders').innerHTML = '<div class="empty"><h2>Сервер не отвечает</h2><p>Проверьте, что бэкенд запущен.</p></div>';
    });
}
