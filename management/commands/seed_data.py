from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date


class Command(BaseCommand):
    help = 'Load sample seed data for the accounting app'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                self._create_users()
                self._create_company()
                self._create_accounts()
                self._create_vouchers()
            self.stdout.write(self.style.SUCCESS('✓ Seed data loaded successfully!'))
            self.stdout.write(self.style.SUCCESS('  Admin login: admin / admin123'))
            self.stdout.write(self.style.SUCCESS('  Staff login: staff / staff123'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Seed data: {e}'))

    def _create_users(self):
        from apps.core.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                role='admin',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write('  Created admin user')

        if not User.objects.filter(username='staff').exists():
            User.objects.create_user(
                username='staff',
                email='staff@example.com',
                password='staff123',
                role='staff',
                first_name='Staff',
                last_name='User'
            )
            self.stdout.write('  Created staff user')

    def _create_company(self):
        from apps.masters.models import CompanyProfile
        if not CompanyProfile.objects.exists():
            CompanyProfile.objects.create(
                name='ABC Traders Pvt. Ltd.',
                gstin='27AABCT1234R1Z5',
                pan='AABCT1234R',
                address='123, Industrial Area, Phase-1',
                city='Mumbai',
                state='Maharashtra',
                pincode='400001',
                phone='+91-9876543210',
                email='info@abctraders.com',
                financial_year='2024-2025'
            )
            self.stdout.write('  Created company profile')

    def _create_accounts(self):
        from apps.masters.models import Account
        if Account.objects.exists():
            return

        accounts = [
            # Assets
            ('1001', 'Cash in Hand', 'assets', 'cash', 50000, 'debit'),
            ('1002', 'HDFC Bank Current A/c', 'assets', 'bank', 500000, 'debit'),
            ('1003', 'Accounts Receivable', 'assets', 'receivable', 200000, 'debit'),
            ('1004', 'Inventory / Stock', 'assets', 'current_asset', 300000, 'debit'),
            ('1005', 'Advance to Suppliers', 'assets', 'current_asset', 0, 'debit'),
            ('1101', 'Furniture & Fixtures', 'assets', 'fixed_asset', 150000, 'debit'),
            ('1102', 'Computer & Equipment', 'assets', 'fixed_asset', 80000, 'debit'),
            ('1103', 'Land & Building', 'assets', 'fixed_asset', 2000000, 'debit'),
            # Liabilities
            ('2001', 'Accounts Payable', 'liabilities', 'payable', 150000, 'credit'),
            ('2002', 'Outstanding Expenses', 'liabilities', 'current_liability', 30000, 'credit'),
            ('2003', 'GST Payable (CGST)', 'liabilities', 'tax', 0, 'credit'),
            ('2004', 'GST Payable (SGST)', 'liabilities', 'tax', 0, 'credit'),
            ('2005', 'GST Payable (IGST)', 'liabilities', 'tax', 0, 'credit'),
            ('2006', 'TDS Payable', 'liabilities', 'tax', 0, 'credit'),
            ('2101', 'Bank Loan - HDFC', 'liabilities', 'long_term_liability', 500000, 'credit'),
            # Equity
            ('3001', "Owner's Capital", 'equity', 'equity', 2500000, 'credit'),
            ('3002', 'Retained Earnings', 'equity', 'equity', 0, 'credit'),
            # Income
            ('4001', 'Sales Revenue', 'income', 'revenue', 0, 'credit'),
            ('4002', 'Service Revenue', 'income', 'revenue', 0, 'credit'),
            ('4003', 'Interest Income', 'income', 'other_income', 0, 'credit'),
            ('4004', 'Other Income', 'income', 'other_income', 0, 'credit'),
            # Expenses
            ('5001', 'Cost of Goods Sold', 'expenses', 'cost_of_goods', 0, 'debit'),
            ('5002', 'Salaries & Wages', 'expenses', 'operating_expense', 0, 'debit'),
            ('5003', 'Rent Expense', 'expenses', 'operating_expense', 0, 'debit'),
            ('5004', 'Electricity Charges', 'expenses', 'operating_expense', 0, 'debit'),
            ('5005', 'Telephone & Internet', 'expenses', 'operating_expense', 0, 'debit'),
            ('5006', 'Office Supplies', 'expenses', 'operating_expense', 0, 'debit'),
            ('5007', 'Travel & Conveyance', 'expenses', 'operating_expense', 0, 'debit'),
            ('5008', 'Advertising & Marketing', 'expenses', 'operating_expense', 0, 'debit'),
            ('5009', 'Bank Charges', 'expenses', 'other_expense', 0, 'debit'),
            ('5010', 'Depreciation', 'expenses', 'other_expense', 0, 'debit'),
            ('5011', 'GST Input Credit (CGST)', 'assets', 'tax', 0, 'debit'),
            ('5012', 'GST Input Credit (SGST)', 'assets', 'tax', 0, 'debit'),
            ('5013', 'GST Input Credit (IGST)', 'assets', 'tax', 0, 'debit'),
        ]

        # Mark GST accounts
        gst_codes = {'2003', '2004', '2005', '5011', '5012', '5013'}

        for code, name, category, acc_type, ob, ob_type in accounts:
            Account.objects.create(
                code=code,
                name=name,
                category=category,
                account_type=acc_type,
                opening_balance=Decimal(str(ob)),
                opening_balance_type=ob_type,
                is_gst_account=(code in gst_codes)
            )
        self.stdout.write(f'  Created {len(accounts)} accounts')

    def _create_vouchers(self):
        from apps.transactions.models import JournalVoucher, JournalVoucherLine
        from apps.masters.models import Account
        from apps.core.models import User

        if JournalVoucher.objects.exists():
            return

        admin = User.objects.get(username='admin')

        def get_acc(code):
            return Account.objects.get(code=code)

        vouchers_data = [
            # JV1: Sales with GST (Intra-state)
            {
                'voucher_number': 'JV20241001001',
                'date': date(2024, 10, 1),
                'narration': 'Sales to Ramesh Traders - Invoice #INV-001',
                'reference': 'INV-001',
                'status': 'posted',
                'lines': [
                    {'account': '1003', 'description': 'Accounts Receivable - Ramesh Traders', 'debit': 118000, 'credit': 0},
                    {'account': '4001', 'description': 'Sales Revenue', 'debit': 0, 'credit': 100000,
                     'has_gst': True, 'gst_type': 'intra', 'gst_rate': 18, 'taxable_value': 100000,
                     'cgst': 9000, 'sgst': 9000, 'igst': 0},
                    {'account': '2003', 'description': 'CGST @ 9%', 'debit': 0, 'credit': 9000},
                    {'account': '2004', 'description': 'SGST @ 9%', 'debit': 0, 'credit': 9000},
                ],
            },
            # JV2: Purchase with GST
            {
                'voucher_number': 'JV20241005001',
                'date': date(2024, 10, 5),
                'narration': 'Purchase from XYZ Suppliers - Bill #PUR-100',
                'reference': 'PUR-100',
                'status': 'posted',
                'lines': [
                    {'account': '1004', 'description': 'Inventory - goods purchased', 'debit': 50000, 'credit': 0,
                     'has_gst': True, 'gst_type': 'intra', 'gst_rate': 18, 'taxable_value': 50000,
                     'cgst': 4500, 'sgst': 4500, 'igst': 0},
                    {'account': '5011', 'description': 'GST Input CGST @ 9%', 'debit': 4500, 'credit': 0},
                    {'account': '5012', 'description': 'GST Input SGST @ 9%', 'debit': 4500, 'credit': 0},
                    {'account': '2001', 'description': 'Accounts Payable - XYZ Suppliers', 'debit': 0, 'credit': 59000},
                ],
            },
            # JV3: Salary payment
            {
                'voucher_number': 'JV20241031001',
                'date': date(2024, 10, 31),
                'narration': 'Monthly salary payment for October 2024',
                'reference': '',
                'status': 'posted',
                'lines': [
                    {'account': '5002', 'description': 'Salary expense - Oct 2024', 'debit': 85000, 'credit': 0},
                    {'account': '1002', 'description': 'Payment via bank transfer', 'debit': 0, 'credit': 85000},
                ],
            },
            # JV4: Rent payment
            {
                'voucher_number': 'JV20241101001',
                'date': date(2024, 11, 1),
                'narration': 'Office rent payment for November 2024',
                'reference': 'RENT-NOV24',
                'status': 'posted',
                'lines': [
                    {'account': '5003', 'description': 'Rent expense', 'debit': 25000, 'credit': 0},
                    {'account': '1001', 'description': 'Cash payment', 'debit': 0, 'credit': 25000},
                ],
            },
            # JV5: Customer payment received
            {
                'voucher_number': 'JV20241110001',
                'date': date(2024, 11, 10),
                'narration': 'Payment received from Ramesh Traders against INV-001',
                'reference': 'REC-001',
                'status': 'posted',
                'lines': [
                    {'account': '1002', 'description': 'Bank receipt', 'debit': 118000, 'credit': 0},
                    {'account': '1003', 'description': 'Accounts Receivable cleared', 'debit': 0, 'credit': 118000},
                ],
            },
            # JV6: Service revenue with Inter-state GST
            {
                'voucher_number': 'JV20241115001',
                'date': date(2024, 11, 15),
                'narration': 'Consulting services to Delhi client - Invoice #SRV-001',
                'reference': 'SRV-001',
                'status': 'posted',
                'lines': [
                    {'account': '1003', 'description': 'Receivable - Delhi client', 'debit': 59000, 'credit': 0},
                    {'account': '4002', 'description': 'Service Revenue', 'debit': 0, 'credit': 50000,
                     'has_gst': True, 'gst_type': 'inter', 'gst_rate': 18, 'taxable_value': 50000,
                     'cgst': 0, 'sgst': 0, 'igst': 9000},
                    {'account': '2005', 'description': 'IGST @ 18%', 'debit': 0, 'credit': 9000},
                ],
            },
            # JV7: Draft voucher (utility bill)
            {
                'voucher_number': 'JV20241201001',
                'date': date(2024, 12, 1),
                'narration': 'Electricity bill for November 2024 (Pending)',
                'reference': 'ELEC-NOV24',
                'status': 'draft',
                'lines': [
                    {'account': '5004', 'description': 'Electricity expense', 'debit': 8500, 'credit': 0},
                    {'account': '2002', 'description': 'Outstanding expense', 'debit': 0, 'credit': 8500},
                ],
            },
        ]

        for vd in vouchers_data:
            v = JournalVoucher.objects.create(
                voucher_number=vd['voucher_number'],
                date=vd['date'],
                narration=vd['narration'],
                reference=vd.get('reference', ''),
                status=vd['status'],
                created_by=admin
            )
            for i, ld in enumerate(vd['lines']):
                JournalVoucherLine.objects.create(
                    voucher=v,
                    account=get_acc(ld['account']),
                    description=ld.get('description', ''),
                    debit_amount=Decimal(str(ld['debit'])),
                    credit_amount=Decimal(str(ld['credit'])),
                    has_gst=ld.get('has_gst', False),
                    gst_type=ld.get('gst_type', ''),
                    gst_rate=Decimal(str(ld['gst_rate'])) if ld.get('gst_rate') else None,
                    taxable_value=Decimal(str(ld['taxable_value'])) if ld.get('taxable_value') else None,
                    cgst_amount=Decimal(str(ld['cgst'])) if ld.get('cgst') is not None else None,
                    sgst_amount=Decimal(str(ld['sgst'])) if ld.get('sgst') is not None else None,
                    igst_amount=Decimal(str(ld['igst'])) if ld.get('igst') is not None else None,
                    line_order=i
                )

        self.stdout.write(f'  Created {len(vouchers_data)} sample journal vouchers')
