import re
from .models import OrderItem

def get_next_custom_job_no():
    all_custom = OrderItem.objects.filter(job_no__startswith='custom').values_list('job_no', flat=True)
    max_num = 0
    for job_no in all_custom:
        match = re.match(r'custom(\d+)', job_no)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return f'custom{max_num + 1}'
