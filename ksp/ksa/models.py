from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Адрес (slug)', unique=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Pizza(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='pizzas', verbose_name='Категория')
    name = models.CharField('Название', max_length=150)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена', max_digits=8, decimal_places=2)
    image = models.ImageField('Фото', upload_to='pizzas/', blank=True, null=True)
    is_available = models.BooleanField('В наличии', default=True)

    class Meta:
        verbose_name = 'Пицца'
        verbose_name_plural = 'Пиццы'

    def __str__(self):
        return self.name


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', verbose_name='Пользователь')
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f"Корзина {self.user.username}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name='Корзина')
    pizza = models.ForeignKey(Pizza, on_delete=models.CASCADE, verbose_name='Пицца')
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        unique_together = ('cart', 'pizza')
        verbose_name = 'Позиция корзины'
        verbose_name_plural = 'Позиции корзины'

    @property
    def subtotal(self):
        return self.pizza.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('cooking', 'Готовится'),
        ('delivering', 'В доставке'),
        ('done', 'Завершён'),
        ('cancelled', 'Отменён'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='Пользователь')
    address = models.CharField('Адрес', max_length=255)
    phone = models.CharField('Телефон', max_length=20)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    total_price = models.DecimalField('Сумма', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f"Заказ #{self.id} - {self.get_status_display()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    pizza = models.ForeignKey(Pizza, on_delete=models.SET_NULL, null=True, verbose_name='Пицца')
    pizza_name = models.CharField('Название пиццы', max_length=150)
    price = models.DecimalField('Цена', max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    @property
    def subtotal(self):
        return self.price * self.quantity
