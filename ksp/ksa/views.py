import re

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.response import Response

from .models import Category, Pizza, Cart, CartItem, Order, OrderItem
from .serializers import (
    CategorySerializer, PizzaSerializer, CartSerializer,
    CartItemSerializer, OrderSerializer, OrderStatusSerializer, RegisterSerializer
)


class IsCustomer(BasePermission):
    message = 'Войдите в аккаунт покупателя'

    def has_permission(self, request, view):
        return request.user.is_authenticated and not request.user.is_staff


def error_list(errors):
    result = []
    for value in errors.values():
        for text in value:
            result.append(str(text))
    return result


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class PizzaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pizza.objects.filter(is_available=True).select_related('category').order_by('category__id', 'id')
    serializer_class = PizzaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset


def cart_info(cart, item_id, quantity, subtotal=0):
    return {
        'item_id': item_id,
        'quantity': quantity,
        'subtotal': float(subtotal),
        'total': float(cart.total_price),
        'count': cart.items_count,
    }


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsCustomer]

    def _get_cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def list(self, request):
        serializer = CartSerializer(self._get_cart(), context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        cart = self._get_cart()
        serializer = CartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': error_list(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        pizza = serializer.validated_data['pizza']
        quantity = serializer.validated_data.get('quantity', 1)

        item, created = CartItem.objects.get_or_create(cart=cart, pizza=pizza)
        if not created:
            item.quantity = min(item.quantity + quantity, 99)
        else:
            item.quantity = min(quantity, 99)
        item.save()
        return Response(cart_info(cart, item.id, item.quantity, item.subtotal), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        cart = self._get_cart()
        try:
            item = cart.items.get(id=request.data.get('item_id'))
            quantity = int(request.data.get('quantity', 1))
        except (CartItem.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Товар не найден'}, status=status.HTTP_404_NOT_FOUND)
        if quantity > 0:
            item.quantity = min(quantity, 99)
            item.save()
            return Response(cart_info(cart, item.id, item.quantity, item.subtotal))
        item_id = item.id
        item.delete()
        return Response(cart_info(cart, item_id, 0))

    @action(detail=False, methods=['post'])
    def remove(self, request):
        cart = self._get_cart()
        item_id = request.data.get('item_id')
        try:
            item = cart.items.get(id=item_id)
        except (CartItem.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Товар не найден'}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(cart_info(cart, int(item_id), 0))

    @action(detail=False, methods=['post'])
    def clear(self, request):
        self._get_cart().items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomer]
    http_method_names = ['get', 'post']

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return Response({'errors': ['Корзина пуста']}, status=status.HTTP_400_BAD_REQUEST)

        address = str(request.data.get('address', '')).strip()
        phone = str(request.data.get('phone', '')).strip()
        errors = []
        if not address:
            errors.append('Укажите адрес доставки')
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 15:
            errors.append('Введите корректный номер телефона')
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({'error': 'Этот заказ уже нельзя отменить'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        order.save()
        return Response(OrderStatusSerializer(order).data)


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


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': error_list(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.save()
    token = Token.objects.create(user=user)
    return Response({'token': token.key, 'username': user.username}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'error': 'Неверное имя пользователя или пароль'}, status=status.HTTP_400_BAD_REQUEST)
    if user.is_staff:
        return Response({'error': 'Этот аккаунт нельзя использовать на сайте'}, status=status.HTTP_403_FORBIDDEN)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsCustomer])
def me(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    return Response({
        'username': request.user.username,
        'cart_count': cart.items_count,
        'last_address': last_order.address if last_order else '',
        'last_phone': last_order.phone if last_order else '',
    })
