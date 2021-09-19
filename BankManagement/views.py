from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponse
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from BankManagement.models import *
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from BankManagement.serializers import *
from rest_framework.permissions import AllowAny
import datetime
import json
import re
# Create your views here.

## 基本信息
class BankViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Bank.objects.all()
    serializer_class = BankSerializer

class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

### 客户管理
class CustomerViewSet(viewsets.ViewSet):
    '''
    Viewset for customer
    '''
    permission_classes = (AllowAny,)

    def list(self, request):  ## 查
        queryset = Customer.objects.all()
        serializer = CustomerSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):  ## 增
        serializer = CustomerSerializer(data=request.data)
        Cname = request.data.get("Customer_Name")
        if re.match(r'^[a-zA-Z\u4e00-\u9fa5]+$' ,Cname ) :
            a = 0;
        else:
            return Response({
                'status': 'Bad request',
                'message': 'Invalid data',
            }, status = 401)

        if serializer.is_valid():
            Customer.objects.create(**serializer.validated_data)
            return Response({
                'status': 'Success',
                'message': 'Create new Customer Successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'status': 'Bad request',
                'message': 'Invalid data',
            }, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None):  ## 改
        if not request.data.get('Customer_ID'):
            return Response({
                'status': 'Failed',
                'message': 'Customer_ID not found'}, status= 403)
        queryset = Customer.objects.filter(pk=pk)
        if not queryset.exists():
            return Response({
                'status': 'Failed',
                'message': 'Customer not exist'}, status=400 )
        if pk != request.data.get("Customer_ID"):
            return Response({
                'status': 'Failed',
                'message': 'Could not change Customer_ID'}, status=401)
        if request.data.get('Employee_ID') and not Employee.objects.filter(pk=request.data.get('Employee_ID')).exists():
            return Response({
                'status': 'Failed',
                'message': 'Employee_ID not found'}, status= 402)
        with transaction.atomic():
            queryset.update(
                Customer_Name=request.data.get("Customer_Name") if request.data.get("Customer_Name") else queryset[
                    0].Customer_Name,
                Customer_Phone_Number=request.data.get("Customer_Phone_Number") if request.data.get(
                    "Customer_Phone_Number") else queryset[0].Customer_Phone_Number,
                Customer_Address=request.data.get("Customer_Address") if request.data.get("Customer_Address") else
                queryset[0].Customer_Address,
                Contact_Person_Name=request.data.get("Contact_Person_Name") if request.data.get(
                    "Contact_Person_Name") else queryset[0].Contact_Person_Name,
                Contact_Person_Phone_Number=request.data.get("Contact_Person_Phone_Number") if request.data.get(
                    "Contact_Person_Phone_Number") else queryset[0].Contact_Person_Phone_Number,
                Contact_Person_Email=request.data.get("Contact_Person_Email") if request.data.get(
                    "Contact_Person_Email") else queryset[0].Contact_Person_Email,
                Contact_Person_Relationship=request.data.get("Contact_Person_Relationship") if request.data.get(
                    "Contact_Person_Relationship") else queryset[0].Contact_Person_Relationship,
                Employee_ID=request.data.get("Employee_ID") if request.data.get("Employee_ID") else queryset[
                    0].Employee_ID
            )
        return Response({
            'status': 'Success',
            'message': 'Update data Successfully'}, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):  ## 删
        queryset = Customer.objects.all()
        customer = get_object_or_404(queryset, pk=pk)
        queryset0 = CustomerToLoan.objects.filter(Customer_ID = customer.Customer_ID)
        queryset1 = CustomerToCA.objects.filter(Customer_ID = customer.Customer_ID)
        queryset2 = CustomerToSA.objects.filter(Customer_ID=customer.Customer_ID)
        if queryset1.exists() or queryset2.exists() or queryset0.exists() :
            return Response({
                'status': 'Failed',
                'message': 'Could not delete .because of the unfinished tran'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                customer.delete()
            except:
                return Response({
                    'status': 'Failed',
                    'message': 'Could not delete'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'status': 'Success',
            'message': 'Delete data Successfully'}, status=200)

## 支票账户管理
class CheckAccountViewSet(viewsets.ModelViewSet):
    '''
    Viewset for check account
    '''
    permission_classes = (AllowAny,)
    def list(self, request):
        queryset1 = CheckAccount.objects.all()
        queryset2 = CustomerToCA.objects.all()
        serializer1 = CheckAccountSerializer(queryset1, many=True)
        serializer2 = CustomerToCASerializer(queryset2, many=True)
        ##  处理customer 与CAccount_ID  的对应
        CA_IDtoC_ID = {}
        for dic in serializer2.data: ##OrderedDict([('CAccount_ID', 'CA0000'), ('Customer_ID', 'C0000'), ('CAccount_Open_Bank_Name', 'bank0'), ('CAccount_Last_Access_Date', ' ')])
            if dic['CAccount_ID'] in CA_IDtoC_ID:
                CA_IDtoC_ID[dic['CAccount_ID']] = CA_IDtoC_ID[dic['CAccount_ID']] +'&' + dic['Customer_ID']
            else:
                CA_IDtoC_ID[dic['CAccount_ID']] = dic['Customer_ID']
        ## 将 Customer 加到 输出序列
        for entry in serializer1.data: ##OrderedDict([('CAccount_ID', 'CA0000'), ('CAccount_Balance', '0'), ('CAccount_Open_Date','')),('CAccount_Overdraft','20'), ('CAccount_Open_Bank_Name','')])
            entry['Customer_ID'] = CA_IDtoC_ID[entry['CAccount_ID']]
        return Response(serializer1.data)

    @transaction.atomic
    def create(self, request):        ## 开户
        checkaccount = request.data.copy()
        
        try:   ## 取出Customer_ID ,  就是账户类
            checkaccount.pop('Customer_ID')
        except KeyError as e:
            return Response({
                'status': 'Failed',
                'message': 'Customer_ID is required'}, status=399)

        customer_to_ca = request.data.copy()
        try:  ## 构造Customer_to_ca类
            customer_to_ca.pop('CAccount_Balance')
            customer_to_ca.pop('CAccount_Overdraft')
        except KeyError as e:
            return Response({
                'status': 'Failed',
                'message': 'More information is required'}, status=398)
        ## 检查客户 是不是存在
        queryset0 = Customer.objects.filter(pk=request.data.get('Customer_ID'))
        if not queryset0.exists():
            return Response({
                'status': 'Failed',
                'message': 'Customer not exist'}, status=397)
        ## 检查一个客户一个银行内是否有账号
        queryset1 = CustomerToCA.objects.filter(Customer_ID=request.data.get('Customer_ID'),CAccount_Open_Bank_Name=request.data.get('CAccount_Open_Bank_Name') )
        if queryset1.exists():
            return Response({
                'status': 'Failed',
                'message': 'Customer not exist'}, status=396)

        ##   补充其他 约束情况 ##
        ## 数据库操作，事务
        try:
            with transaction.atomic():    ## 数据库操作，事务
                checkaccount['CAccount_Open_Date'] = datetime.datetime.now()  ## 准备 checkaccount
                customer_to_ca['CAccount_Last_Access_Date'] = datetime.datetime.now() ## 准备 customer_to_ca
                ca_serializer = CheckAccountSerializer(data=checkaccount)
                ca_to_customer_serializer = CustomerToCASerializer(data=customer_to_ca)
                if ca_serializer.is_valid():      ## 开户信息 符合要求
                    CheckAccount.objects.create(**ca_serializer.validated_data)
                    #ca_to_customer_serializer = CustomerToCASerializer(data=customer_to_ca)
                if ca_to_customer_serializer.is_valid():
                    CustomerToCA.objects.create(**ca_to_customer_serializer.validated_data)
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'Success',
            'message': 'Create new Check Account Successfully'}, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None):
        #Only balance and overdraft are allowed to modify
        queryset = CheckAccount.objects.filter(pk=pk)
        # 修改的账户不存在
        if not queryset.exists():
            return Response({
                'status': 'Failed',
                'message': 'Check Account not exist'}, status=status.HTTP_400_BAD_REQUEST)
        # if pk != request.data.get("CAccount_ID"):
        #     return Response({
        #         'status': 'Failed',
        #         'message': 'Could not change CAccount_ID'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                queryset.update(
                    CAccount_ID=pk,
                    CAccount_Balance=request.data.get('CAccount_Balance') if request.data.get('CAccount_Balance') else queryset[0].CAccount_Balance,
                    CAccount_Overdraft=request.data.get('CAccount_Overdraft') if request.data.get('CAccount_Overdraft') else queryset[0].CAccount_Overdraft,
                )
                ## 伴随 CustomtoCA也要更新
                queryset = CustomerToCA.objects.filter(CAccount_ID=pk)
                queryset.update(
                    CAccount_Last_Access_Date=datetime.datetime.now()
                )
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'Success',
            'message': 'Update Check Account Successfully'}, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, pk=None):
        deleteInfo = request.data.copy()
        ## 账户不存在则异常 .
        queryset1 = CheckAccount.objects.all()
        checkaccount = get_object_or_404(queryset1, pk=pk)
        queryset2 = CustomerToCA.objects.all()
        customer_to_ca = get_list_or_404(queryset2, CAccount_ID=pk,Customer_ID = deleteInfo['Customer_ID'])
        try: ## 先删除 Cusromer to CA
            CustomerToCA.objects.filter(CAccount_ID = deleteInfo['CAccount_ID'],Customer_ID = deleteInfo['Customer_ID']).delete()
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

        queryset3 = CustomerToCA.objects.filter(CAccount_ID = deleteInfo['CAccount_ID'])
        if not queryset3.exists():
            try:  ## 先删除 Cusromer to CA
             checkaccount.delete()
            except IntegrityError as e:
                return Response({
                    'status': 'Bad request',
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
        'status': 'Success',
        'message': 'Delete Check Account Successfully'}, status=status.HTTP_200_OK)

class CustomerToCAViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = CustomerToCA.objects.all()
    serializer_class = CustomerToCASerializer

## 存储账户管理
class SavingAccountViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    def list(self, request):
        queryset1 = SavingAccount.objects.all()
        queryset2 = CustomerToSA.objects.all()
        serializer1 = SavingAccountSerializer(queryset1, many=True)
        serializer2 = CustomerToSASerializer(queryset2, many=True)
        ##  处理customer 与CAccount_ID  的对应
        SA_IDtoC_ID = {}
        for dic in serializer2.data: ##OrderedDict([('CAccount_ID', 'CA0000'), ('Customer_ID', 'C0000'), ('CAccount_Open_Bank_Name', 'bank0'), ('CAccount_Last_Access_Date', ' ')])
            if dic['SAccount_ID'] in SA_IDtoC_ID:
                SA_IDtoC_ID[dic['SAccount_ID']] = SA_IDtoC_ID[dic['SAccount_ID']] +'&' + dic['Customer_ID']
            else:
                SA_IDtoC_ID[dic['SAccount_ID']] = dic['Customer_ID']
        ## 将 Customer 加到 输出序列
        for entry in serializer1.data: ##OrderedDict([('CAccount_ID', 'CA0000'), ('CAccount_Balance', '0'), ('CAccount_Open_Date','')),('CAccount_Overdraft','20'), ('CAccount_Open_Bank_Name','')])
            entry['Customer_ID'] = SA_IDtoC_ID[entry['SAccount_ID']]
        return Response(serializer1.data)

    def create(self, request):
        savingaccount = request.data.copy()
        try:
            savingaccount.pop('Customer_ID')
        except KeyError as e:
            return Response({
                'status': 'Failed',
                'message': 'Customer_ID is required'}, status=399)
        try:
            sa_to_customer = request.data.copy()
            sa_to_customer.pop('SAccount_Balance')
            sa_to_customer.pop('SAccount_Interest_Rate')
            sa_to_customer.pop('SAccount_Currency_Type')
        except KeyError as e:
            return Response({
                'status': 'Failed',
                'message': 'More information is required'}, status=398)

        ## 检查客户是否存在
        queryset = Customer.objects.filter(pk=request.data.get('Customer_ID'))
        if not queryset.exists():
            return Response({
                'status': 'Failed',
                'message': 'Customer not exist'}, status=397)
        ## 检查一个客户一个银行内是否有账号

        queryset1 = CustomerToSA.objects.filter(Customer_ID=request.data.get('Customer_ID'),SAccount_Open_Bank_Name=request.data.get('SAccount_Open_Bank_Name') )
        if queryset1.exists():
            return Response({
                'status': 'Failed',
                'message': 'Customer not exist'}, status=396)
        ##   补充其他 约束情况 ##

        try:
            with transaction.atomic():
                savingaccount['SAccount_Open_Date'] = datetime.datetime.now()
                sa_serializer = SavingAccountSerializer(data=savingaccount)
                sa_to_customer['SAccount_Last_Access_Date'] = datetime.datetime.now()
                sa_to_customer_serializer = CustomerToSASerializer(data=sa_to_customer)
                if sa_serializer.is_valid():
                    SavingAccount.objects.create(**sa_serializer.validated_data)
                if sa_to_customer_serializer.is_valid():
                    CustomerToSA.objects.create( **sa_to_customer_serializer.validated_data)
                else:
                    return Response({
                        'status': 'Bad request',
                        'message': 'conflicts',
                    }, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'Success',
            'message': 'Create new Saving Account Successfully'}, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None):
        # Only balance and overdraft are allowed to modify
        queryset = SavingAccount.objects.filter(pk=pk)
        if not queryset.exists():
            return Response({
                'status': 'Failed',
                'message': 'Check Account not exist'}, status=status.HTTP_400_BAD_REQUEST)
        if pk != request.data.get("SAccount_ID"):
            return Response({
                'status': 'Failed',
                'message': 'Could not change SAccount_ID'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                queryset.update(
                    SAccount_ID=pk,
                    SAccount_Balance=request.data.get('SAccount_Balance') if request.data.get('SAccount_Balance') else queryset[0].SAccount_Balance,
                    SAccount_Interest_Rate=request.data.get('SAccount_Interest_Rate') if request.data.get('SAccount_Interest_Rate') else queryset[0].SAccount_Interest_Rate,
                    SAccount_Currency_Type=request.data.get('SAccount_Currency_Type') if request.data.get('SAccount_Currency_Type') else queryset[0].SAccount_Currency_Type,
                )
                queryset = CustomerToSA.objects.filter(SAccount_ID=pk)
                queryset.update(
                    SAccount_Last_Access_Date=datetime.datetime.now()
                )
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'Success',
            'message': 'Update Check Account Successfully'}, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, pk=None):
        deleteInfo = request.data.copy()
        queryset1 = SavingAccount.objects.all()
        savingaccount = get_object_or_404(queryset1, SAccount_ID =deleteInfo['SAccount_ID'])
        queryset2 = CustomerToSA.objects.all()
        customer_to_sa = get_list_or_404(queryset2, SAccount_ID=deleteInfo['SAccount_ID'] ,Customer_ID = deleteInfo['Customer_ID'])
        try: ## 先删除 Cusromer to CA
            CustomerToSA.objects.filter(SAccount_ID = deleteInfo['SAccount_ID'],Customer_ID = deleteInfo['Customer_ID']).delete()
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

        queryset3 = CustomerToSA.objects.filter(SAccount_ID = deleteInfo['SAccount_ID'])
        if not queryset3.exists():
            try:  ## 先删除 Cusromer to CA
             savingaccount.delete()
            except IntegrityError as e:
                return Response({
                    'status': 'Bad request',
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'status': 'Success',
            'message': 'Delete Saving Account Successfully'}, status=status.HTTP_200_OK)

class CustomerToSAViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = CustomerToSA.objects.all()
    serializer_class = CustomerToSASerializer

# ## 贷款管理
# class LoanViewSet(viewsets.ViewSet):
#     permission_classes = (AllowAny,)
#
#     def list(self, request):
#         queryset1 = Loan.objects.all()
#         queryset2 = CustomerToLoan.objects.all()
#         serializer1 = LoanSerializer(queryset1, many=True)
#         serializer2 = CustomerToLoanSerializer(queryset2, many=True)
#         # ##  处理customer 与CAccount_ID  的对应
#         # Loan_IDtoC_ID = {}
#         # for dic in serializer1.data:  ##OrderedDict([('CAccount_ID', 'CA0000'), ('Customer_ID', 'C0000'), ('CAccount_Open_Bank_Name', 'bank0'), ('CAccount_Last_Access_Date', ' ')])
#         #     if dic['Loan_ID'] in Loan_IDtoC_ID:
#         #         Loan_IDtoC_ID[dic['Loan_ID']] = Loan_IDtoC_ID[dic['Loan_ID']] + '&' + dic['Customer_ID']
#         #     else:
#         #         Loan_IDtoC_ID[dic['Loan_ID']] = dic['Customer_ID']
#         # ## 将 Customer 加到 输出序列
#         # for entry in serializer2.data:  ##OrderedDict([('CAccount_ID', 'CA0000'), ('CAccount_Balance', '0'), ('CAccount_Open_Date','')),('CAccount_Overdraft','20'), ('CAccount_Open_Bank_Name','')])
#         #     entry['Customer_ID'] = Loan_IDtoC_ID[entry['Loan_ID']]
#         return Response(serializer2.data)
#
#     @transaction.atomic
#     def create(self, request):
#         loan = request.data.copy()
#
#         try:
#             loan.pop('Customer_ID')
#         except KeyError as e:
#             return Response({
#                 'status': 'Failed',
#                 'message': 'Customer_ID is required'}, status=status.HTTP_400_BAD_REQUEST)
#
#         customer_to_loan = request.data.copy()
#         try:
#             customer_to_loan.pop('Loan_Total')
#             customer_to_loan.pop('Loan_Status')
#             customer_to_loan.pop('Loan_Bank_Name')
#         except KeyError as e:
#             return Response({
#                 'status': 'Failed',
#                 'message': 'More information is required'}, status=status.HTTP_400_BAD_REQUEST)
#
#         queryset = Customer.objects.filter(pk=request.data.get('Customer_ID'))
#         if not queryset.exists():
#             return Response({
#                 'status': 'Failed',
#                 'message': 'Customer not exist'}, status=status.HTTP_400_BAD_REQUEST)
#         serializer = LoanSerializer(data=loan)
#         customer_to_loan_serializer = CustomerToLoanSerializer(data=customer_to_loan)
#         try:
#             with transaction.atomic():
#                 if serializer.is_valid():
#                     Loan.objects.create(**serializer.validated_data)
#                 #customer_to_loan_serializer = CustomerToLoanSerializer(data=customer_to_loan)
#                 if customer_to_loan_serializer.is_valid():
#                     CustomerToLoan.objects.create(**customer_to_loan_serializer.validated_data)
#         except IntegrityError as e:
#             return Response({
#                 'status': 'Bad request',
#                 'message': str(e),
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         return Response({
#             'status': 'Success',
#             'message': 'Create new Loan Successfully'},
#             status=status.HTTP_201_CREATED)
#
#     def update(self, request, pk=None):
#         return Response({
#             'status': 'Bad request',
#             'message': 'Loan is not allowed to modify',
#         }, status=status.HTTP_400_BAD_REQUEST)
#
#     def retrieve(self, request, pk=None):
#         queryset = Loan.objects.all()
#         loan = get_object_or_404(queryset, pk=pk)
#         serializer = LoanSerializer(loan)
#         return Response(serializer.data)
#
#     @transaction.atomic
#     def destroy(self, request, pk=None):
#         queryset = Loan.objects.all()
#         loan = get_object_or_404(queryset, pk=pk)
#         queryset = CustomerToLoan.objects.all()
#         customer_to_loan = get_list_or_404(queryset, Loan_ID=pk)
#         if loan.Loan_Status == '1':
#             return Response({
#                 'status': 'Bad request',
#                 'message': 'A loan record in the issuing state is not allowed to be deleted',
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             with transaction.atomic():
#                 for obj in customer_to_loan:
#                     obj.delete()
#                 loan.delete()
#         except IntegrityError as e:
#             return Response({
#                 'status': 'Bad request',
#                 'message': str(e),
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         return Response({
#             'status': 'Success',
#             'message': 'Delete Loan Successfully'}, status=status.HTTP_200_OK)
#

class LoanViewSet(viewsets.ViewSet):

    permission_classes = (AllowAny,)

    def list(self, request):
        queryset = Loan.objects.all()
        serializer = LoanSerializer(queryset, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request):
        loan = request.data.copy()
        queryset = Loan.objects.filter(pk=request.data.get('Loan_ID'))
        if queryset.exists():
            return Response({
                'status': 'Failed',
                'message': 'Loan allready exist'}, status=399)
        serializer = LoanSerializer(data=loan)
        if request.data.get("Loan_Status") != '0':
            return Response({
                'status': 'Failed',
                'message': 'wrong initial status'}, status=398)
        try:
            with transaction.atomic():
                if serializer.is_valid():
                    Loan.objects.create(**serializer.validated_data)
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'status': 'Success',
            'message': 'Create new Loan Successfully'},
            status=status.HTTP_201_CREATED)

    @transaction.atomic
    def destroy(self, request, pk=None):
        queryset = Loan.objects.all()
        loan = get_object_or_404(queryset, pk=pk)
        queryset = LoanRelease.objects.all()
        if loan.Loan_Status == '1':
            return Response({
                'status': 'Bad request',
                'message': 'A loan record in the issuing state is not allowed to be deleted',
            }, status=399)
        try:
            with transaction.atomic():
                if not queryset.exists():
                    loanrelease = get_list_or_404(queryset, Loan_ID=pk)
                    for obj in loanrelease:
                        obj.delete()
                loan.delete()
        except IntegrityError as e:
            return Response({
                'status': 'Bad request',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'Success',
            'message': 'Delete Loan Successfully'}, status=status.HTTP_200_OK)

class CustomerToLoanViewSet(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    queryset = CustomerToLoan.objects.all()
    serializer_class = CustomerToLoanSerializer

class LoanReleaseViewSet(viewsets.ViewSet):
    '''
    Viewset for loan release
    '''
    permission_classes = (AllowAny,)
    
    def list(self, request):
        queryset = LoanRelease.objects.all()
        serializer = LoanReleaseSerializer(queryset, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request):
        ## 发放的贷款要 存在 ，且未结束
        loan = Loan.objects.filter(pk=request.data.get('Loan_ID'))
        if not loan.exists():
            return Response({
                'status': 'Failed',
                'message': 'Loan not exist'}, status=399)
        if loan.get().Loan_Status == '2':
            return Response({
                'status': 'Failed',
                'message': 'Loan is finished'}, status=398)

        queryset = LoanRelease.objects.filter(Loan_ID=request.data.get('Loan_ID'))
        loan_amount = sum([q.Loan_Release_Amount for q in queryset])

        ## 贷款量不能超过
        if float(loan_amount) + float(request.data.get('Loan_Release_Amount')) > float(loan.get().Loan_Total):
            return Response({
                'status': 'Failed',
                'message': 'Loan release is more than total amount'}, status=397)

        newrequest = request.data.copy()
        newrequest['Loan_Release_Date'] = datetime.datetime.now()
        serializer = LoanReleaseSerializer(data=newrequest)
        
        try:
            with transaction.atomic():
                if serializer.is_valid():
                    if not LoanRelease.objects.create(**serializer.validated_data):
                        return Response({
                            'status': 'Bad request',
                            'message': 'Invalid data',
                        }, status=status.HTTP_400_BAD_REQUEST)
                    queryset = Loan.objects.filter(pk=request.data.get('Loan_ID'))
                    if float(loan_amount) + float(request.data.get('Loan_Release_Amount')) == float(loan.get().Loan_Total):
                        queryset.update(Loan_Status='2')
                    else:
                        queryset.update(Loan_Status='1')
                else:
                    return Response({
                        'status': 'Bad request',
                        'message': 'Invalid data',
                    }, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:       
            return Response({
                'status': 'Bad request',
                'message': 'Invalid data',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'Success',
            'message': 'Create new Loan Release Successfully'},
            status=status.HTTP_201_CREATED)



class StatisticalDataViewSet(viewsets.ViewSet):
    '''
    Viewset for statistical data
    '''
    permission_classes = (AllowAny,)

    def list(self, request):
        bank_set = Bank.objects.all()   #获得银行数组
        time_list = []
        for bank in bank_set:  # 获得每个行的 存储账户
            saving_account_set = SavingAccount.objects.filter(SAccount_Open_Bank_Name=bank.Bank_Name)
            overall_balance = 0.00
            for sa in saving_account_set:  # 获取每个存储账户的 开户时间
                time_list.append(sa.SAccount_Open_Date)
                overall_balance += float(sa.SAccount_Balance)
        start_time = min(time_list)
        now_time = datetime.datetime.now()

        # Process year
        bank_year_data = []
        bank_quarter_data = []
        bank_month_data = []
        quarter_range = [[1, 3], [4, 6], [7, 9], [10, 12]]
        for bank in bank_set: #对银行遍历
            tmp = {}
            for year in range(start_time.year, now_time.year + 1): # 对年遍历
                saving_account_set = SavingAccount.objects.filter(SAccount_Open_Bank_Name=bank.Bank_Name) # 获得银行的所有储蓄 记录
                loan_set = Loan.objects.filter(Loan_Bank_Name=bank.Bank_Name) # 获得银行的所有贷款记录
                overall_balance = 0.00
                overall_loan = 0.00
                overall_customer = 0
                for sa in saving_account_set:         # 对每个记录
                    if sa.SAccount_Open_Date.year == year:
                        overall_balance += float(sa.SAccount_Balance)
                        overall_customer += 1
                for ln in loan_set:  # 一个银行的贷款  ， 确定银行
                    release_set = LoanRelease.objects.filter(Loan_ID=ln.Loan_ID)  #该贷款发放的量  ，  确定时间
                    for release in release_set:
                        if release.Loan_Release_Date.year == year:
                            overall_loan += float(release.Loan_Release_Amount)
                            overall_customer += 1
                tmp[str(year)] = [overall_balance, overall_loan, overall_customer]
            bank_year_data.append(tmp)
        # print(bank_year_data)

        # Process quarter
        for bank in bank_set:
            tmp = {}
            for year in range(start_time.year, now_time.year + 1):
                for quarter in range(1, 5):
                    saving_account_set = SavingAccount.objects.filter(SAccount_Open_Bank_Name=bank.Bank_Name)
                    loan_set = Loan.objects.filter(Loan_Bank_Name=bank.Bank_Name)
                    overall_balance = 0.00
                    overall_loan = 0.00
                    overall_customer = 0
                    for sa in saving_account_set:
                        if sa.SAccount_Open_Date.year == year and quarter_range[quarter-1][0] <= sa.SAccount_Open_Date.month <= quarter_range [quarter-1][1]:
                            overall_balance += float(sa.SAccount_Balance)
                            overall_customer += 1
                    for ln in loan_set:
                        release_set = LoanRelease.objects.filter(Loan_ID=ln.Loan_ID)
                        for release in release_set:
                            if release.Loan_Release_Date.year == year and quarter_range[quarter-1][0] <= release.Loan_Release_Date.month <= quarter_range [quarter-1][1]:
                                overall_loan += float(release.Loan_Release_Amount)
                                overall_customer += 1
                    tmp[str(year) + "-Q" + str(quarter)] = [overall_balance, overall_loan, overall_customer]
            bank_quarter_data.append(tmp)
        # print(bank_quarter_data)

        # Process month
        for bank in bank_set: # 确定银行
            tmp = {}
            for year in range(start_time.year, now_time.year + 1):    # 确定年
                for month in range(1, 13):             #确定月
                    saving_account_set = SavingAccount.objects.filter(
                        SAccount_Open_Bank_Name=bank.Bank_Name)
                    loan_set = Loan.objects.filter(
                        Loan_Bank_Name=bank.Bank_Name)
                    overall_balance = 0.00
                    overall_loan = 0.00
                    overall_customer = 0
                    for sa in saving_account_set:    ## 统计储蓄账户
                        if sa.SAccount_Open_Date.year == year and sa.SAccount_Open_Date.month == month:
                            overall_balance += float(sa.SAccount_Balance)
                            overall_customer += 1
                    for ln in loan_set:      ## 统计贷款账户
                        release_set = LoanRelease.objects.filter(Loan_ID=ln.Loan_ID)
                        for release in release_set:
                            if release.Loan_Release_Date.year <= year and release.Loan_Release_Date.month == month:
                                overall_loan += float(release.Loan_Release_Amount)
                                overall_customer += 1
                    tmp[str(year) + "-M" + str(month)] = [overall_balance, overall_loan, overall_customer]
            bank_month_data.append(tmp)
        # print(bank_month_data)

        response_data = {}
        response_data['year_data'] = bank_year_data
        response_data['quarter_data'] = bank_quarter_data
        response_data['month_data'] = bank_month_data

        return Response(response_data)
