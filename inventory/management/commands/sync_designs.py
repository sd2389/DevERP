# inventory/management/commands/sync_designs.py

import json
import logging
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import Design, Category

logger = logging.getLogger('inventory')

class Command(BaseCommand):
    help = 'Synchronize designs from DevJewels API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all designs regardless of changes',
        )
        
        parser.add_argument(
            '--active',
            action='store_true',
            help='Set all newly created designs to active by default',
            default=True,
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"Starting design synchronization at {start_time}")
        force_update = options['force']
        set_active = options['active']
        
        try:
            # API credentials
            API_DESIGN_URL = "https://admin.devjewels.com/mobileapi/api_design.php"
            USER_ID = "admin@eg.com"
            
            # Get existing designs for comparison
            existing_designs = {d.design_no: d for d in Design.objects.all()}
            self.stdout.write(f"Found {len(existing_designs)} existing designs in database")
            
            # Fetch from API
            self.stdout.write("Fetching designs from API...")
            response = requests.post(
                API_DESIGN_URL, 
                json={'userid': USER_ID}, 
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response
            api_data = response.json()
            if not isinstance(api_data, dict) or 'data' not in api_data:
                raise ValueError(f"Unexpected API response format: {api_data}")
                
            design_data = api_data.get('data', [])
            
            # Process each design
            stats = {'total': len(design_data), 'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0}
            
            # Collect categories for bulk processing
            categories = set()
            
            for design in design_data:
                try:
                    design_no = design.get('design_no')
                    if not design_no:
                        self.stdout.write(f"Skipping design with no design_no")
                        stats['skipped'] += 1
                        continue
                    
                    # Extract category and add to set for later processing
                    category_name = (design.get('category') or '').strip().title()
                    if category_name:
                        categories.add(category_name)
                    
                    # Prepare the design data
                    design_fields = {
                        'design_id': design.get('design_id', ''),
                        'date': timezone.now().date(),  # Set current date if not provided
                        'category': category_name,
                        'subcategory': design.get('subcategory', ''),
                        'titleline': design.get('titleline', ''),
                        'brand': design.get('brand', ''),
                        'gender': design.get('gender', ''),
                        'collection': design.get('collection', ''),
                        'producttype': design.get('producttype', ''),
                        'occation': design.get('occation', ''),
                        'gwt': float(design.get('gwt', 0) or 0),
                        'nwt': float(design.get('nwt', 0) or 0),
                        'dwt': float(design.get('dwt', 0) or 0),
                        'dpcs': int(design.get('dpcs', 0) or 0),
                        'swt': float(design.get('swt', 0) or 0),
                        'spcs': int(design.get('spcs', 0) or 0),
                        'miscwt': float(design.get('miscwt', 0) or 0),
                        'miscpcs': int(design.get('miscpcs', 0) or 0),
                        'remarks': design.get('remarks', ''),
                        'isNew': bool(design.get('isNew', False)),
                        'length': design.get('length', ''),
                        'width': design.get('width', ''),
                        'size': design.get('size', ''),
                        'margin': float(design.get('margin', 0) or 0),
                        'duty': float(design.get('duty', 0) or 0),
                        'totamt': float(design.get('totamt', 0) or 0),
                        'vendor_code': design.get('vendor_code', ''),
                        'parent_designno': design.get('parent_designno', ''),
                        'package': design.get('package', ''),
                        'stock_qty': int(design.get('stock_qty', 0) or 0),
                        'is_active': set_active,
                        'image_base_path': f"https://dev-jewels.s3.us-east-2.amazonaws.com/products/{design_no}",
                        'last_synced': timezone.now(),
                    }
                    
                    # Use update_or_create to handle both new and existing designs
                    design_obj, created = Design.objects.update_or_create(
                        design_no=design_no,
                        defaults=design_fields
                    )
                    
                    if created:
                        stats['created'] += 1
                    else:
                        stats['updated'] += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing design {design.get('design_no', 'unknown')}: {str(e)}"))
                    logger.error(f"Error in design sync: {str(e)} for design {design.get('design_no', 'unknown')}")
                    stats['failed'] += 1
            
            # Create any missing categories
            if categories:
                self.stdout.write(f"Creating {len(categories)} categories...")
                for cat_name in categories:
                    Category.objects.get_or_create(name=cat_name)
            
            # Output results
            duration = timezone.now() - start_time
            self.stdout.write(self.style.SUCCESS(
                f"Synchronization completed in {duration}\n"
                f"Total designs: {stats['total']}\n"
                f"Created: {stats['created']}\n"
                f"Updated: {stats['updated']}\n"
                f"Skipped: {stats['skipped']}\n"
                f"Failed: {stats['failed']}"
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Synchronization failed: {str(e)}"))
            logger.error(f"Design sync command failed: {str(e)}") 