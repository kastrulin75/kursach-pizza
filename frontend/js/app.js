var API = 'http://127.0.0.1:8000/api/';

function getToken() {
    return localStorage.getItem('token') || '';
}

function saveLogin(data) {
    localStorage.setItem('token', data.token);
    localStorage.setItem('username', data.username);
}

function clearLogin() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
}

function isLoggedIn() {
    return getToken() != '';
}

function api(url, method, data) {
    var options = {method: method || 'GET', headers: {}};
    if (getToken()) {
        options.headers['Authorization'] = 'Token ' + getToken();
    }
    if (data !== undefined) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(data);
    }
    return fetch(API + url, options).then(function (response) {
        if (response.status == 401) {
            clearLogin();
        }
        if (response.status == 204) {
            return {status: 204, data: {}};
        }
        return response.json().then(function (json) {
            return {status: response.status, data: json};
        });
    });
}

function needLogin() {
    if (!isLoggedIn()) {
        location.href = 'login.html?next=' + encodeURIComponent(location.pathname.split('/').pop() + location.search);
        return true;
    }
    return false;
}

function getParam(name) {
    return new URLSearchParams(location.search).get(name) || '';
}

function safe(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatPrice(value) {
    value = Number(value);
    var text = value % 1 === 0 ? String(value) : value.toFixed(2).replace('.', ',');
    return text + ' ₽';
}

function formatDate(text) {
    var date = new Date(text);
    return date.toLocaleString('ru-RU', {day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'});
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
    showToast('Сервер не отвечает, проверьте, что бэкенд запущен', 'error');
}

toasts.addEventListener('click', function (event) {
    if (event.target.classList.contains('toast')) {
        hideToast(event.target);
    }
});

var saved = sessionStorage.getItem('toast');
if (saved) {
    sessionStorage.removeItem('toast');
    showToast(saved);
}

function toastNextPage(text) {
    sessionStorage.setItem('toast', text);
}


function updateCount(count) {
    var counter = document.querySelector('[data-cart-count]');
    if (counter) {
        counter.textContent = count > 0 ? count : '';
        pop(counter);
    }
}

function drawNav() {
    var nav = document.querySelector('.nav');
    var html = '<a href="index.html" class="nav__link">Меню</a>';
    if (isLoggedIn()) {
        html += '<a href="orders.html" class="nav__link">Мои заказы</a>';
        html += '<a href="cart.html" class="nav__cart">Корзина <span class="nav__count" data-cart-count></span></a>';
        html += '<button type="button" class="link-button" id="logout">' + safe(localStorage.getItem('username')) + ' · Выйти</button>';
    } else {
        html += '<a href="login.html" class="nav__link">Войти</a>';
        html += '<a href="register.html" class="btn btn--small">Регистрация</a>';
    }
    nav.innerHTML = html;

    if (isLoggedIn()) {
        document.getElementById('logout').addEventListener('click', function () {
            api('auth/logout/', 'POST').catch(function () {}).finally(function () {
                clearLogin();
                toastNextPage('Вы вышли из аккаунта');
                location.href = 'index.html';
            });
        });
        api('auth/me/').then(function (answer) {
            if (answer.status == 200) {
                updateCount(answer.data.cart_count);
            } else {
                clearLogin();
                drawNav();
            }
        }).catch(function () {});
    }
}

drawNav();


function showReveal() {
    var items = document.querySelectorAll('.hero, .page-title, .menu-section__title, .card, .panel, .order-card, .empty');
    if (!('IntersectionObserver' in window)) {
        items.forEach(function (item) {
            item.classList.add('is-visible');
        });
        return;
    }
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

    items.forEach(function (item) {
        if (item.classList.contains('is-visible')) {
            return;
        }
        var index = Array.prototype.indexOf.call(item.parentNode.children, item);
        item.style.transitionDelay = (index % 4) * 80 + 'ms';
        observer.observe(item);
    });
}


function passwordEyes() {
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
}

function showMessages(box, errors) {
    var html = '';
    errors.forEach(function (error) {
        html += '<div class="message message--error">' + safe(error) + '</div>';
    });
    box.innerHTML = html;
}
