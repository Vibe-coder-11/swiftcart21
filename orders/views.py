import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from products.models import Product
from .models import Order, OrderItem
from .serializers import OrderDetailSerializer


def _generate_order_number():
    while True:
        order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        if not Order.objects.filter(order_number=order_number).exists():
            return order_number


def _parse_datetime_input(value):
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def buy_now(request):
    product_id = request.data.get('product_id')
    quantity_value = request.data.get('quantity', 1)
    recipient_name = (request.data.get('recipient_name') or '').strip()
    recipient_phone = (request.data.get('recipient_phone') or '').strip()
    shipping_address = (request.data.get('shipping_address') or '').strip()
    house_details = (
        request.data.get('house_details')
        or request.data.get('house_name_building_landmark')
        or ''
    ).strip()
    village = (request.data.get('village') or '').strip()
    post_office = (request.data.get('post_office') or '').strip()
    district = (request.data.get('district') or '').strip()
    pin_code = (request.data.get('pin_code') or '').strip()
    payment_transaction_id = (request.data.get('payment_transaction_id') or '').strip()
    payment_phone_number = (request.data.get('payment_phone_number') or '').strip()
    payment_made_at_raw = (
        request.data.get('payment_made_at')
        or request.data.get('payment_date_time')
        or ''
    ).strip()
    payment_screenshot = request.FILES.get('payment_screenshot')
    payment_made_at = _parse_datetime_input(payment_made_at_raw) if payment_made_at_raw else None

    errors = {}
    if not product_id:
        errors['product_id'] = 'Product is required.'
    if not recipient_name:
        errors['recipient_name'] = 'Name is required.'
    if not recipient_phone:
        errors['recipient_phone'] = 'Mobile number is required.'
    if not payment_phone_number:
        # Fallback to recipient number so refund routing remains available.
        payment_phone_number = recipient_phone
    if not payment_phone_number:
        errors['payment_phone_number'] = 'Payment mobile number is required.'
    if not payment_made_at_raw:
        errors['payment_made_at'] = 'Payment date and time is required.'
    elif not payment_made_at:
        errors['payment_made_at'] = 'Invalid payment date and time format.'

    # Support both legacy shipping_address and structured address fields.
    if not shipping_address:
        if not house_details:
            errors['house_details'] = 'House / Building / Landmark is required.'
        if not village:
            errors['village'] = 'Village is required.'
        if not post_office:
            errors['post_office'] = 'Post office is required.'
        if not district:
            errors['district'] = 'District is required.'
        if not pin_code:
            errors['pin_code'] = 'PIN code is required.'
        elif not pin_code.isdigit() or len(pin_code) != 6:
            errors['pin_code'] = 'PIN code must be 6 digits.'

    if not payment_screenshot:
        errors['payment_screenshot'] = 'Payment screenshot is required.'

    try:
        quantity = int(quantity_value)
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        errors['quantity'] = 'Quantity must be a positive number.'
        quantity = 0

    if errors:
        return Response(
            {'success': False, 'error': 'Validation failed', 'errors': errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not shipping_address:
        shipping_address = (
            f"{house_details}, Village: {village}, "
            f"Post Office: {post_office}, District: {district}, PIN: {pin_code}"
        )

    product = get_object_or_404(Product, id=product_id, status='active')

    if product.track_inventory and product.quantity < quantity:
        return Response(
            {
                'success': False,
                'error': 'Not enough stock available.',
                'available_quantity': product.quantity,
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        subtotal = Decimal(product.price) * Decimal(quantity)
    except (TypeError, InvalidOperation):
        return Response(
            {'success': False, 'error': 'Invalid product price configuration.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    payment_upi_id = getattr(settings, 'ADMIN_UPI_ID', '').strip() or product.seller_upi_id
    if not payment_upi_id:
        return Response(
            {'success': False, 'error': 'Payment UPI ID is not configured. Please contact admin.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            order_number=_generate_order_number(),
            status='pending',
            payment_status='pending',
            payment_method='upi',
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            shipping_address=shipping_address,
            billing_address=shipping_address,
            subtotal=subtotal,
            total_amount=subtotal,
            payment_upi_id=payment_upi_id,
            payment_transaction_id=payment_transaction_id,
            payment_phone_number=payment_phone_number,
            payment_made_at=payment_made_at,
            payment_screenshot=payment_screenshot,
            status_message='Payment screenshot submitted. Awaiting admin approval.',
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price,
        )

        if product.track_inventory:
            product.quantity = product.quantity - quantity
            product.save(update_fields=['quantity', 'updated_at'])

    return Response(
        {
            'success': True,
            'message': 'Order submitted successfully. Admin will review and update your order status.',
            'order_id': str(order.id),
            'order_number': order.order_number,
            'redirect_url': '/orders/',
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def request_cancellation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    reason = (request.data.get('reason') or '').strip()

    if order.status in ['cancelled', 'delivered']:
        return Response(
            {'success': False, 'error': 'This order cannot be canceled now.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if order.cancellation_request_status == 'pending':
        return Response(
            {'success': True, 'message': 'Cancellation request already submitted for admin approval.'}
        )

    if not reason:
        return Response(
            {'success': False, 'error': 'Please provide cancellation reason.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    order.cancellation_request_status = 'pending'
    order.cancellation_request_reason = reason
    order.cancellation_requested_at = timezone.now()
    order.status_message = 'Cancellation requested by customer. Awaiting admin approval.'
    order.save(
        update_fields=[
            'cancellation_request_status',
            'cancellation_request_reason',
            'cancellation_requested_at',
            'status_message',
            'updated_at',
        ]
    )

    return Response(
        {
            'success': True,
            'message': 'Cancellation request submitted. Admin will review it.',
            'cancellation_request_status': order.cancellation_request_status,
        }
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.cancellation_request_status == 'pending':
        return Response(
            {'success': False, 'error': 'Cancellation request is pending admin review.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if order.status in ['pending', 'cancelled']:
        return Response(
            {'success': False, 'error': 'This order is not eligible for delivery confirmation.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if order.delivery_confirmed_by_customer:
        return Response(
            {
                'success': True,
                'message': 'Delivery was already confirmed.',
                'status': order.status,
            }
        )

    if order.status not in ['confirmed', 'processing', 'shipped', 'delivered']:
        return Response(
            {'success': False, 'error': 'Order status does not allow delivery confirmation.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    order.status = 'delivered'
    order.delivery_confirmed_by_customer = True
    order.delivery_confirmed_at = timezone.now()
    order.save(
        update_fields=[
            'status',
            'delivery_confirmed_by_customer',
            'delivery_confirmed_at',
            'updated_at',
        ]
    )

    return Response(
        {
            'success': True,
            'message': 'Delivery confirmed successfully.',
            'status': order.status,
            'delivery_confirmed_by_customer': order.delivery_confirmed_by_customer,
            'delivery_confirmed_at': order.delivery_confirmed_at,
        }
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product__images'), id=order_id)

    if not request.user.is_superuser and order.user_id != request.user.id:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = OrderDetailSerializer(order, context={'request': request})
    return Response(serializer.data)
