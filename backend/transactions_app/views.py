from rest_framework import viewsets,status
from django.db import transaction 
from django.db.models import Q

from .models import (
    NatureGroup,
    MainGroup, 
    Ledger, 
    Transaction,
    IncomeStatement, 
    BalanceSheet,
    ShareUsers
    )
from .serializers import (
     NatureGroupSerializer, 
     MainGroupSerializer, 
     LedgerSerializer, 
     TransactionSerializer,
     IncomeStatementSerializer, 
     BalanceSheetSerializer,
     ShareUserManagementSerializer,
     ProfitLossShareTransaction,
     ProfitLossShareTransactionSerializer
     )
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound

class NatureGroupViewSet(viewsets.ModelViewSet):
    queryset = NatureGroup.objects.all()
    serializer_class = NatureGroupSerializer

class MainGroupViewSet(viewsets.ModelViewSet):
    queryset = MainGroup.objects.all()
    serializer_class = MainGroupSerializer

class LedgerViewSet(viewsets.ModelViewSet):
    queryset = Ledger.objects.all()
    serializer_class = LedgerSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        transaction1_data = request.data.get('transaction1')
        transaction2_data = request.data.get('transaction2')

        if not transaction1_data or not transaction2_data:
            return Response({"error": "Both transaction1 and transaction2 are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate the next voucher number
        last_transaction = Transaction.objects.order_by('-voucher_no').first()
        next_voucher_no = (last_transaction.voucher_no + 1) if last_transaction else 1

        # Assign the generated voucher number to both transactions
        transaction1_data['voucher_no'] = next_voucher_no
        transaction2_data['voucher_no'] = next_voucher_no

        serializer1 = self.get_serializer(data=transaction1_data)
        serializer1.is_valid(raise_exception=True)
        self.perform_create(serializer1)

        serializer2 = self.get_serializer(data=transaction2_data)
        serializer2.is_valid(raise_exception=True)
        self.perform_create(serializer2)

        return Response(serializer1.data, status=status.HTTP_201_CREATED) 

    @action(detail=False, methods=['get'])
    def ledger_report(self, request):
        ledger_id = request.query_params.get('ledger', None)
        from_date = request.query_params.get('from_date', None)
        to_date = request.query_params.get('to_date', None)

        if not ledger_id:
            return Response([])

        queryset = self.queryset.filter(ledger__id=ledger_id)

        if not queryset.exists():
            return Response([])

        if from_date:
            from_date = parse_date(from_date)
        if to_date:
            to_date = parse_date(to_date)

        if from_date and to_date:
            queryset = queryset.filter(date__range=(from_date, to_date))
        elif from_date:
            queryset = queryset.filter(date__gte=from_date)
        elif to_date:
            queryset = queryset.filter(date__lte=to_date)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='filter-by-nature-group')
    def filter_by_nature_group(self, request):
        nature_group_name = request.query_params.get('nature_group_name', None)
        from_date = request.query_params.get('from_date', None)
        to_date = request.query_params.get('to_date', None)

        # Create a filter condition for nature_group_name
        filters = Q()
        if nature_group_name:
            filters &= Q(ledger__group__nature_group__name__iexact=nature_group_name)

        # Parse and apply the date range filter
        if from_date and to_date:
            from_date_parsed = parse_date(from_date)
            to_date_parsed = parse_date(to_date)

            if from_date_parsed and to_date_parsed:
                filters &= Q(date__range=(from_date_parsed, to_date_parsed))
            else:
                return Response([])  # Return empty response if dates are invalid
        else:
            return Response([])  # Return empty response if both dates are not provided

        # Fetch filtered transactions
        transactions = Transaction.objects.filter(filters)

        # Return empty if no transactions found
        if not transactions.exists():
            return Response([])

        # Serialize and return the filtered data
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)




class IncomeStatementViewSet(viewsets.ModelViewSet):
    queryset = IncomeStatement.objects.all()
    serializer_class = IncomeStatementSerializer

class BalanceSheetViewSet(viewsets.ModelViewSet):
    queryset = BalanceSheet.objects.all()
    serializer_class = BalanceSheetSerializer

#ShareManagement Section
class ShareUserManagementViewSet(viewsets.ModelViewSet):
    queryset = ShareUsers.objects.all()
    serializer_class = ShareUserManagementSerializer

class ProfitLossShareTransactionViewSet(viewsets.ModelViewSet):
    queryset = ProfitLossShareTransaction.objects.all()
    serializer_class = ProfitLossShareTransactionSerializer
    def get_queryset(self):
        queryset = ProfitLossShareTransaction.objects.all()
        transaction_no = self.request.query_params.get('transaction_no', None)
        if transaction_no:
            queryset = queryset.filter(transaction_no=transaction_no)
            if not queryset.exists():
                raise NotFound("Transaction not found")
        return queryset
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        return Response(serializer.data, status=201, headers=headers)

    def perform_create(self, serializer):
        serializer.save()