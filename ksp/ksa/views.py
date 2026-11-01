import re

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Category, Pizza, Cart, CartItem, Order, OrderItem
from .serializers import (
    CategorySerializer, PizzaSerializer, CartSerializer,
    CartItemSerializer, OrderSerializer, OrderStatusSerializer
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class PizzaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pizza.objects.filter(is_available=True)
    serializer_class = PizzaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def list(self, request):
        serializer = CartSerializer(self._get_cart())
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        cart = self._get_cart()
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pizza = serializer.validated_data['pizza']
        quantity = serializer.validated_data.get('quantity', 1)

        item, created = CartItem.objects.get_or_create(cart=cart, pizza=pizza)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()
        return Response(CartItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def remove(self, request):
        cart = self._get_cart()
        item_id = request.data.get('item_id')
        try:
            item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({'error': 'Товар не найден'}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        self._get_cart().items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

        address = request.data.get('address')
        phone = request.data.get('phone')
        if not address or not phone:
            return Response({'error': 'Укажите адрес и телефон'}, status=status.HTTP_400_BAD_REQUEST)

        order = make_order(cart, address, phone)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        order = self.get_object()
        return Response(OrderStatusSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status not in ('new', 'cooking'):
            return Response({'error': 'Нельзя отменить заказ'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        order.save()
        return Response(OrderStatusSerializer(order).data)


def is_customer(user):
    return user.is_authenticated and not user.is_staff


customer_required = user_passes_test(is_customer)


@transaction.atomic
def make_order(cart, address, phone):
    order = Order.objects.create(user=cart.user, address=address, phone=phone)

    total = 0
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            pizza=item.pizza,
            pizza_name=item.pizza.name,
            price=item.pizza.price,
            quantity=item.quantity
        )
        total += item.subtotal

    order.total_price = total
    order.save()
    cart.items.all().delete()
    return order


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def cart_json(cart, item_id, quantity, subtotal=0):
    return JsonResponse({
        'item_id': item_id,
        'quantity': quantity,
        'subtotal': float(subtotal),
        'total': float(cart.total_price),
        'count': cart.items_count,
    })


def menu(request):
    pizzas = Pizza.objects.filter(is_available=True).select_related('category').order_by('category__id', 'id')
    category = request.GET.get('category')
    if category:
        pizzas = pizzas.filter(category__slug=category)

    pizzas = list(pizzas)
    if is_customer(request.user):
        in_cart = {}
        for item in CartItem.objects.filter(cart__user=request.user):
            in_cart[item.pizza_id] = item
        for pizza in pizzas:
            if pizza.id in in_cart:
                pizza.cart_item_id = in_cart[pizza.id].id
                pizza.cart_qty = in_cart[pizza.id].quantity

    return render(request, 'ksa/menu.html', {
        'categories': Category.objects.all(),
        'pizzas': pizzas,
        'current_category': category,
    })


@customer_required
def cart_page(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'ksa/cart.html', {'cart': cart, 'items': cart.items.all()})


@customer_required
def cart_add(request, pizza_id):
    if request.method == 'POST':
        pizza = get_object_or_404(Pizza, id=pizza_id)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, pizza=pizza)
        if not created:
            item.quantity += 1
            item.save()
        if is_ajax(request):
            return cart_json(cart, item.id, item.quantity, item.subtotal)
        messages.success(request, f'Добавлено в корзину: {pizza.name}')
    return redirect('menu')


@customer_required
def cart_update(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            item.quantity = min(quantity, 99)
            item.save()
        else:
            item.delete()
        if is_ajax(request):
            if quantity > 0:
                return cart_json(item.cart, item.id, item.quantity, item.subtotal)
            return cart_json(item.cart, item_id, 0)
    return redirect('cart')


@customer_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        item.delete()
        if is_ajax(request):
            return cart_json(item.cart, item_id, 0)
    return redirect('cart')


@customer_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if not cart.items.exists():
        messages.warning(request, 'Корзина пуста')
        return redirect('menu')

    address = ''
    phone = ''
    errors = []

    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        if not address:
            errors.append('Укажите адрес доставки')
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 15:
            errors.append('Введите корректный номер телефона')

        if not errors:
            order = make_order(cart, address, phone)
            messages.success(request, f'Заказ #{order.id} оформлен!')
            return redirect('order_detail', pk=order.id)
    else:
        last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        if last_order:
            address = last_order.address
            phone = last_order.phone

    return render(request, 'ksa/checkout.html', {
        'cart': cart,
        'items': cart.items.all(),
        'address': address,
        'phone': phone,
        'errors': errors,
    })


@customer_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'ksa/order_list.html', {'orders': orders})


@customer_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)

    steps = []
    passed = order.status != 'cancelled'
    for code, name in Order.STATUS_CHOICES:
        if code == 'cancelled':
            continue
        if code == order.status:
            steps.append({'code': code, 'name': name, 'state': 'current'})
            passed = False
        elif passed:
            steps.append({'code': code, 'name': name, 'state': 'done'})
        else:
            steps.append({'code': code, 'name': name, 'state': 'todo'})

    return render(request, 'ksa/order_detail.html', {
        'order': order,
        'steps': steps,
        'can_cancel': order.status in ('new', 'cooking'),
    })


@customer_required
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == 'POST':
        if order.status in ('new', 'cooking'):
            order.status = 'cancelled'
            order.save()
            messages.info(request, f'Заказ #{order.id} отменён')
        else:
            messages.error(request, 'Этот заказ уже нельзя отменить')
    return redirect('order_detail', pk=order.id)


def login_page(request):
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    error = ''

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                error = 'Этот аккаунт нельзя использовать на сайте'
            else:
                login(request, user)
                if next_url.startswith('/') and not next_url.startswith('//'):
                    return redirect(next_url)
                return redirect('menu')
        else:
            error = 'Неверное имя пользователя или пароль'
    else:
        form = AuthenticationForm(request)

    return render(request, 'ksa/login.html', {'form': form, 'error': error, 'next': next_url})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('menu')
    else:
        form = UserCreationForm()
    return render(request, 'ksa/register.html', {'form': form})


def csrf_failure(request, reason=''):
    messages.error(request, 'Страница устарела, попробуйте ещё раз')
    return redirect(request.META.get('HTTP_REFERER') or 'menu')
