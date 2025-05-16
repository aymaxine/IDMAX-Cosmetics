import os
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Product, ProductImage


class Command(BaseCommand):
    help = 'Update product image paths based on downloaded images in media directory'

    def handle(self, *args, **options):
        # Path to the product images directory
        image_dir = os.path.join(settings.MEDIA_ROOT, 'product_images')
        
        if not os.path.exists(image_dir):
            self.stdout.write(self.style.ERROR(f'Image directory not found: {image_dir}'))
            return
        
        # Get all image files in the directory
        image_files = [f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]
        
        if not image_files:
            self.stdout.write(self.style.WARNING('No image files found in the directory'))
            return
        
        self.stdout.write(f'Found {len(image_files)} image files')
        
        # Track statistics
        products_updated = 0
        products_with_multiple_images = 0
        products_not_found = 0
        
        # Process each image file
        for image_file in image_files:
            image_path = os.path.join('product_images', image_file)
            
            # Extract product name from filename (remove timestamp and extension)
            name_parts = image_file.split('_')
            if len(name_parts) < 2:
                continue
                
            # Remove timestamp (last part before extension) and extension
            product_name_parts = name_parts[:-1]  # Remove the timestamp
            product_name_clean = '_'.join(product_name_parts)
            product_name_clean = product_name_clean.replace('_', ' ')
            
            # Try to find a product with a name containing this string
            matching_products = Product.objects.filter(name__icontains=product_name_clean.split()[0])
            
            if not matching_products:
                # Try with just the first word of the product name
                first_word = product_name_clean.split()[0] if product_name_clean.split() else ""
                if first_word and len(first_word) > 3:  # Only use first word if it's meaningful
                    matching_products = Product.objects.filter(name__icontains=first_word)
            
            if matching_products:
                product = matching_products.first()
                
                # Update the main product image if it's not already set
                if not product.image or 'default' in product.image:
                    product.image = image_path
                    product.save()
                    self.stdout.write(f'Updated main image for product: {product.name}')
                
                # Check if we need to create a ProductImage record
                if not ProductImage.objects.filter(product=product, image_url=image_path).exists():
                    # Create a ProductImage instance
                    is_primary = not ProductImage.objects.filter(product=product, is_primary=True).exists()
                    ProductImage.objects.create(
                        product=product,
                        image_url=image_path,
                        alt_text=product.name,
                        is_primary=is_primary
                    )
                    
                    if ProductImage.objects.filter(product=product).count() > 1:
                        products_with_multiple_images += 1
                
                products_updated += 1
            else:
                products_not_found += 1
                self.stdout.write(self.style.WARNING(f'No matching product found for image: {image_file}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully processed {len(image_files)} image files.\n'
            f'Products updated: {products_updated}\n'
            f'Products with multiple images: {products_with_multiple_images}\n'
            f'Images without matching products: {products_not_found}'
        ))
