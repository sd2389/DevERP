# orders/views.py
from django.shortcuts import render
from django.http import HttpResponse

# Create a simple placeholder view
def order_list(request):
    return HttpResponse("Orders list will be displayed here.")