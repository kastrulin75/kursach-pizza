if (isLoggedIn()) {
    location.href = 'index.html';
}

passwordEyes();

document.getElementById('register-form').addEventListener('submit', function (event) {
    event.preventDefault();
    var data = {
        username: document.getElementById('username').value.trim(),
        password1: document.getElementById('password1').value,
        password2: document.getElementById('password2').value
    };
    api('auth/register/', 'POST', data).then(function (answer) {
        if (answer.status == 201) {
            saveLogin(answer.data);
            toastNextPage('Аккаунт создан, приятного аппетита!');
            location.href = 'index.html';
        } else {
            showMessages(document.getElementById('errors'), answer.data.errors || ['Не удалось создать аккаунт']);
        }
    }).catch(showError);
});

showReveal();
