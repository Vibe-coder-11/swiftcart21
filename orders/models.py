from django.db import models
from django.conf import settings
from django.utils import timezone
from products.models import Product

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('upi', 'UPI'),
        ('card', 'Credit/Debit Card'),
        ('net_banking', 'Net Banking'),
    ]

    CANCELLATION_REQUEST_STATUS_CHOICES = [
        ('none', 'No Request'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')

    # Buyer and payment proof details
    recipient_name = models.CharField(max_length=150, blank=True, default='')
    recipient_phone = models.CharField(max_length=20, blank=True, default='')
    payment_upi_id = models.CharField(max_length=80, blank=True, default='')
    payment_transaction_id = models.CharField(max_length=120, blank=True, default='')
    payment_phone_number = models.CharField(max_length=20, blank=True, default='')
    payment_made_at = models.DateTimeField(blank=True, null=True)
    payment_screenshot = models.ImageField(upload_to='orders/payments/', blank=True, null=True)
    refund_screenshot = models.ImageField(upload_to='orders/refunds/', blank=True, null=True)
    refund_processed_at = models.DateTimeField(blank=True, null=True)
    
    # Address information
    shipping_address = models.TextField()
    billing_address = models.TextField(blank=True, null=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Tracking and notes
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    status_message = models.TextField(blank=True, default='')
    cancellation_reason = models.TextField(blank=True, default='')
    cancellation_request_status = models.CharField(
        max_length=20,
        choices=CANCELLATION_REQUEST_STATUS_CHOICES,
        default='none'
    )
    cancellation_request_reason = models.TextField(blank=True, default='')
    cancellation_requested_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_orders'
    )
    estimated_delivery_date = models.DateField(blank=True, null=True)
    delivery_confirmed_by_customer = models.BooleanField(default=False)
    delivery_confirmed_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    @property
    def customer_name(self):
        if self.recipient_name:
            return self.recipient_name
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.email
    
    @property
    def customer_email(self):
        return self.user.email
    
    @property
    def customer_phone(self):
        return self.recipient_phone or getattr(self.user, 'phone', None)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def total(self):
        return self.price * self.quantity
    
    @property
    def product_name(self):
        return self.product.name
