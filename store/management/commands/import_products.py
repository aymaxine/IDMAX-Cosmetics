import csv
import requests
import json
import logging
import os
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError, DatabaseError
from store.models import Category, Product
from django.utils.text import slugify
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import products from CSV file (default) or Open Food Facts API'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=2000, help='Number of products to import (0 for all available products)')
        parser.add_argument('--category', type=str, default='', help='Category to import')
        parser.add_argument('--source', type=str, default='csv', choices=['api', 'csv'], help='Source of product data (api or csv)')
        parser.add_argument('--csv-file', type=str, default='products.csv', help='Path to CSV file (relative to project root)')

    def handle(self, *args, **options):
        limit = options['limit']
        category_name = options['category']
        source = options['source']
        csv_file = options['csv_file']

        # If limit is 0, we'll import all available products
        limit_message = "all available" if limit == 0 else limit
        self.stdout.write(self.style.SUCCESS(f'Starting import of {limit_message} products from {source}...'))

        # Create or get the category
        if category_name:
            category, created = Category.objects.get_or_create(name=category_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category_name}'))
        else:
            # Default category
            category, created = Category.objects.get_or_create(name='Products')
            if created:
                self.stdout.write(self.style.SUCCESS('Created default category: Products'))

        if source == 'csv':
            self.import_from_csv(csv_file, limit, category)
        else:
            self.import_from_api(limit, category_name, category)

    def import_from_csv(self, csv_file, limit, default_category):
        """Import products from a CSV file"""
        try:
            # Check if the file exists
            if not os.path.exists(csv_file):
                # Try with ecommerce prefix
                csv_file = os.path.join('ecommerce', csv_file)
                if not os.path.exists(csv_file):
                    self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_file}'))
                    return

            self.stdout.write(f'Importing data from CSV file: {csv_file}')

            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as file:
                reader = csv.DictReader(file)

                # Import products
                with transaction.atomic():
                    count = 0
                    for row in reader:
                        try:
                            # Check if we've reached the limit
                            if limit > 0 and count >= limit:
                                break

                            # Extract product data
                            name = row.get('product_name', '')
                            if not name:
                                continue

                            # Truncate name if too long
                            if len(name) > 200:
                                name = name[:197] + '...'

                            # Get or create category based on CSV data
                            category_name = row.get('category', '')
                            subcategory_name = row.get('subcategory', '')

                            if category_name and subcategory_name:
                                category, _ = Category.objects.get_or_create(name=f"{category_name} - {subcategory_name}")
                            elif category_name:
                                category, _ = Category.objects.get_or_create(name=category_name)
                            else:
                                category = default_category

                            # Get description from ingredients
                            description = row.get('ingredients', '')
                            if not description:
                                description = f"Brand: {row.get('brand', '')}, Type: {row.get('type', '')}"

                            # Get price
                            try:
                                price_str = row.get('price', '0')
                                price = Decimal(price_str)
                                # Ensure price is positive
                                if price < 0:
                                    price = Decimal('9.99')  # Default price for negative values
                            except (ValueError, InvalidOperation, TypeError) as e:
                                logger.warning(f"Invalid price format: {e}. Using default price.")
                                price = Decimal('9.99')  # Default price

                            # Get stock (default value)
                            try:
                                stock_str = row.get('stock', '50')
                                stock = int(stock_str)
                                # Ensure stock is positive
                                if stock < 0:
                                    stock = 50  # Default stock for negative values
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Invalid stock format: {e}. Using default stock.")
                                stock = 50  # Default stock

                            # Create a unique external_id
                            external_id = f"{row.get('website', '')}-{row.get('brand', '')}-{name}"[:100]

                            # Create or update the product
                            product, created = Product.objects.update_or_create(
                                external_id=external_id,
                                defaults={
                                    'name': name,
                                    'description': description or 'No description available',
                                    'price': price,
                                    'category': category,
                                    'stock': stock,
                                    'available': True,
                                    'data_source': row.get('website', 'CSV Import'),
                                }
                            )

                            count += 1
                            if count % 100 == 0:
                                self.stdout.write(f'Imported {count} products...')

                        except (KeyError, ValueError, TypeError, IntegrityError, DatabaseError) as e:
                            logger.error(f"Error importing product: {e}")
                            self.stdout.write(self.style.ERROR(f'Error importing product: {e}'))
                        except Exception as e:
                            logger.error(f"Unexpected error importing product: {e}", exc_info=True)
                            self.stdout.write(self.style.ERROR(f'Unexpected error importing product: {e}'))

                self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} products from CSV'))

        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"File error when importing from CSV: {e}")
            self.stdout.write(self.style.ERROR(f'File error when importing from CSV: {e}'))
        except (csv.Error, UnicodeDecodeError) as e:
            logger.error(f"CSV parsing error: {e}")
            self.stdout.write(self.style.ERROR(f'CSV parsing error: {e}'))
        except (DatabaseError, IntegrityError) as e:
            logger.error(f"Database error when importing from CSV: {e}")
            self.stdout.write(self.style.ERROR(f'Database error when importing from CSV: {e}'))
        except Exception as e:
            logger.error(f"Unexpected error importing data from CSV: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'Unexpected error importing data from CSV: {e}'))

    def import_from_api(self, limit, category_name, category):
        """Import products from Open Food Facts API"""
        # API fetching functionality has been commented out as requested
        self.stdout.write(self.style.WARNING('API fetching functionality has been disabled.'))
        self.stdout.write(self.style.SUCCESS('No products were imported from API.'))
        return
