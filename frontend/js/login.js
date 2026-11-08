function goNext() {
    var next = getParam('next');
    if (next == '' || next.indexOf('/') != -1 || next.indexOf(':') != -1) {
        next = 'index.html';
    }
    location.href = next;
}

if (isLoggedIn()) {
    goNext();
}

passwordEyes();

document.getElementById('login-form').addEventListener('submit', function (event) {
    event.preventDefault();
    var data = {
        username: document.getElementById('username').value.trim(),
        password: document.getElementById('password').value
    };
    api('auth/login/', 'POST', data).then(function (answer) {
        if (answer.status == 200) {
            saveLogin(answer.data);
            toastNextPage('Добро пожаловать, ' + answer.data.username + '!');
            goNext();
        } else {
            showMessages(document.getElementById('errors'), [answer.data.error]);
        }
    }).catch(showError);
});

showReveal();
