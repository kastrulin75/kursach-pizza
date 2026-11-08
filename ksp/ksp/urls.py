from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ksa import views

router = DefaultRouter()
router.register('categories', views.CategoryViewSet)
router.register('pizzas', views.PizzaViewSet)
router.register('cart', views.CartViewSet, basename='cart')
router.register('orders', views.OrderViewSet, basename='order')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register/', views.register),
    path('api/auth/login/', views.login),
    path('api/auth/logout/', views.logout),
    path('api/auth/me/', views.me),
    path('api/', include(router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
