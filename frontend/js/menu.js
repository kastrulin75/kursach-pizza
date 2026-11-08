var current = getParam('category');
var inCart = {};

function pizzaCard(pizza) {
    var html = '<article class="card"><div class="card__image">';
    if (pizza.image) {
        html += '<img src="' + pizza.image + '" alt="' + safe(pizza.name) + '" loading="lazy">';
    } else {
        html += '<span class="card__noimage">Нет фото</span>';
    }
    html += '</div><div class="card__body">';
    html += '<h2 class="card__title">' + safe(pizza.name) + '</h2>';
    if (pizza.description) {
        html += '<p class="card__text">' + safe(pizza.description) + '</p>';
    }
    html += '<div class="card__footer"><span class="price">' + formatPrice(pizza.price) + '</span>';
    if (isLoggedIn()) {
        var item = inCart[pizza.id];
        html += '<div class="buy' + (item ? ' is-added' : '') + '" data-item="' + (item ? item.id : '') + '" data-pizza="' + pizza.id + '" data-name="' + safe(pizza.name) + '">';
        html += '<div class="buy__add"><button type="button" class="btn">В корзину</button></div>';
        html += '<div class="qty buy__qty">';
        html += '<button type="button" class="qty__btn" data-step="-1" aria-label="Уменьшить">−</button>';
        html += '<span class="qty__value">' + (item ? item.quantity : 0) + '</span>';
        html += '<button type="button" class="qty__btn" data-step="1" aria-label="Увеличить">+</button>';
        html += '</div></div>';
    } else {
        html += '<a href="login.html" class="btn btn--ghost">Войти, чтобы заказать</a>';
    }
    html += '</div></div></article>';
    return html;
}

function drawMenu(categories, pizzas) {
    var filters = '<a href="index.html" class="chip' + (current == '' ? ' is-active' : '') + '" data-filter="">Все</a>';
    categories.forEach(function (category) {
        filters += '<a href="?category=' + category.slug + '" class="chip' + (current == category.slug ? ' is-active' : '') + '" data-filter="' + category.slug + '">' + safe(category.name) + '</a>';
    });
    document.getElementById('filters').innerHTML = filters;

    if (pizzas.length == 0) {
        document.getElementById('menu').innerHTML = '<div class="empty"><h2>Меню пока пустое</h2><p>Скоро здесь появятся наши пиццы.</p></div>';
        showReveal();
        return;
    }

    var html = '';
    categories.forEach(function (category) {
        var list = pizzas.filter(function (pizza) {
            return pizza.category.id == category.id;
        });
        if (list.length == 0) {
            return;
        }
        html += '<section class="menu-section" data-category="' + category.slug + '"';
        if (current != '' && current != category.slug) {
            html += ' hidden';
        }
        html += '><h1 class="menu-section__title">' + safe(category.name) + '</h1><div class="grid">';
        list.forEach(function (pizza) {
            html += pizzaCard(pizza);
        });
        html += '</div></section>';
    });
    document.getElementById('menu').innerHTML = html;
    showReveal();
    setupFilters();
}

function setupFilters() {
    var sections = document.querySelectorAll('.menu-section');
    document.querySelectorAll('[data-filter]').forEach(function (chip) {
        chip.addEventListener('click', function (event) {
            event.preventDefault();
            var slug = chip.dataset.filter;
            current = slug;
            document.querySelectorAll('[data-filter]').forEach(function (other) {
                other.classList.toggle('is-active', other == chip);
            });
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
            history.replaceState(null, '', slug ? '?category=' + slug : location.pathname);
        });
    });
}

function loadMenu() {
    var requests = [api('categories/'), api('pizzas/')];
    if (isLoggedIn()) {
        requests.push(api('cart/'));
    }
    Promise.all(requests).then(function (answers) {
        if (answers[2] && answers[2].status == 200) {
            answers[2].data.items.forEach(function (item) {
                inCart[item.pizza.id] = item;
            });
        }
        drawMenu(answers[0].data, answers[1].data);
    }).catch(function () {
        document.getElementById('menu').innerHTML = '<div class="empty"><h2>Сервер не отвечает</h2><p>Проверьте, что бэкенд запущен.</p></div>';
    });
}

document.addEventListener('click', function (event) {
    var add = event.target.closest('.buy__add button');
    if (add) {
        var buy = add.closest('.buy');
        api('cart/add/', 'POST', {pizza_id: Number(buy.dataset.pizza), quantity: 1}).then(function (answer) {
            if (answer.status != 200) {
                showToast('Не удалось добавить товар', 'error');
                return;
            }
            buy.dataset.item = answer.data.item_id;
            buy.querySelector('.qty__value').textContent = answer.data.quantity;
            buy.classList.add('is-added');
            updateCount(answer.data.count);
            showToast('Добавлено в корзину: ' + buy.dataset.name);
        }).catch(showError);
        return;
    }

    var button = event.target.closest('[data-step]');
    if (!button) {
        return;
    }
    var box = button.closest('.buy');
    if (box.classList.contains('is-busy')) {
        return;
    }
    var quantity = parseInt(box.querySelector('.qty__value').textContent) + parseInt(button.dataset.step);
    if (quantity > 99) {
        return;
    }
    box.classList.add('is-busy');
    api('cart/update_item/', 'POST', {item_id: Number(box.dataset.item), quantity: quantity}).then(function (answer) {
        updateCount(answer.data.count);
        if (answer.data.quantity > 0) {
            var value = box.querySelector('.qty__value');
            value.textContent = answer.data.quantity;
            pop(value);
        } else {
            box.classList.remove('is-added');
        }
    }).catch(showError).finally(function () {
        box.classList.remove('is-busy');
    });
});

loadMenu();
