import os
import requests
from decimal import Decimal
from .models import InventoryItem

logger = logging.getLogger(__name__)

class DevJewelsAPIService:
    """
    Service for interacting with DevJewels external APIs (stock and design endpoints).
    """
    STOCK_API_URL   = os.getenv('DEVJEWELS_STOCK_API')
    DESIGN_API_URL  = os.getenv('DEVJEWELS_DESIGN_API')
    API_CREDENTIALS = {"userid": "admin@eg.com"}

    @classmethod
    def get_stock_data(cls):
        """
        Fetch raw stock data list from the DevJewels stock API.
        """
        resp = requests.get(cls.STOCK_API_URL, params=cls.API_CREDENTIALS)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def get_design_data(cls):
        """
        Fetch design metadata (e.g., images, descriptions) from the DevJewels design API.
        """
        resp = requests.get(cls.DESIGN_API_URL, params=cls.API_CREDENTIALS)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def get_combined_inventory_data(cls):
        """
        Combine stock and design data by matching design_no.
        Returns a list of merged dicts.
        """
        stock_raw  = cls.get_stock_data()
        design_raw = cls.get_design_data()

        # Normalize lists
        stock_list  = json.loads(stock_raw) if isinstance(stock_raw, str) else stock_raw
        design_list = json.loads(design_raw) if isinstance(design_raw, str) else design_raw

        # Index design_by_no
        design_map = {d['design_no']: d for d in design_list if isinstance(d, dict)}
        combined = []
        for entry in stock_list if isinstance(stock_list, list) else []:
            if not isinstance(entry, dict):
                logger.warning("Skipping non-dict stock entry: %r", entry)
                continue
            design_info = design_map.get(entry.get('design_no'), {})
            merged = {**entry, **design_info}
            combined.append(merged)
        return combined


def sync_inventory():
    """
    Fetch & upsert combined stock/design data into the InventoryItem model.
    """
    items = DevJewelsAPIService.get_combined_inventory_data()

    for entry in items:
        InventoryItem.objects.update_or_create(
            job_id=entry.get('job_id'),
            defaults={
                'design_no':     entry.get('design_no'),
                'job_no':        entry.get('job_no'),
                'metal_type':    entry.get('metal_type'),
                'metal_quality': entry.get('metal_quality'),
                'gwt':           Decimal(entry.get('gwt', '0')),
                'nwt':           Decimal(entry.get('nwt', '0')),
                'dwt':           Decimal(entry.get('dwt', '0')),
                'dpcs':          int(entry.get('dpcs', 0)),
                'size':          entry.get('size', ''),
                'memostock':     bool(int(entry.get('memostock', '0'))),
                'totamt':        Decimal(entry.get('totamt', '0')),
                # design API fields (e.g., images)
                'image_list':    entry.get('images', []),  # ensure your model has this field
            }
        )



