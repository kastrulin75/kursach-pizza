# kursach-pizza

Веб-приложение пиццерии: меню, корзина и статус заказа.

Автор: Матвеев Ефим

## Запуск

```
pip install -r requirements.txt
cd ksp
python manage.py migrate
python manage.py loaddata menu
python manage.py createsuperuser
python manage.py runserver
```

Сайт: http://127.0.0.1:8000/

Админка: http://127.0.0.1:8000/admin/
