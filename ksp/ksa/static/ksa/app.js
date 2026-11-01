function getToken() {
    var input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
}

function formatPrice(value) {
    var text = value % 1 === 0 ? String(value) : value.toFixed(2).replace('.', ',');
    return text + ' ₽';
}

function sendPost(url, data) {
    var body = new FormData();
    for (var key in data) {
        body.append(key, data[key]);
    }
    return fetch(url, {
        method: 'POST',
        headers: {'X-CSRFToken': getToken(), 'X-Requested-With': 'XMLHttpRequest'},
        body: body
    }).then(function (response) {
        if (!response.ok) {
            throw new Error(response.status);
        }
        return response.json();
    });
}

function pop(element) {
    element.classList.remove('pop');
    void element.offsetWidth;
    element.classList.add('pop');
}


var toasts = document.querySelector('.toasts');

function hideToast(toast) {
    if (toast.classList.contains('is-leaving')) {
        return;
    }
    toast.classList.add('is-leaving');
    setTimeout(function () {
        toast.remove();
    }, 300);
}

function showToast(text, type) {
    var toast = document.createElement('div');
    toast.className = 'toast toast--' + (type || 'success');
    toast.textContent = text;
    toasts.appendChild(toast);

    var all = toasts.querySelectorAll('.toast:not(.is-leaving)');
    if (all.length > 3) {
        hideToast(all[0]);
    }
    setTimeout(function () {
        hideToast(toast);
    }, 2500);
}

function showError() {
    showToast('Что-то пошло не так, обновите страницу', 'error');
}

document.querySelectorAll('.toast').forEach(function (toast) {
    setTimeout(function () {
        hideToast(toast);
    }, 3500);
});

toasts.addEventListener('click', function (event) {
    if (event.target.classList.contains('toast')) {
        hideToast(event.target);
    }
});


function updateCount(count) {
    var counter = document.querySelector('[data-cart-count]');
    if (counter) {
        counter.textContent = count > 0 ? count : '';
        pop(counter);
    }
}

function updateTotal(total) {
    var element = document.querySelector('[data-cart-total]');
    if (element) {
        element.textContent = formatPrice(total);
        pop(element);
    }
}

function setQuantity(box, quantity) {
    var value = box.querySelector('.qty__value');
    value.textContent = quantity;
    pop(value);
}

function removeRow(row) {
    row.style.height = row.offsetHeight + 'px';
    void row.offsetHeight;
    row.classList.add('is-removing');
    setTimeout(function () {
        row.remove();
        if (!document.querySelector('.cart-row')) {
            location.reload();
        }
    }, 400);
}

function applyItem(box, data) {
    updateCount(data.count);
    updateTotal(data.total);

    if (data.quantity > 0) {
        setQuantity(box, data.quantity);
        var subtotal = box.querySelector('[data-subtotal]');
        if (subtotal) {
            subtotal.textContent = formatPrice(data.subtotal);
            pop(subtotal);
        }
    } else if (box.classList.contains('buy')) {
        box.classList.remove('is-added');
    } else {
        removeRow(box);
    }
}

document.querySelectorAll('.buy__add').forEach(function (form) {
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var buy = form.closest('.buy');
        sendPost(form.action, {}).then(function (data) {
            buy.dataset.item = data.item_id;
            buy.querySelector('.qty__value').textContent = data.quantity;
            buy.classList.add('is-added');
            updateCount(data.count);
            showToast('Добавлено в корзину: ' + buy.dataset.name);
        }).catch(showError);
    });
});

document.querySelectorAll('.cart-row__remove').forEach(function (form) {
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var row = form.closest('.cart-row');
        sendPost(form.action, {}).then(function (data) {
            applyItem(row, data);
        }).catch(showError);
    });
});

document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-step]');
    if (!button) {
        return;
    }
    var box = button.closest('[data-item]');
    if (box.classList.contains('is-busy')) {
        return;
    }
    var current = parseInt(box.querySelector('.qty__value').textContent);
    var quantity = current + parseInt(button.dataset.step);
    if (quantity > 99) {
        return;
    }

    box.classList.add('is-busy');
    sendPost('/cart/update/' + box.dataset.item + '/', {quantity: quantity})
        .then(function (data) {
            applyItem(box, data);
        })
        .catch(showError)
        .finally(function () {
            box.classList.remove('is-busy');
        });
});


var sections = document.querySelectorAll('.menu-section');

