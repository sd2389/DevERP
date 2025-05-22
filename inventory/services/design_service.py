# inventory/services/design_service.py

import logging
from datetime import datetime
import requests
from django.conf import settings
from inventory.models import Design

logger = logging.getLogger('inventory')

class DesignSyncService:
    """Service for synchronizing designs with external API"""
    
    API_DESIGN_URL = "https://admin.devjewels.com/mobileapi/api_design.php"
    USER_ID = "admin@eg.com"
    
    @classmethod
    def sync_designs(cls, force_update=False):
        """
        Fetch designs from API and update local database
        
        Args:
            force_update: If True, update all designs regardless of changes
            
        Returns:
            dict: Sync statistics
        """
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0
        }
        
        try:
            # Fetch designs from API
            logger.info("Fetching designs from API")
            response = requests.post(
                cls.API_DESIGN_URL, 
                json={'userid': cls.USER_ID}, 
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response
            design_data = response.json().get('data', [])
            stats['total'] = len(design_data)
            
            # Get existing designs for bulk comparison
            existing_designs = {d.design_no: d for d in Design.objects.all()}
            
            # Process each design
            for design in design_data:
                design_no = design.get('design_no')
                
                if not design_no:
                    logger.warning("Skipping design with no design_no")
                    stats['skipped'] += 1
                    continue
                
                try:
                    # Check if design exists
                    if design_no in existing_designs:
                        # Update existing design
                        existing = existing_designs[design_no]
                        
                        # Only update if force_update is True or there are changes
                        # We don't update is_active as that's controlled by admins
                        if force_update or cls._has_changes(existing, design):
                            existing.category = design.get('category', '').title()
                            existing.subcategory = design.get('subcategory', '')
                            existing.description = design.get('description', '')
                            existing.image_base_path = cls._get_image_path(design)
                            existing.save()
                            stats['updated'] += 1
                        else:
                            stats['skipped'] += 1
                    else:
                        # Create new design
                        Design.objects.create(
                            design_no=design_no,
                            is_active=True,  # New designs are active by default
                            category=design.get('category', '').title(),
                            subcategory=design.get('subcategory', ''),
                            description=design.get('description', ''),
                            image_base_path=cls._get_image_path(design)
                        )
                        stats['created'] += 1
                except Exception as e:
                    logger.error(f"Error processing design {design_no}: {str(e)}")
                    stats['failed'] += 1
            
            logger.info(f"Design sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Design sync failed: {str(e)}")
            raise
    
    @classmethod
    def _has_changes(cls, existing_design, api_design):
        """Check if API data differs from existing design"""
        return (
            existing_design.category != api_design.get('category', '').title() or
            existing_design.subcategory != api_design.get('subcategory', '') or
            existing_design.description != api_design.get('description', '') or
            existing_design.image_base_path != cls._get_image_path(api_design)
        )
    
    @classmethod
    def _get_image_path(cls, design):
        """Extract or construct image path from design data"""
        # If API provides image path, use it
        if 'image_path' in design:
            return design['image_path']
        
        # Otherwise construct based on design_no
        design_no = design.get('design_no', '')
        return f"https://dev-jewels.s3.us-east-2.amazonaws.com/products/{design_no}"