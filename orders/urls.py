from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('buy-now/', views.buy_now, name='buy_now'),
    path('<int:order_id>/request-cancellation/', views.request_cancellation, name='request_cancellation'),
    path('<int:order_id>/confirm-delivery/', views.confirm_delivery, name='confirm_delivery'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
]
