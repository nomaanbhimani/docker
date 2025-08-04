from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import math

from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationSerializer, CustomerRegistrationResponseSerializer,
    EligibilityCheckSerializer, EligibilityResponseSerializer,
    LoanCreateSerializer, LoanCreateResponseSerializer,
    LoanDetailSerializer, CustomerLoanSerializer
)

def calculate_monthly_installment(loan_amount, interest_rate, tenure):
    """Calculate EMI using compound interest formula"""
    monthly_rate = float(interest_rate) / (12 * 100)
    if monthly_rate == 0:
        return float(loan_amount) / tenure
    
    emi = float(loan_amount) * monthly_rate * (1 + monthly_rate)**tenure / ((1 + monthly_rate)**tenure - 1)
    return round(emi, 2)

def calculate_credit_score(customer):
    """Calculate credit score based on historical data"""
    loans = customer.loans.all()
    
    if not loans.exists():
        return 50  # Default score for new customers
    
    # Check if sum of current loans > approved limit
    current_debt = sum(float(loan.loan_amount) for loan in loans if loan.end_date >= date.today())
    if current_debt > float(customer.approved_limit):
        return 0
    
    score = 0
    total_loans = loans.count()
    
    # 1. Past Loans paid on time (40 points)
    if total_loans > 0:
        total_emis = sum(loan.tenure for loan in loans)
        total_on_time = sum(loan.emis_paid_on_time for loan in loans)
        on_time_ratio = total_on_time / total_emis if total_emis > 0 else 0
        score += min(40, on_time_ratio * 40)
    
    # 2. Number of loans taken (20 points - fewer loans is better)
    if total_loans <= 3:
        score += 20
    elif total_loans <= 6:
        score += 10
    
    # 3. Loan activity in current year (20 points)
    current_year_loans = loans.filter(start_date__year=date.today().year)
    if current_year_loans.count() <= 2:
        score += 20
    elif current_year_loans.count() <= 4:
        score += 10
    
    # 4. Loan approved volume (20 points)
    total_approved = sum(float(loan.loan_amount) for loan in loans)
    approved_limit_float = float(customer.approved_limit)
    if total_approved <= approved_limit_float * 0.5:
        score += 20
    elif total_approved <= approved_limit_float * 0.8:
        score += 10
    
    return min(100, max(0, score))

@api_view(['POST'])
def register_customer(request):
    serializer = CustomerRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        customer = serializer.save()
        response_serializer = CustomerRegistrationResponseSerializer(customer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def check_eligibility(request):
    serializer = EligibilityCheckSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    customer_id = data['customer_id']
    loan_amount = float(data['loan_amount'])  # Convert to float
    interest_rate = float(data['interest_rate'])  # Convert to float
    tenure = data['tenure']
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Calculate credit score
    credit_score = calculate_credit_score(customer)
    
    # Check current EMI burden
    current_loans = customer.loans.filter(end_date__gte=date.today())
    current_emi_sum = sum(float(loan.monthly_repayment) for loan in current_loans)
    
    monthly_installment = calculate_monthly_installment(loan_amount, interest_rate, tenure)
    total_emi = current_emi_sum + monthly_installment
    monthly_salary_float = float(customer.monthly_salary)
    
    # Determine approval and corrected interest rate
    approval = False
    corrected_interest_rate = interest_rate
    
    if total_emi > monthly_salary_float * 0.5:
        approval = False
    elif credit_score > 50:
        approval = True
    elif 30 < credit_score <= 50:
        if interest_rate >= 12:
            approval = True
        else:
            corrected_interest_rate = 12.0
            monthly_installment = calculate_monthly_installment(loan_amount, corrected_interest_rate, tenure)
    elif 10 < credit_score <= 30:
        if interest_rate >= 16:
            approval = True
        else:
            corrected_interest_rate = 16.0
            monthly_installment = calculate_monthly_installment(loan_amount, corrected_interest_rate, tenure)
    else:  # credit_score <= 10
        approval = False
    
    response_data = {
        'customer_id': customer_id,
        'approval': approval,
        'interest_rate': interest_rate,
        'corrected_interest_rate': corrected_interest_rate,
        'tenure': tenure,
        'monthly_installment': monthly_installment
    }
    
    response_serializer = EligibilityResponseSerializer(response_data)
    return Response(response_serializer.data)

@api_view(['POST'])
def create_loan(request):
    serializer = LoanCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    customer_id = data['customer_id']
    loan_amount = float(data['loan_amount'])  # Convert to float
    interest_rate = float(data['interest_rate'])  # Convert to float
    tenure = data['tenure']
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check eligibility (reuse logic from check_eligibility)
    credit_score = calculate_credit_score(customer)
    current_loans = customer.loans.filter(end_date__gte=date.today())
    current_emi_sum = sum(float(loan.monthly_repayment) for loan in current_loans)
    
    monthly_installment = calculate_monthly_installment(loan_amount, interest_rate, tenure)
    total_emi = current_emi_sum + monthly_installment
    monthly_salary_float = float(customer.monthly_salary)
    
    loan_approved = False
    message = ""
    loan_id = None
    
    if total_emi > monthly_salary_float * 0.5:
        message = "Loan not approved: Total EMI exceeds 50% of monthly salary"
    elif credit_score <= 10:
        message = "Loan not approved: Credit score too low"
    elif credit_score > 50:
        loan_approved = True
    elif 30 < credit_score <= 50 and interest_rate >= 12:
        loan_approved = True
    elif 10 < credit_score <= 30 and interest_rate >= 16:
        loan_approved = True
    else:
        message = "Loan not approved: Interest rate too low for credit score"
    
    if loan_approved:
        # Create loan
        start_date = date.today()
        end_date = start_date + relativedelta(months=tenure)
        
        loan = Loan.objects.create(
            customer=customer,
            loan_amount=loan_amount,
            tenure=tenure,
            interest_rate=interest_rate,
            monthly_repayment=monthly_installment,
            start_date=start_date,
            end_date=end_date
        )
        loan_id = loan.loan_id
        message = "Loan approved successfully"
        
        # Update customer's current debt
        customer.current_debt = float(customer.current_debt) + loan_amount
        customer.save()
    
    response_data = {
        'loan_id': loan_id,
        'customer_id': customer_id,
        'loan_approved': loan_approved,
        'message': message,
        'monthly_installment': monthly_installment
    }
    
    response_serializer = LoanCreateResponseSerializer(response_data)
    return Response(response_serializer.data)

@api_view(['GET'])
def view_loan(request, loan_id):
    try:
        loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = LoanDetailSerializer(loan)
    return Response(serializer.data)

@api_view(['GET'])
def view_customer_loans(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    
    loans = customer.loans.filter(end_date__gte=date.today())  # Current loans only
    serializer = CustomerLoanSerializer(loans, many=True)
    return Response(serializer.data)