# orders/views.py
from django.shortcuts import render
from django.http import HttpResponse
from .utils import get_next_custom_job_no

# Create a simple placeholder view
def order_list(request):
    return HttpResponse("Orders list will be displayed here.")