from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .models import Category, Pizza, Order


class PizzeriaApiTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Классические', slug='classic')
        self.other_category = Category.objects.create(name='Острые', slug='spicy')
        self.pizza = Pizza.objects.create(category=self.category, name='Маргарита', price='450.00')
        self.spicy = Pizza.objects.create(category=self.other_category, name='Диабло', price='590.00')
        self.user = User.objects.create_user('ivan', password='test-pass-123')
        self.token = Token.objects.create(user=self.user)

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def add(self, pizza, quantity=1):
        return self.client.post('/api/cart/add/', {'pizza_id': pizza.id, 'quantity': quantity}, format='json')

    def test_api_answers_json(self):
        for url in ['/api/categories/', '/api/pizzas/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/json')

    def test_menu_filters_by_category(self):
        names = [p['name'] for p in self.client.get('/api/pizzas/').json()]
        self.assertEqual(names, ['Маргарита', 'Диабло'])
        names = [p['name'] for p in self.client.get('/api/pizzas/?category=spicy').json()]
        self.assertEqual(names, ['Диабло'])

    def test_hidden_pizza_not_in_menu(self):
        self.spicy.is_available = False
        self.spicy.save()
        names = [p['name'] for p in self.client.get('/api/pizzas/').json()]
        self.assertNotIn('Диабло', names)

    def test_cart_requires_login(self):
        self.assertEqual(self.client.get('/api/cart/').status_code, 401)
        self.assertEqual(self.client.get('/api/orders/').status_code, 401)

    def test_register_gives_token(self):
        response = self.client.post('/api/auth/register/', {'username': 'maria', 'password1': 'Sl0zhnyi-parol', 'password2': 'Sl0zhnyi-parol'}, format='json')
        self.assertEqual(response.status_code, 201)
        token = response.json()['token']
        self.assertTrue(User.objects.filter(username='maria').exists())
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        self.assertEqual(self.client.get('/api/auth/me/').json()['username'], 'maria')

    def test_register_errors(self):
        response = self.client.post('/api/auth/register/', {'username': 'ivan', 'password1': '123', 'password2': '321'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Пользователь с таким именем уже существует', response.json()['errors'])

    def test_weak_password_rejected(self):
        response = self.client.post('/api/auth/register/', {'username': 'olga', 'password1': '12345', 'password2': '12345'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='olga').exists())

    def test_login_and_logout(self):
        response = self.client.post('/api/auth/login/', {'username': 'ivan', 'password': 'wrong'}, format='json')
        self.assertEqual(response.json()['error'], 'Неверное имя пользователя или пароль')

        response = self.client.post('/api/auth/login/', {'username': 'ivan', 'password': 'test-pass-123'}, format='json')
        self.assertEqual(response.json()['token'], self.token.key)

        self.auth()
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)

    def test_admin_cannot_use_site(self):
        boss = User.objects.create_superuser('boss', password='test-pass-123')
        response = self.client.post('/api/auth/login/', {'username': 'boss', 'password': 'test-pass-123'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Этот аккаунт нельзя использовать на сайте')
        boss_token = Token.objects.create(user=boss)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + boss_token.key)
        self.assertEqual(self.client.get('/api/cart/').status_code, 403)

    def test_add_update_and_remove_cart_items(self):
        self.auth()
        self.add(self.pizza)
        data = self.add(self.pizza).json()
        self.assertEqual(data['quantity'], 2)
        self.assertEqual(data['count'], 2)

        data = self.client.post('/api/cart/update_item/', {'item_id': data['item_id'], 'quantity': 5}, format='json').json()
        self.assertEqual(data['quantity'], 5)
        self.assertEqual(data['total'], 2250)

        cart = self.client.get('/api/cart/').json()
        self.assertEqual(cart['items_count'], 5)

        data = self.client.post('/api/cart/remove/', {'item_id': data['item_id']}, format='json').json()
        self.assertEqual(data['count'], 0)
        self.assertFalse(self.user.cart.items.exists())

    def test_quantity_zero_removes_item(self):
        self.auth()
        data = self.add(self.pizza).json()
        data = self.client.post('/api/cart/update_item/', {'item_id': data['item_id'], 'quantity': 0}, format='json').json()
        self.assertEqual(data['quantity'], 0)
        self.assertFalse(self.user.cart.items.exists())

    def test_checkout_creates_order_and_clears_cart(self):
        self.auth()
        self.add(self.pizza)
        self.add(self.spicy)
        response = self.client.post('/api/orders/', {'address': 'ул. Ленина, 1', 'phone': '+7 900 123-45-67'}, format='json')
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.total_price, 1040)
        self.assertEqual(order.items.count(), 2)
        self.assertFalse(self.user.cart.items.exists())

    def test_checkout_rejects_bad_data(self):
        self.auth()
        self.add(self.pizza)
        response = self.client.post('/api/orders/', {'address': '', 'phone': '123'}, format='json')
        self.assertEqual(response.json()['errors'], ['Укажите адрес доставки', 'Введите корректный номер телефона'])
        self.assertFalse(Order.objects.exists())

    def test_empty_cart_cannot_be_ordered(self):
        self.auth()
        response = self.client.post('/api/orders/', {'address': 'ул. Ленина, 1', 'phone': '+79001234567'}, format='json')
        self.assertEqual(response.json()['errors'], ['Корзина пуста'])

    def test_order_status_and_cancel(self):
        order = Order.objects.create(user=self.user, address='ул. Ленина, 1', phone='+79001234567', status='cooking')
        self.auth()
        self.assertEqual(self.client.get('/api/orders/' + str(order.pk) + '/status/').json()['status_display'], 'Готовится')
        self.client.post('/api/orders/' + str(order.pk) + '/cancel/')
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_delivering_order_cannot_be_cancelled(self):
        order = Order.objects.create(user=self.user, address='ул. Ленина, 1', phone='+79001234567', status='delivering')
        self.auth()
        response = self.client.post('/api/orders/' + str(order.pk) + '/cancel/')
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivering')

    def test_user_cannot_see_foreign_order(self):
        stranger = User.objects.create_user('petr', password='test-pass-123')
        order = Order.objects.create(user=stranger, address='ул. Мира, 2', phone='+79001234567')
        self.auth()
        self.assertEqual(self.client.get('/api/orders/' + str(order.pk) + '/').status_code, 404)
        self.assertEqual(self.client.get('/api/orders/').json(), [])

    def test_me_returns_last_address(self):
        Order.objects.create(user=self.user, address='ул. Ленина, 1', phone='+79001234567')
        self.auth()
        data = self.client.get('/api/auth/me/').json()
        self.assertEqual(data['last_address'], 'ул. Ленина, 1')

    def test_admin_panel_works(self):
        User.objects.create_superuser('boss', password='test-pass-123')
        client = APIClient()
        client.login(username='boss', password='test-pass-123')
        self.assertEqual(client.get('/admin/').status_code, 200)

    def test_no_html_pages(self):
        self.assertEqual(self.client.get('/').status_code, 404)
        self.assertEqual(self.client.get('/cart/').status_code, 404)
