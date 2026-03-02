from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class TimeStampedModel(models.Model):
    """Abstract base model with created_at and updated_at fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    """Abstract base model with soft delete functionality"""
    is_deleted = models.BooleanField(_('deleted'), default=False)
    deleted_at = models.DateTimeField(_('deleted at'), null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Mark the object as deleted"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """Restore the soft deleted object"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

class SiteSettings(TimeStampedModel):
    """Global site settings"""
    site_name = models.CharField(_('site name'), max_length=100, default='SwiftCart')
    site_description = models.TextField(
        _('site description'),
        blank=True,
        default='SwiftCart is an online shopping platform registered in 2026.',
    )
    site_logo = models.ImageField(_('site logo'), upload_to='settings/', blank=True, null=True)
    favicon = models.ImageField(_('favicon'), upload_to='settings/', blank=True, null=True)
    
    # Contact Information
    contact_email = models.EmailField(_('contact email'), blank=True)
    contact_phone = models.CharField(_('contact phone'), max_length=20, blank=True)
    contact_address = models.TextField(_('contact address'), blank=True)
    
    # Social Media
    facebook_url = models.URLField(_('Facebook URL'), blank=True)
    twitter_url = models.URLField(_('Twitter URL'), blank=True)
    instagram_url = models.URLField(_('Instagram URL'), blank=True)
    linkedin_url = models.URLField(_('LinkedIn URL'), blank=True)
    
    # Business Settings
    commission_rate = models.DecimalField(_('commission rate'), max_digits=5, decimal_places=2, default=10.00)
    shipping_cost = models.DecimalField(_('shipping cost'), max_digits=10, decimal_places=2, default=50.00)
    tax_rate = models.DecimalField(_('tax rate'), max_digits=5, decimal_places=2, default=18.00)
    
    # Currency Settings
    default_currency = models.CharField(_('default currency'), max_length=3, default='INR')
    
    # Email Settings
    send_order_emails = models.BooleanField(_('send order emails'), default=True)
    send_payment_emails = models.BooleanField(_('send payment emails'), default=True)
    
    class Meta:
        verbose_name = _('Site Settings')
        verbose_name_plural = _('Site Settings')
        
    def __str__(self):
        return self.site_name

class Banner(TimeStampedModel):
    """Homepage banners and promotional banners"""
    BANNER_TYPES = (
        ('hero', _('Hero Banner')),
        ('promotion', _('Promotion Banner')),
        ('announcement', _('Announcement Banner')),
        ('category', _('Category Banner')),
    )
    
    title = models.CharField(_('title'), max_length=200)
    subtitle = models.CharField(_('subtitle'), max_length=300, blank=True)
    description = models.TextField(_('description'), blank=True)
    image = models.ImageField(_('image'), upload_to='banners/')
    banner_type = models.CharField(_('banner type'), max_length=20, choices=BANNER_TYPES, default='hero')
    
    # Link settings
    link_url = models.URLField(_('link URL'), blank=True)
    link_text = models.CharField(_('link text'), max_length=100, blank=True)
    
    # Display settings
    is_active = models.BooleanField(_('active'), default=True)
    start_date = models.DateTimeField(_('start date'), null=True, blank=True)
    end_date = models.DateTimeField(_('end date'), null=True, blank=True)
    sort_order = models.PositiveIntegerField(_('sort order'), default=0)
    
    class Meta:
        verbose_name = _('Banner')
        verbose_name_plural = _('Banners')
        ordering = ['sort_order', '-created_at']
        
    def __str__(self):
        return self.title
    
    def is_currently_active(self):
        """Check if banner is currently active based on dates"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
            
        if self.start_date and now < self.start_date:
            return False
            
        if self.end_date and now > self.end_date:
            return False
            
        return True

class Newsletter(TimeStampedModel):
    """Newsletter subscribers"""
    email = models.EmailField(_('email'), unique=True)
    is_active = models.BooleanField(_('active'), default=True)
    
    class Meta:
        verbose_name = _('Newsletter Subscriber')
        verbose_name_plural = _('Newsletter Subscribers')
        
    def __str__(self):
        return self.email

class ContactMessage(TimeStampedModel):
    """Contact form messages"""
    name = models.CharField(_('name'), max_length=100)
    email = models.EmailField(_('email'))
    subject = models.CharField(_('subject'), max_length=200)
    message = models.TextField(_('message'))
    is_read = models.BooleanField(_('read'), default=False)
    
    class Meta:
        verbose_name = _('Contact Message')
        verbose_name_plural = _('Contact Messages')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} - {self.subject}"
