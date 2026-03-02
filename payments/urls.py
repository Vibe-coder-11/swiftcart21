from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('create/', views.create_payment, name='create_payment'),
    path('success/', views.payment_success, name='payment_success'),
]
