# E-commerce Product Import

This repository contains a Django e-commerce application with functionality to import products from different data sources.

## Importing Products from CSV

The application now supports importing products from a CSV file. The provided `products.csv` file contains a comprehensive list of products that can be imported into the system.

### CSV File Format

The CSV file should have the following columns:
- `product_name`: Name of the product
- `website`: Source website
- `country`: Country of origin
- `category`: Main product category
- `subcategory`: Product subcategory
- `title-href`: URL to the product
- `price`: Product price
- `brand`: Product brand
- `ingredients`: Product ingredients or description
- `form`: Product form (e.g., cream)
- `type`: Product type
- `color`: Product color
- `size`: Product size
- `rating`: Product rating
- `noofratings`: Number of ratings

### How to Import Products

To import products from the CSV file, use the following management command:

```bash
# Activate your virtual environment first
# Then run:
python manage.py import_products --source csv --limit 100
```

Command options:
- `--source csv`: Specifies to use the CSV file as the data source (instead of the default API)
- `--limit 100`: Limits the import to 100 products (adjust as needed)
- `--csv-file products.csv`: Path to the CSV file (default is 'products.csv' in the project root)
- `--category`: Optionally specify a category to filter products (not typically needed with CSV import)

### Example Commands

Import 100 products from the default CSV file:
```bash
python manage.py import_products --source csv --limit 100
```

Import all products from the CSV file:
```bash
python manage.py import_products --source csv --limit 10000
```

Import from a specific CSV file:
```bash
python manage.py import_products --source csv --csv-file path/to/your/file.csv
```

## Original API Import

The system still supports importing products from the Cosmetics API:

```bash
python manage.py import_products --limit 100 --category "Cream"
```

## Notes

- The import process creates categories based on the category and subcategory fields in the CSV
- Products are uniquely identified by a combination of website, brand, and product name
- Default stock level is set to 50 for all imported products
- The import process is wrapped in a database transaction for data consistency# IDMAX-Cosmetics