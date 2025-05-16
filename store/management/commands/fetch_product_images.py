import os
import csv
import time
import random
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from store.models import Product, ProductImage


class Command(BaseCommand):
    help = 'Fetch product images from URLs in the CSV file and update products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            default='products.csv',
            help='CSV file path containing product data with URLs'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between requests in seconds to be respectful to servers'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of products to process'
        )
        parser.add_argument(
            '--use-placeholders',
            action='store_true',
            help='Use placeholder images instead of scraping when needed'
        )
        parser.add_argument(
            '--retry',
            type=int,
            default=2,
            help='Number of retries for failed requests'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        delay = options['delay']
        limit = options['limit']
        use_placeholders = options['use_placeholders']
        retries = options['retry']
        
        # Ensure the media directory exists
        media_dir = os.path.join(settings.MEDIA_ROOT, 'product_images')
        os.makedirs(media_dir, exist_ok=True)
        
        # Path to the CSV file
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(settings.BASE_DIR, csv_path)
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_path}'))
            return
        
        products_updated = 0
        placeholders_used = 0
        products_skipped = 0
        products_failed = 0
        
        # Custom headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Multiple user agents to rotate through to avoid blocking
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36',
        ]
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                
                product_name = row.get('product_name', '')
                product_url = row.get('title-href', '')
                product_category = row.get('category', '')
                product_subcategory = row.get('subcategory', '')
                
                # Skip if URL is missing
                if not product_url:
                    self.stdout.write(self.style.WARNING(f'Skipping: No URL for "{product_name}"'))
                    products_skipped += 1
                    continue
                
                # Find the product in the database
                products = Product.objects.filter(name__icontains=product_name.split(',')[0])
                if not products.exists():
                    self.stdout.write(self.style.WARNING(f'Skipping: No matching product found for "{product_name}"'))
                    products_skipped += 1
                    continue
                
                product = products.first()
                
                try:
                    self.stdout.write(f'Processing: {product_name}')
                    
                    image_path = None
                    
                    # Try scraping the product page with retries
                    for attempt in range(retries + 1):
                        try:
                            # Rotate user agents
                            current_headers = headers.copy()
                            current_headers['User-Agent'] = random.choice(user_agents)
                            
                            # First try to get image from the product URL
                            image_path = self._try_scrape_image(product_url, product_name, current_headers)
                            
                            if image_path:
                                break
                                
                            # Add delay before retry
                            if attempt < retries:
                                time.sleep(delay * (attempt + 1))  # Exponential backoff
                                
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Attempt {attempt+1} failed for "{product_name}": {str(e)}'))
                            if attempt < retries:
                                time.sleep(delay * (attempt + 1))
                    
                    # If scraping failed, use a placeholder image API
                    if not image_path and use_placeholders:
                        image_path = self._get_placeholder_image(product_name, product_category, product_subcategory)
                        if image_path:
                            self.stdout.write(self.style.WARNING(f'Using placeholder image for "{product_name}"'))
                            placeholders_used += 1
                    
                    if not image_path:
                        self.stdout.write(self.style.ERROR(f'Failed to get any image for "{product_name}"'))
                        products_failed += 1
                        continue
                    
                    # Update the product
                    product.image = image_path
                    product.save()
                    
                    # Also create a ProductImage instance
                    ProductImage.objects.create(
                        product=product,
                        image_url=image_path,
                        alt_text=product_name,
                        is_primary=True
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f'Updated image for "{product_name}"'))
                    products_updated += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing "{product_name}": {str(e)}'))
                    products_failed += 1
                
                # Be respectful with a delay between requests
                time.sleep(delay)
        
        self.stdout.write(self.style.SUCCESS(
            f'Finished! Updated: {products_updated}, Using Placeholders: {placeholders_used}, '
            f'Skipped: {products_skipped}, Failed: {products_failed}'
        ))
    
    def _try_scrape_image(self, url, product_name, headers):
        """Try to scrape an image from the provided URL"""
        try:
            # Fetch the product page
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.stdout.write(self.style.WARNING(
                    f'Failed to fetch URL for "{product_name}": Status {response.status_code}'
                ))
                return None
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if it's Amazon
            if 'amazon' in url.lower():
                return self._extract_amazon_image(soup, product_name)
            # Check if it's Flipkart
            elif 'flipkart' in url.lower():
                return self._extract_flipkart_image(soup, product_name)
            else:
                # Generic extraction
                return self._extract_generic_image(soup, product_name, url)
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error during scraping: {str(e)}'))
            return None
    
    def _extract_amazon_image(self, soup, product_name):
        """Extract image from Amazon product page"""
        # Try multiple selectors used by Amazon
        selectors = [
            '#landingImage',
            '#imgBlkFront',
            '#main-image',
            '.a-dynamic-image',
            'img[data-old-hires]',
            'img.a-dynamic-image',
        ]
        
        for selector in selectors:
            image_element = soup.select_one(selector)
            if image_element:
                # Try different attributes Amazon uses for image URLs
                image_url = image_element.get('data-old-hires') or \
                           image_element.get('data-a-dynamic-image') or \
                           image_element.get('src')
                
                if image_url and '{' in image_url:
                    # Handle JSON format
                    import json
                    try:
                        image_data = json.loads(image_url)
                        image_url = list(image_data.keys())[0] if image_data else None
                    except json.JSONDecodeError:
                        pass
                
                if image_url:
                    return self._download_and_save_image(image_url, product_name)
        
        return None
    
    def _extract_flipkart_image(self, soup, product_name):
        """Extract image from Flipkart product page"""
        # Try multiple selectors used by Flipkart
        selectors = [
            'img._396cs4',
            'img[data-zoom-image]',
            '.CXW8mj img',
            '._396cs4 img',
        ]
        
        for selector in selectors:
            image_element = soup.select_one(selector)
            if image_element:
                image_url = image_element.get('src')
                if image_url:
                    return self._download_and_save_image(image_url, product_name)
        
        return None
    
    def _extract_generic_image(self, soup, product_name, base_url):
        """Extract image using generic selectors that might work across sites"""
        # Try to find a product image based on common patterns
        selectors = [
            'img.product-image',
            'img.product-img',
            'img.productImage',
            'img.product_image',
            'img[id*="product"]',
            'img[class*="product"]',
            'img[id*="main"]',
            'img[class*="main"]',
            'img[id*="primary"]',
            'img[class*="primary"]',
        ]
        
        for selector in selectors:
            image_element = soup.select_one(selector)
            if image_element and image_element.get('src'):
                image_url = image_element.get('src')
                return self._download_and_save_image(image_url, product_name)
        
        # If no specific selectors worked, try to find the largest image
        images = soup.find_all('img')
        largest_image = None
        largest_size = 0
        
        for img in images:
            # Skip tiny images, icons, or data URIs
            src = img.get('src', '')
            if not src or src.startswith('data:') or '/icon' in src.lower():
                continue
                
            # Try to find dimensions
            width = img.get('width', '0')
            height = img.get('height', '0')
            
            try:
                width = int(width)
                height = int(height)
                size = width * height
                if size > largest_size:
                    largest_size = size
                    largest_image = img
            except (ValueError, TypeError):
                # If width/height aren't available or aren't numbers
                if 'product' in src.lower() or 'large' in src.lower() or 'main' in src.lower():
                    largest_image = img
        
        if largest_image and largest_image.get('src'):
            image_url = largest_image.get('src')
            
            # Handle relative URLs
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                base_domain = '/'.join(base_url.split('/')[:3])  # http(s)://domain.com
                image_url = base_domain + image_url
                
            return self._download_and_save_image(image_url, product_name)
            
        return None
    
    def _get_placeholder_image(self, product_name, category, subcategory):
        """Get a placeholder image for the product from various placeholder APIs"""
        try:
            # Clean the product name and category for use in the URL
            clean_name = product_name.replace(' ', '+')[:50]
            clean_category = f"{category}+{subcategory}" if subcategory else category
            clean_category = clean_category.replace(' ', '+')
            
            # Try different placeholder image APIs
            placeholder_apis = [
                f"https://source.unsplash.com/300x300/?{clean_category}+{clean_name}",
                f"https://loremflickr.com/320/240/{clean_category},{clean_name}",
                f"https://placeimg.com/300/300/{clean_category}",
                f"https://dummyimage.com/300x300/aaa/fff.png&text={clean_name}",
                f"https://via.placeholder.com/300x300.png?text={clean_name}"
            ]
            
            for api_url in placeholder_apis:
                try:
                    return self._download_and_save_image(api_url, product_name)
                except Exception:
                    continue
                    
            # If all APIs fail, use a local default placeholder
            return self._create_default_placeholder(product_name)
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error getting placeholder image: {str(e)}"))
            return None
    
    def _create_default_placeholder(self, product_name):
        """Create a default placeholder image with the product name"""
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create a blank image
        img = Image.new('RGB', (300, 300), color=(200, 200, 200))
        d = ImageDraw.Draw(img)
        
        # Try to use a default font
        font_size = 20
        try:
            # Try to find a system font
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            # Fallback to default
            font = ImageFont.load_default()
        
        # Add text
        clean_name = product_name.replace(',', ' ').split(' - ')[0][:40]
        text_x = 150
        text_y = 150
        d.text((text_x, text_y), clean_name, fill=(100, 100, 100), font=font, anchor="mm")
        
        # Save the image
        buffer = io.BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)
        
        # Generate a unique filename
        clean_name = ''.join(e for e in product_name if e.isalnum() or e in [' ', '-', '_'])
        clean_name = clean_name.replace(' ', '_')[:50]
        image_filename = f"{clean_name}_placeholder_{int(time.time())}.jpg"
        image_path = os.path.join('product_images', image_filename)
        
        default_storage.save(image_path, ContentFile(buffer.read()))
        return image_path
    
    def _download_and_save_image(self, image_url, product_name):
        """Download and save an image from the given URL"""
        if not image_url:
            return None
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(image_url, headers=headers, timeout=10, stream=True)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download image: {response.status_code}")
        
        # Check if it's actually an image
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            raise Exception(f"URL does not point to an image: {content_type}")
        
        # Generate a unique filename
        if '.' in image_url.split('/')[-1]:
            extension = image_url.split('.')[-1].split('?')[0].lower()
            # Validate extension
            if extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
                extension = 'jpg'
        else:
            extension = 'jpg'
        
        clean_name = ''.join(e for e in product_name if e.isalnum() or e in [' ', '-', '_'])
        clean_name = clean_name.replace(' ', '_')[:50]
        image_filename = f"{clean_name}_{int(time.time())}.{extension}"
        image_path = os.path.join('product_images', image_filename)
        
        # Save the image
        default_storage.save(image_path, ContentFile(response.content))
        return image_path
