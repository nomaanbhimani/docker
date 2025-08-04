from rest_framework import serializers
from .models import Customer, Loan

class CustomerRegistrationSerializer(serializers.ModelSerializer):
    monthly_income = serializers.DecimalField(max_digits=10, decimal_places=2, source='monthly_salary')
    
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'age', 'monthly_income', 'phone_number']
    
    def create(self, validated_data):
        monthly_salary = validated_data['monthly_salary']
        # approved_limit = 36 * monthly_salary (rounded to nearest lakh)
        approved_limit = round(36 * monthly_salary / 100000) * 100000
        
        validated_data['approved_limit'] = approved_limit
        return super().create(validated_data)

class CustomerRegistrationResponseSerializer(serializers.ModelSerializer):
    monthly_income = serializers.DecimalField(max_digits=10, decimal_places=2, source='monthly_salary')
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = ['customer_id', 'name', 'age', 'monthly_income', 'approved_limit', 'phone_number']
    
    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class EligibilityCheckSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()

class EligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2)

class LoanCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()

class LoanCreateResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2)

class CustomerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='customer_id')
    
    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'phone_number', 'age']

class LoanDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2, source='monthly_repayment')
    
    class Meta:
        model = Loan
        fields = ['loan_id', 'customer', 'loan_amount', 'interest_rate', 'monthly_installment', 'tenure']

class CustomerLoanSerializer(serializers.ModelSerializer):
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2, source='monthly_repayment')
    
    class Meta:
        model = Loan
        fields = ['loan_id', 'loan_amount', 'interest_rate', 'monthly_installment', 'repayments_left']