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
                    
                    # Get or prepare new design
                    if design_no in existing_designs:
                        # Update existing design
                        d = existing_designs[design_no]
                        
                        # Check if update is needed
                        need_update = (
                            force_update or
                            d.category != category_name or
                            (design.get('subcategory', '') and d.subcategory != design.get('subcategory', '')) or
                            (design.get('description', '') and d.description != design.get('description', ''))
                        )
                        
                        if need_update:
                            d.category = category_name
                            d.subcategory = design.get('subcategory', '')
                            d.description = design.get('description', '')
                            d.image_base_path = f"https://dev-jewels.s3.us-east-2.amazonaws.com/products/{design_no}"
                            d.last_synced = timezone.now()
                            d.save()
                            stats['updated'] += 1
                        else:
                            stats['skipped'] += 1
                    else:
                        # Create new design
                        Design.objects.create(
                            design_no=design_no,
                            is_active=set_active,
                            category=category_name,
                            subcategory=design.get('subcategory', ''),
                            description=design.get('titleline', ''),
                            image_base_path=f"https://dev-jewels.s3.us-east-2.amazonaws.com/products/{design_no}",
                            created_at=timezone.now(),
                            last_synced=timezone.now()
                        )
                        stats['created'] += 1
                        
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