from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import View
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from accounts.models import User as CustomUser
from sellers.models import Seller
from products.models import Product
from orders.models import Order
from .models import ContactMessage
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

def admin_login_required(view_func):
    """Decorator to check if user is admin (superuser only)"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        
        # Check if user is superuser
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('admin_login')
    return wrapper

class AdminLoginView(View):
    """Admin login page using .env credentials"""
    template_name = 'core/admin_login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin_dashboard')
            else:
                # Don't redirect to admin_login if user is not admin, just show the page
                pass
        return render(request, self.template_name)
    
    def post(self, request):
        email = (request.POST.get('email') or '').strip().lower()
        password = (request.POST.get('password') or '').strip()
        
        # Check against .env admin credentials
        admin_email = (getattr(settings, 'ADMIN_EMAIL', '') or '').strip().lower()
        admin_password = getattr(settings, 'ADMIN_PASSWORD', '') or ''
        
        if email == admin_email and password == admin_password:
            # Try to authenticate with existing user or create/get admin user
            user = CustomUser.objects.filter(email__iexact=admin_email).first()
            if not user:
                user = CustomUser.objects.create_superuser(
                    email=admin_email,
                    password=admin_password,
                    first_name='Admin',
                    last_name='User',
                    role='admin',
                    is_active=True
                )
            else:
                update_fields = []
                if user.email != admin_email:
                    user.email = admin_email
                    update_fields.append('email')
                if user.role != 'admin':
                    user.role = 'admin'
                    update_fields.append('role')
                if not user.is_staff:
                    user.is_staff = True
                    update_fields.append('is_staff')
                if not user.is_superuser:
                    user.is_superuser = True
                    update_fields.append('is_superuser')
                if not user.is_active:
                    user.is_active = True
                    update_fields.append('is_active')
                if not user.first_name:
                    user.first_name = 'Admin'
                    update_fields.append('first_name')
                if not user.last_name:
                    user.last_name = 'User'
                    update_fields.append('last_name')
                if not user.check_password(admin_password):
                    user.set_password(admin_password)
                    update_fields.append('password')
                if update_fields:
                    user.save(update_fields=update_fields)
            
            # Authenticate and login
            authenticated_user = authenticate(request, username=admin_email, password=admin_password)
            if authenticated_user:
                login(request, authenticated_user)
                messages.success(request, 'Welcome to Admin Dashboard!')
                return redirect('admin_dashboard')
        
        messages.error(request, 'Invalid admin credentials')
        return render(request, self.template_name)

@admin_login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    # Get statistics
    total_users = CustomUser.objects.filter(is_superuser=False).count()
    total_sellers = Seller.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_contact_messages = ContactMessage.objects.count()
    unread_contact_messages = ContactMessage.objects.filter(is_read=False).count()
    
    # Get pending sellers
    pending_sellers = Seller.objects.filter(approval_status='pending')[:5]
    
    # Get seller category for admin, create if it doesn't exist
    from products.models import Category
    seller_category, created = Category.objects.get_or_create(
        name='Seller Products',
        defaults={
            'slug': 'seller-products',
            'is_active': True
        }
    )
    
    # Get recent activities (empty for now)
    recent_activities = []
    recent_contact_messages = ContactMessage.objects.order_by('-created_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_contact_messages': total_contact_messages,
        'unread_contact_messages': unread_contact_messages,
        'pending_sellers': pending_sellers,
        'seller_category': seller_category,
        'recent_activities': recent_activities,
        'recent_contact_messages': recent_contact_messages,
    }
    
    return render(request, 'core/admin_dashboard.html', context)


@admin_login_required
def admin_contact_messages(request):
    """Admin contact messages list"""
    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip().lower()
        message_id = (request.POST.get('message_id') or '').strip()

        if message_id:
            try:
                contact_message = ContactMessage.objects.get(id=message_id)
                if action == 'mark_read':
                    contact_message.is_read = True
                    contact_message.save(update_fields=['is_read', 'updated_at'])
                    messages.success(request, 'Message marked as read.')
                elif action == 'delete':
                    contact_message.delete()
                    messages.success(request, 'Message deleted successfully.')
            except ContactMessage.DoesNotExist:
                messages.error(request, 'Message not found.')

        return redirect('admin_contact_messages')

    messages_qs = ContactMessage.objects.order_by('-created_at')

    status_filter = (request.GET.get('status') or '').strip().lower()
    if status_filter == 'unread':
        messages_qs = messages_qs.filter(is_read=False)
    elif status_filter == 'read':
        messages_qs = messages_qs.filter(is_read=True)

    context = {
        'messages_list': messages_qs,
        'total_messages': ContactMessage.objects.count(),
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
        'read_messages': ContactMessage.objects.filter(is_read=True).count(),
    }
    return render(request, 'core/admin_contacts.html', context)

@admin_login_required
def admin_users(request):
    """Admin users management"""
    users = CustomUser.objects.filter(is_superuser=False).order_by('-created_at')
    
    context = {
        'users': users
    }
    return render(request, 'core/admin_users.html', context)

@admin_login_required
def admin_sellers(request):
    """Admin sellers management"""
    sellers = Seller.objects.select_related('user').order_by('-created_at')
    
    context = {
        'sellers': sellers
    }
    return render(request, 'core/admin_sellers.html', context)

@admin_login_required
def admin_products(request):
    """Admin products management"""
    products = Product.objects.select_related('category', 'seller').order_by('-created_at')
    
    context = {
        'products': products
    }
    return render(request, 'core/admin_products.html', context)

@admin_login_required
def admin_orders(request):
    """Admin orders management"""
    orders = Order.objects.select_related('user').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Calculate statistics
    pending_orders = Order.objects.filter(status='pending').count()
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    context = {
        'orders': orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
    }
    return render(request, 'core/user_orders.html', context)

@admin_login_required
def admin_activities(request):
    """Admin activities monitoring"""
    from orders.models import Order

    today = timezone.now().date()

    active_users_today = CustomUser.objects.filter(last_login__date=today).count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_registrations = CustomUser.objects.filter(created_at__date=today).count()

    pending_orders = Order.objects.filter(status='pending').count()
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    completed_orders = Order.objects.filter(status='delivered').count()
    total_orders = Order.objects.count()

    recent_activities = []

    recent_orders_list = Order.objects.select_related('user').order_by('-created_at')[:10]
    for order in recent_orders_list:
        user_role = getattr(order.user, 'role', 'user') if order.user else 'user'
        if user_role == 'customer':
            user_role = 'user'

        recent_activities.append({
            'user': order.user.email if order.user else 'Guest',
            'action': f'Placed order #{order.order_number} - INR {order.total_amount}',
            'timestamp': order.created_at,
            'ip_address': 'N/A',
            'user_agent': 'N/A',
            'type': 'order',
            'order_id': order.id,
            'status': 'success',
            'user_email': order.user.email if order.user else 'guest@example.com',
            'user_type': user_role,
        })

    recent_users_list = CustomUser.objects.order_by('-created_at')[:5]
    for user in recent_users_list:
        user_role = user.role if user.role else 'user'
        if user_role == 'customer':
            user_role = 'user'

        recent_activities.append({
            'user': user.email,
            'action': 'Registered new account',
            'timestamp': user.created_at,
            'ip_address': 'N/A',
            'user_agent': 'N/A',
            'type': 'registration',
            'user_id': user.id,
            'status': 'success',
            'user_email': user.email,
            'user_type': user_role,
        })

    recent_logins = CustomUser.objects.filter(last_login__isnull=False).order_by('-last_login')[:10]
    for user in recent_logins:
        user_role = user.role if user.role else 'user'
        if user_role == 'customer':
            user_role = 'user'

        recent_activities.append({
            'user': user.email,
            'action': 'Logged in',
            'timestamp': user.last_login,
            'ip_address': 'N/A',
            'user_agent': 'N/A',
            'type': 'login',
            'user_id': user.id,
            'status': 'success',
            'user_email': user.email,
            'user_type': user_role,
        })

    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)

    context = {
        'activities': recent_activities,
        'today_activities': today_registrations + today_orders + active_users_today,
        'active_users': active_users_today,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'completed_orders': completed_orders,
        'total_orders': total_orders,
        'recent_orders': recent_orders_list[:5],
        'failed_logins': 0,
        'system_alerts': 0,
    }
    return render(request, 'core/admin_activities.html', context)

# API Views for Admin
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_dashboard_api(request):
    """API endpoint for admin dashboard data"""
    # Check if user is superuser
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get statistics
    total_users = CustomUser.objects.filter(role='user').count()
    total_sellers = Seller.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    
    # Get pending sellers
    pending_sellers_data = []
    for seller in Seller.objects.filter(approval_status='pending')[:5]:
        pending_sellers_data.append({
            'id': seller.id,
            'business_name': seller.business_name,
            'user_email': seller.user.email,
            'created_at': seller.created_at
        })
    
    # Mock recent activities
    recent_activities = [
        {
            'user': 'New User',
            'action': 'Registered',
            'time': '2 hours ago'
        },
        {
            'user': 'Seller XYZ',
            'action': 'Applied for seller account',
            'time': '4 hours ago'
        }
    ]
    
    return Response({
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_sellers': pending_sellers_data,
        'recent_activities': recent_activities
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_seller(request, seller_id):
    """Approve a seller"""
    if not (request.user.is_superuser or request.user.email == getattr(settings, 'ADMIN_EMAIL', '')):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        seller = Seller.objects.get(id=seller_id)
        seller.approval_status = 'approved'
        seller.approved_by = request.user
        seller.approved_at = timezone.now()
        seller.save()
        
        return Response({'message': 'Seller approved successfully'})
    except Seller.DoesNotExist:
        return Response({'error': 'Seller not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_seller(request, seller_id):
    """Reject a seller"""
    if not (request.user.is_superuser or request.user.email == getattr(settings, 'ADMIN_EMAIL', '')):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        seller = Seller.objects.get(id=seller_id)
        rejection_reason = request.data.get('rejection_reason', '')
        seller.approval_status = 'rejected'
        seller.rejection_reason = rejection_reason
        seller.approved_by = request.user
        seller.save()
        
        return Response({'message': 'Seller rejected successfully'})
    except Seller.DoesNotExist:
        return Response({'error': 'Seller not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_seller(request, seller_id):
    """Delete a seller"""
    if not (request.user.is_superuser or request.user.email == getattr(settings, 'ADMIN_EMAIL', '')):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        seller = Seller.objects.get(id=seller_id)
        user = seller.user
        seller.delete()
        user.delete()  # Also delete the associated user
        
        return Response({'message': 'Seller deleted successfully'})
    except Seller.DoesNotExist:
        return Response({'error': 'Seller not found'}, status=status.HTTP_404_NOT_FOUND)
