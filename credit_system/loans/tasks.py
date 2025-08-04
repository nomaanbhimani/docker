from celery import shared_task
import pandas as pd
from django.conf import settings
from .models import Customer, Loan
from datetime import datetime
import os

@shared_task
def load_customer_data():
    """Load customer data from Excel file"""
    file_path = os.path.join(settings.BASE_DIR, 'data', 'customer_data.xlsx')
    
    try:
        df = pd.read_excel(file_path)
        
        print(f"Loading {len(df)} customers...")
        
        loaded_count = 0
        for _, row in df.iterrows():
            try:
                # Use update_or_create to handle existing IDs
                customer, created = Customer.objects.update_or_create(
                    customer_id=int(row['customer_id']),
                    defaults={
                        'first_name': str(row['first_name']),
                        'last_name': str(row['last_name']),
                        'age': int(row['age']),
                        'phone_number': str(row['phone_number']),
                        'monthly_salary': float(row['monthly_salary']),
                        'approved_limit': float(row['approved_limit']),
                        'current_debt': 0  # Default since not in your Excel
                    }
                )
                if created:
                    loaded_count += 1
                    
                # Update the sequence to avoid conflicts with new registrations
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT setval(pg_get_serial_sequence('loans_customer', 'customer_id'), "
                        "(SELECT MAX(customer_id) FROM loans_customer) + 1, false)"
                    )
                    
            except Exception as row_error:
                print(f"Error processing customer row {loaded_count + 1}: {row_error}")
                continue
        
        return f"Successfully loaded/updated {loaded_count} customers out of {len(df)} rows"
    
    except Exception as e:
        return f"Error loading customer data: {str(e)}"

@shared_task
def load_loan_data():
    """Load loan data from Excel file"""
    file_path = os.path.join(settings.BASE_DIR, 'data', 'loan_data.xlsx')
    
    try:
        df = pd.read_excel(file_path)
        
        print(f"Loading {len(df)} loans...")
        
        # First, check if we need to add customer_id column
        if 'customer_id' not in df.columns:
            return "Error: loan_data.xlsx is missing customer_id column. Please add it or provide the customer mapping."
        
        loaded_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                # Get customer
                customer_id = int(row['customer_id'])
                try:
                    customer = Customer.objects.get(customer_id=customer_id)
                except Customer.DoesNotExist:
                    print(f"Customer {customer_id} not found, skipping loan {row['loan_id']}")
                    skipped_count += 1
                    continue
                
                # Parse dates
                start_date = pd.to_datetime(row['date_of_approval']).date()
                end_date = pd.to_datetime(row['end_date']).date()
                
                Loan.objects.get_or_create(
                    loan_id=int(row['loan_id']),
                    defaults={
                        'customer': customer,
                        'loan_amount': float(row['loan_amount']),
                        'tenure': int(row['tenure']),
                        'interest_rate': float(row['interest_rate']),
                        'monthly_repayment': float(row['monthly_payment']),  # Your column is monthly_payment
                        'emis_paid_on_time': int(row['emis_paid_on_time']),
                        'start_date': start_date,  # Using date_of_approval as start_date
                        'end_date': end_date,
                    }
                )
                loaded_count += 1
                
            except Exception as row_error:
                print(f"Error processing loan row: {row_error}")
                skipped_count += 1
                continue
        
        return f"Successfully loaded {loaded_count} loans, skipped {skipped_count} loans out of {len(df)} total rows"
    
    except Exception as e:
        return f"Error loading loan data: {str(e)}"