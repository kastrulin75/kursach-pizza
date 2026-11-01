from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from .models import Category, Pizza, Order


class PizzeriaSiteTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Классические', slug='classic')
        self.other_category = Category.objects.create(name='Острые', slug='spicy')
        self.pizza = Pizza.objects.create(category=self.category, name='Маргарита', price='450.00')
        self.spicy = Pizza.objects.create(category=self.other_category, name='Диабло', price='590.00')
        self.user = User.objects.create_user('ivan', password='test-pass-123')

    def test_menu_shows_pizzas_and_filters_by_category(self):
        response = self.client.get(reverse('menu'))
        self.assertContains(response, 'Маргарита')
        self.assertContains(response, 'Диабло')

        response = self.client.get(reverse('menu'), {'category': 'spicy'})
        self.assertNotContains(response, 'Маргарита')
        self.assertContains(response, 'Диабло')

    def test_cart_requires_login(self):
        response = self.client.get(reverse('cart'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('cart')}")

    def test_add_update_and_remove_cart_items(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart_add', args=[self.pizza.id]))
        self.client.post(reverse('cart_add', args=[self.pizza.id]))
        item = self.user.cart.items.get()
        self.assertEqual(item.quantity, 2)

        self.client.post(reverse('cart_update', args=[item.id]), {'quantity': 5})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

        response = self.client.get(reverse('cart'))
        self.assertContains(response, '2250 ₽')

        self.client.post(reverse('cart_remove', args=[item.id]))
        self.assertFalse(self.user.cart.items.exists())

    def test_cart_buttons_without_reload(self):
        self.client.force_login(self.user)
        ajax = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        data = self.client.post(reverse('cart_add', args=[self.pizza.id]), **ajax).json()
        self.assertEqual(data['quantity'], 1)
        self.assertEqual(data['count'], 1)

        data = self.client.post(reverse('cart_update', args=[data['item_id']]), {'quantity': 3}, **ajax).json()
        self.assertEqual(data['quantity'], 3)
        self.assertEqual(data['total'], 1350)

        menu = self.client.get(reverse('menu'))
        self.assertContains(menu, 'buy is-added')

        data = self.client.post(reverse('cart_update', args=[data['item_id']]), {'quantity': 0}, **ajax).json()
        self.assertEqual(data['quantity'], 0)
        self.assertEqual(data['count'], 0)
        self.assertFalse(self.user.cart.items.exists())

    def test_checkout_creates_order_and_clears_cart(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart_add', args=[self.pizza.id]))
        self.client.post(reverse('cart_add', args=[self.spicy.id]))

        response = self.client.post(reverse('checkout'), {
            'address': 'ул. Ленина, 1', 'phone': '+7 900 123-45-67'
        })
        order = Order.objects.get()
        self.assertRedirects(response, reverse('order_detail', args=[order.pk]))
        self.assertEqual(order.total_price, 1040)
        self.assertEqual(order.items.count(), 2)
        self.assertFalse(self.user.cart.items.exists())

    def test_checkout_rejects_bad_phone(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart_add', args=[self.pizza.id]))
        response = self.client.post(reverse('checkout'), {'address': 'ул. Ленина, 1', 'phone': '123'})
        self.assertContains(response, 'Введите корректный номер телефона')
        self.assertFalse(Order.objects.exists())

    def test_order_status_page_and_cancel(self):
        order = Order.objects.create(user=self.user, address='ул. Ленина, 1', phone='+79001234567', status='cooking')
        self.client.force_login(self.user)

        response = self.client.get(reverse('order_detail', args=[order.pk]))
        self.assertContains(response, 'Готовится')
        self.assertContains(response, 'is-current')

        api_response = self.client.get(f'/api/orders/{order.pk}/status/')
        self.assertEqual(api_response.json()['status'], 'cooking')

        self.client.post(reverse('order_cancel', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_order_status_api_for_live_updates(self):
        order = Order.objects.create(user=self.user, address='ул. Ленина, 1', phone='+79001234567')
        self.client.force_login(self.user)

        data = self.client.get('/api/orders/').json()
        self.assertEqual(data[0]['status'], 'new')
        self.assertEqual(data[0]['status_display'], 'Новый')

        order.status = 'delivering'
        order.save()
        data = self.client.get(f'/api/orders/{order.pk}/status/').json()
        self.assertEqual(data['status_display'], 'В доставке')

        page = self.client.get(reverse('order_detail', args=[order.pk]))
        self.assertContains(page, 'data-step-status="delivering"')
        self.assertContains(page, 'order-cancel is-gone')

    def test_cancelled_order_has_no_active_steps(self):
        order = Order.objects.create(user=self.user, address='ул. Ленина, 1', phone='+79001234567', status='cancelled')
        self.client.force_login(self.user)
        page = self.client.get(reverse('order_detail', args=[order.pk]))
        self.assertNotContains(page, 'is-current')
        self.assertNotContains(page, 'is-done')

    def test_user_cannot_see_foreign_order(self):
        stranger = User.objects.create_user('petr', password='test-pass-123')
        order = Order.objects.create(user=stranger, address='ул. Мира, 2', phone='+79001234567')
        self.client.force_login(self.user)
        response = self.client.get(reverse('order_detail', args=[order.pk]))
        self.assertEqual(response.status_code, 404)

    def test_login_and_logout(self):
        response = self.client.post(reverse('login'), {'username': 'ivan', 'password': 'wrong'})
        self.assertContains(response, 'Неверное имя пользователя или пароль')

        response = self.client.post(reverse('login'), {'username': 'ivan', 'password': 'test-pass-123'})
        self.assertRedirects(response, reverse('menu'))
        self.assertContains(self.client.get(reverse('menu')), 'ivan')

        self.client.post(reverse('logout'))
        self.assertNotContains(self.client.get(reverse('menu')), 'ivan')

    def test_old_csrf_token_redirects_back(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse('menu'))
        response = client.post(
            reverse('cart_add', args=[self.pizza.id]),
            {'csrfmiddlewaretoken': 'x' * 64},
            HTTP_REFERER='http://testserver/',
        )
        self.assertRedirects(response, 'http://testserver/', fetch_redirect_response=False)
        self.assertContains(client.get(reverse('menu')), 'Страница устарела')

    def test_admin_cannot_use_site(self):
        User.objects.create_superuser('boss', password='test-pass-123')

        response = self.client.post(reverse('login'), {'username': 'boss', 'password': 'test-pass-123'})
        self.assertContains(response, 'Этот аккаунт нельзя использовать на сайте')
        self.assertNotIn('_auth_user_id', self.client.session)

        self.client.login(username='boss', password='test-pass-123')
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        menu = self.client.get(reverse('menu'))
        self.assertNotContains(menu, 'boss')
        self.assertContains(menu, 'Регистрация')
        self.assertRedirects(self.client.get(reverse('cart')), f"{reverse('login')}?next={reverse('cart')}")

    def test_login_returns_to_next_page(self):
        response = self.client.post(reverse('login'), {
            'username': 'ivan', 'password': 'test-pass-123', 'next': reverse('orders')
        })
        self.assertRedirects(response, reverse('orders'))

    def test_register_logs_user_in(self):
        response = self.client.post(reverse('register'), {
            'username': 'maria', 'password1': 'Sl0zhnyi-parol', 'password2': 'Sl0zhnyi-parol'
        })
        self.assertRedirects(response, reverse('menu'))
        self.assertTrue(User.objects.filter(username='maria').exists())
        self.assertContains(self.client.get(reverse('menu')), 'maria')
