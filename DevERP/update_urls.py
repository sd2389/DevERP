# update_urls.py - Save this script at the root of your project
import os
import re

def update_template_urls(directory):
    """Update all URL patterns in HTML templates to include namespaces."""
    
    # URLs to replace: url_name -> namespace:url_name
    url_patterns = {
        "'inventory'": "'inventory:inventory'",
        "'wishlist'": "'inventory:wishlist'",
        "'requests'": "'inventory:requests'",
        "'cart'": "'inventory:cart'",
        "'orders'": "'inventory:orders'",
        "'custom_orders'": "'inventory:custom_orders'",
        '"inventory"': '"inventory:inventory"',
        '"wishlist"': '"inventory:wishlist"',
        '"requests"': '"inventory:requests"',
        '"cart"': '"inventory:cart"',
        '"orders"': '"inventory:orders"',
        '"custom_orders"': '"inventory:custom_orders"',
    }
    
    # Process all HTML files in the directory
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.html'):
                file_path = os.path.join(root, filename)
                print(f"Processing: {file_path}")
                
                # Read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for URL patterns
                original_content = content
                for pattern, replacement in url_patterns.items():
                    # Only replace patterns wrapped in {% url ... %} tags
                    content = re.sub(r'{%\s+url\s+' + pattern + r'\s+%}', 
                                     r'{% url ' + replacement + r' %}', 
                                     content)
                
                # If changes were made, write back to file
                if content != original_content:
                    print(f"  - Updated URLs in {filename}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    print(f"  - No changes needed in {filename}")

if __name__ == "__main__":
    # Update templates in the inventory app
    update_template_urls("inventory/templates")
    
    # Also update templates in the root templates directory if it exists
    if os.path.exists("templates"):
        update_template_urls("templates")