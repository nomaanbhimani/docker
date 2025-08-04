from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_customer, name='register'),
    path('check-eligibility/', views.check_eligibility, name='check-eligibility'),
    path('create-loan/', views.create_loan, name='create-loan'),
    path('view-loan/<int:loan_id>/', views.view_loan, name='view-loan'),
    path('view-loans/<int:customer_id>/', views.view_customer_loans, name='view-customer-loans'),
]