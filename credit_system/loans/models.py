from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(validators=[MinValueValidator(18)])
    phone_number = models.CharField(max_length=15)
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2)
    approved_limit = models.DecimalField(max_digits=12, decimal_places=2)
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure = models.IntegerField()  # in months
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_repayment = models.DecimalField(max_digits=10, decimal_places=2)
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    
    def __str__(self):
        return f"Loan {self.loan_id} - {self.customer}"
    
    @property
    def repayments_left(self):
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        current_date = date.today()
        if current_date >= self.end_date:
            return 0
        
        # Calculate months remaining
        months_left = (self.end_date.year - current_date.year) * 12 + (self.end_date.month - current_date.month)
        return max(0, months_left)