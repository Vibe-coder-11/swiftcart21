from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductVariant

class CategorySerializer(serializers.ModelSerializer):
    """Category serializer"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'parent', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer"""
    image_url = serializers.ImageField(source='image', read_only=True)
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'alt_text', 'sort_order', 'is_primary']

class ProductVariantSerializer(serializers.ModelSerializer):
    """Product variant serializer"""
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku', 'price', 'quantity', 'weight', 
                  'option1_name', 'option1_value', 'option2_name', 'option2_value']

class ProductSerializer(serializers.ModelSerializer):
    """Product serializer with clean validation"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'short_description',
            'price', 'compare_price', 'cost_price', 'sku', 'barcode',
            'track_inventory', 'quantity', 'weight', 'status', 'featured',
            'digital', 'seller_upi_id', 'meta_title', 
            'meta_description', 'category', 'category_name', 'seller', 
            'images', 'variants', 'is_in_stock', 'discount_percentage', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Clean validation for product creation"""
        # Generate slug from name if not provided
        if not attrs.get('slug') and attrs.get('name'):
            import re
            slug = attrs['name'].lower()
            slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
            attrs['slug'] = slug
        
        # Ensure slug is unique
        if attrs.get('slug'):
            from .models import Product
            queryset = Product.objects.filter(slug=attrs['slug'])
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                # Make slug unique by adding counter
                counter = 1
                original_slug = attrs['slug']
                while queryset.exists():
                    attrs['slug'] = f"{original_slug}-{counter}"
                    counter += 1
                    queryset = Product.objects.filter(slug=attrs['slug'])
                    if self.instance:
                        queryset = queryset.exclude(pk=self.instance.pk)
        
        return attrs

class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer (minimal data for list views)"""
    primary_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'price',
            'compare_price', 'featured', 'seller_upi_id',
            'category_name', 'primary_image', 'is_in_stock', 
            'discount_percentage', 'created_at'
        ]
    
    def get_primary_image(self, obj):
        """Get primary image or first image"""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image.url
        first_image = obj.images.first()
        if first_image:
            return first_image.image.url
        return None
