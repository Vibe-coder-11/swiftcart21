from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_image',
            'price',
            'quantity',
            'subtotal',
        ]

    def get_product_image(self, obj):
        image = obj.product.images.first()
        if not image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(image.image.url)
        return image.image.url

    def get_subtotal(self, obj):
        return str(obj.total)


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    customer_email = serializers.EmailField(source='user.email', read_only=True)
    payment_screenshot_url = serializers.SerializerMethodField()
    refund_screenshot_url = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'payment_status',
            'payment_method',
            'payment_method_display',
            'shipping_address',
            'billing_address',
            'subtotal',
            'tax_amount',
            'shipping_cost',
            'discount_amount',
            'total_amount',
            'tracking_number',
            'admin_notes',
            'status_message',
            'cancellation_reason',
            'recipient_name',
            'recipient_phone',
            'payment_upi_id',
            'payment_transaction_id',
            'payment_phone_number',
            'payment_made_at',
            'payment_screenshot_url',
            'refund_screenshot_url',
            'refund_processed_at',
            'cancellation_request_status',
            'cancellation_request_reason',
            'cancellation_requested_at',
            'estimated_delivery_date',
            'delivery_confirmed_by_customer',
            'delivery_confirmed_at',
            'customer_email',
            'created_at',
            'updated_at',
            'items',
        ]

    def get_payment_screenshot_url(self, obj):
        if not obj.payment_screenshot:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.payment_screenshot.url)
        return obj.payment_screenshot.url

    def get_refund_screenshot_url(self, obj):
        if not obj.refund_screenshot:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.refund_screenshot.url)
        return obj.refund_screenshot.url