function filterMenu(slug) {
    sections.forEach(function (section) {
        section.classList.add('is-hidden');
    });
    setTimeout(function () {
        sections.forEach(function (section) {
            section.hidden = slug != '' && section.dataset.category != slug;
        });
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                sections.forEach(function (section) {
                    section.classList.remove('is-hidden');
                });
            });
        });
    }, 200);
}

if (sections.length > 1) {
    document.querySelectorAll('[data-filter]').forEach(function (chip) {
        chip.addEventListener('click', function (event) {
            var slug = chip.dataset.filter;
            if (slug && !document.querySelector('.menu-section[data-category="' + slug + '"]')) {
                return;
            }
            event.preventDefault();
            document.querySelectorAll('[data-filter]').forEach(function (other) {
                other.classList.toggle('is-active', other == chip);
            });
            filterMenu(slug);
            history.replaceState(null, '', slug ? '?category=' + slug : location.pathname);
        });
    });
}


var statusSteps = ['new', 'cooking', 'delivering', 'done'];
var orderBoxes = document.querySelectorAll('[data-order]');

function isFinished(status) {
    return status == 'done' || status == 'cancelled';
}

function showOrderStatus(box, status, name) {
    box.dataset.status = status;

    var badge = box.querySelector('[data-badge]');
    badge.className = 'badge badge--' + status;
    badge.textContent = name;
    pop(badge);

    var timeline = box.querySelector('.timeline');
    if (!timeline) {
        return;
    }

    var current = statusSteps.indexOf(status);
    box.querySelectorAll('[data-step-status]').forEach(function (step) {
        var index = statusSteps.indexOf(step.dataset.stepStatus);
        step.classList.remove('is-done', 'is-current', 'is-todo');
        if (status == 'cancelled' || index > current) {
            step.classList.add('is-todo');
        } else if (index == current) {
            step.classList.add('is-current');
        } else {
            step.classList.add('is-done');
        }
    });

    timeline.hidden = status == 'cancelled';
    box.querySelector('[data-cancelled]').hidden = status != 'cancelled';
    box.querySelector('[data-hint]').hidden = isFinished(status);
    box.querySelector('.order-cancel').classList.toggle('is-gone', status != 'new' && status != 'cooking');
}

function checkOrders() {
    if (document.hidden) {
        return;
    }
    fetch('/api/orders/')
        .then(function (response) {
            return response.json();
        })
        .then(function (orders) {
            orders.forEach(function (order) {
                var box = document.querySelector('[data-order="' + order.id + '"]');
                if (box && box.dataset.status != order.status) {
                    showOrderStatus(box, order.status, order.status_display);
                    showToast('Заказ #' + order.id + ': ' + order.status_display.toLowerCase(),
                        order.status == 'cancelled' ? 'warning' : 'success');
                }
            });

            var waiting = Array.prototype.some.call(orderBoxes, function (box) {
                return !isFinished(box.dataset.status);
            });
            if (!waiting) {
                clearInterval(ordersTimer);
            }
        })
        .catch(function () {});
}

if (orderBoxes.length) {
    var ordersTimer = setInterval(checkOrders, 3000);
}


var revealItems =document.querySelectorAll('.hero, .page-title, .menu-section__title, .card, .panel, .order-card, .empty');

if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) {
                return;
            }
            var item = entry.target;
            item.classList.add('is-visible');
            observer.unobserve(item);
            setTimeout(function () {
                item.style.transitionDelay = '';
            }, 900);
        });
    }, {threshold: 0.1});

    revealItems.forEach(function (item) {
        var index = Array.prototype.indexOf.call(item.parentNode.children, item);
        item.style.transitionDelay = (index % 4) * 80 + 'ms';
        observer.observe(item);
    });
} else {
    revealItems.forEach(function (item) {
        item.classList.add('is-visible');
    });
}


document.querySelectorAll('input[type=password]').forEach(function (input) {
    var wrap = document.createElement('div');
    wrap.className = 'password';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'password__toggle';
    button.title = 'Показать пароль';
    button.innerHTML = '<span class="eye"></span>';
    wrap.appendChild(button);

    button.addEventListener('click', function (event) {
        event.preventDefault();
        if (input.type == 'password') {
            input.type = 'text';
            button.classList.add('is-open');
            button.title = 'Скрыть пароль';
        } else {
            input.type = 'password';
            button.classList.remove('is-open');
            button.title = 'Показать пароль';
        }
        input.focus();
    });
});
