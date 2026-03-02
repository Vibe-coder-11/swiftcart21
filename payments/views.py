from django.shortcuts import render, get_object_or_404
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from products.models import Product
from orders.models import Order, OrderItem
from django.contrib.auth.decorators import login_required
import uuid
import logging


logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payment(request):
    """Create payment for product - direct to seller UPI"""
    try:
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        if quantity <= 0:
            return Response({'error': 'Quantity must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)
        
        product = get_object_or_404(Product, id=product_id, status='active')
        if product.track_inventory and product.quantity < quantity:
            return Response(
                {'error': 'Not enough stock available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_upi_id = getattr(settings, 'ADMIN_UPI_ID', '').strip() or product.seller_upi_id
        if not payment_upi_id:
            return Response({'error': 'Payment is not configured for this product'}, status=status.HTTP_400_BAD_REQUEST)

        recipient_name = request.user.get_full_name().strip() or request.user.email
        recipient_phone = str(getattr(request.user, 'phone', '') or '')
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            status='pending',
            payment_method='upi',
            payment_status='pending',
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            subtotal=product.price * quantity,
            total_amount=product.price * quantity,
            shipping_address="Address to be updated",
            billing_address="Address to be updated",
            payment_upi_id=payment_upi_id,
            status_message='Payment initiated. Please complete payment and share proof.'
        )
        
        # Create order items
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price
        )
        
        return Response({
            'message': 'Payment initiated successfully',
            'order_id': order.id,
            'upi_id': payment_upi_id,
            'amount': order.total_amount
        }, status=status.HTTP_201_CREATED)
        
    except Exception:
        logger.exception('Payment creation failed')
        return Response({
            'error': 'Unable to initiate payment right now.'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def payment_success(request):
    """Handle successful payment"""
    order_id = request.data.get('order_id')
    
    try:
        if request.user.is_superuser:
            order = get_object_or_404(Order, id=order_id)
        else:
            order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status == 'cancelled':
            return Response({'error': 'Cancelled orders cannot be marked as paid.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.payment_status == 'paid':
            return Response({'message': 'Payment already marked successful', 'order': order.id})

        order.payment_status = 'paid'
        order.status = 'confirmed'
        order.save()
        
        return Response({
            'message': 'Payment successful',
            'order': order.id
        })
        
    except Exception:
        logger.exception('Payment success callback failed')
        return Response({
            'error': 'Unable to confirm payment right now.'
        }, status=status.HTTP_400_BAD_REQUEST)
