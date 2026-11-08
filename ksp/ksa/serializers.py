from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Category, Pizza, Cart, CartItem, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class PizzaSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )

    class Meta:
        model = Pizza
        fields = ['id', 'category', 'category_id', 'name', 'description', 'price', 'image', 'is_available']


class CartItemSerializer(serializers.ModelSerializer):
    pizza = PizzaSerializer(read_only=True)
    pizza_id = serializers.PrimaryKeyRelatedField(
        queryset=Pizza.objects.filter(is_available=True), source='pizza', write_only=True
    )
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ['id', 'pizza', 'pizza_id', 'quantity', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()
    items_count = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'items_count']


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['id', 'pizza', 'pizza_name', 'price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'address', 'phone', 'status', 'status_display', 'created_at', 'total_price', 'items']
        read_only_fields = ['status', 'created_at', 'total_price']


class OrderStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'status_display']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, error_messages={'blank': 'Введите имя пользователя', 'required': 'Введите имя пользователя'})
    password1 = serializers.CharField(error_messages={'blank': 'Введите пароль', 'required': 'Введите пароль'})
    password2 = serializers.CharField(error_messages={'blank': 'Повторите пароль', 'required': 'Повторите пароль'})

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Пользователь с таким именем уже существует')
        return value

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Пароли не совпадают'})
        try:
            validate_password(data['password1'], User(username=data['username']))
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password1': list(error.messages)})
        return data

    def create(self, validated_data):
        return User.objects.create_user(validated_data['username'], password=validated_data['password1'])
