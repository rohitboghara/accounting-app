from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from decimal import Decimal
from datetime import date, timedelta
from apps.masters.models import Account, CompanyProfile, Budget
from apps.transactions.models import JournalVoucherLine, JournalVoucher


def get_fy_dates(request):
    active_id = request.session.get('active_company_id')
    company = CompanyProfile.objects.filter(id=active_id).first()
    if company:
        return company.fy_start(), company.fy_end()
    today = date.today()
    if today.month >= 4:
        return date(today.year, 4, 1), date(today.year + 1, 3, 31)
    else:
        return date(today.year - 1, 4, 1), date(today.year, 3, 31)


@login_required
def report_index(request):
    return render(request, 'reports/index.html')


@login_required
def ledger_report(request):
    active_id = request.session.get('active_company_id')
    accounts = Account.objects.filter(company_id=active_id, is_active=True).order_by('code')
    fy_start, fy_end = get_fy_dates(request)

    account_id = request.GET.get('account_id', '')
    date_from = request.GET.get('date_from', fy_start.isoformat())
    date_to = request.GET.get('date_to', fy_end.isoformat())

    selected_account = None
    ledger_entries = []
    opening_balance = Decimal('0')
    closing_balance = Decimal('0')

    if account_id:
        selected_account = get_object_or_404(Account, pk=account_id, company_id=active_id)

        # Opening balance
        ob_debit = JournalVoucherLine.objects.filter(
            voucher__company_id=active_id,
            account=selected_account,
            voucher__date__lt=date_from
        ).aggregate(s=Sum('debit_amount'))['s'] or Decimal('0')
        ob_credit = JournalVoucherLine.objects.filter(
            voucher__company_id=active_id,
            account=selected_account,
            voucher__date__lt=date_from
        ).aggregate(s=Sum('credit_amount'))['s'] or Decimal('0')

        acc_ob = selected_account.opening_balance
        if selected_account.opening_balance_type == 'debit':
            ob_debit += acc_ob
        else:
            ob_credit += acc_ob

        if selected_account.category in ('assets', 'expenses'):
            opening_balance = ob_debit - ob_credit
        else:
            opening_balance = ob_credit - ob_debit

        # Lines
        lines = JournalVoucherLine.objects.filter(
            voucher__company_id=active_id,
            account=selected_account,
            voucher__date__gte=date_from,
            voucher__date__lte=date_to
        ).select_related('voucher').order_by('voucher__date', 'voucher__voucher_number')

        running_balance = opening_balance
        for line in lines:
            if selected_account.category in ('assets', 'expenses'):
                running_balance += line.debit_amount - line.credit_amount
            else:
                running_balance += line.credit_amount - line.debit_amount
            ledger_entries.append({
                'date': line.voucher.date,
                'voucher_number': line.voucher.voucher_number,
                'description': line.description or line.voucher.narration,
                'debit': line.debit_amount,
                'credit': line.credit_amount,
                'balance': running_balance,
            })
        closing_balance = running_balance

    return render(request, 'reports/ledger.html', {
        'accounts': accounts, 'selected_account': selected_account,
        'account_id': account_id, 'date_from': date_from, 'date_to': date_to,
        'opening_balance': opening_balance, 'ledger_entries': ledger_entries,
        'closing_balance': closing_balance,
    })


@login_required
def trial_balance(request):
    active_id = request.session.get('active_company_id')
    fy_start, fy_end = get_fy_dates(request)
    date_to = request.GET.get('date_to', fy_end.isoformat())

    accounts = Account.objects.filter(company_id=active_id, is_active=True).order_by('code')
    rows = []
    totals = {'ob_d': Decimal('0'), 'ob_c': Decimal('0'), 'pd': Decimal('0'), 'pc': Decimal('0'), 'cd': Decimal('0'), 'cc': Decimal('0')}

    for acc in accounts:
        ob_d, ob_c = (acc.opening_balance, Decimal('0')) if acc.opening_balance_type == 'debit' else (Decimal('0'), acc.opening_balance)
        
        agg = JournalVoucherLine.objects.filter(voucher__company_id=active_id, account=acc, voucher__date__lte=date_to).aggregate(td=Sum('debit_amount'), tc=Sum('credit_amount'))
        td, tc = agg['td'] or Decimal('0'), agg['tc'] or Decimal('0')

        agg_period = JournalVoucherLine.objects.filter(voucher__company_id=active_id, account=acc, voucher__date__gte=fy_start, voucher__date__lte=date_to).aggregate(td=Sum('debit_amount'), tc=Sum('credit_amount'))
        pd, pc = agg_period['td'] or Decimal('0'), agg_period['tc'] or Decimal('0')

        closing_d, closing_c = ob_d + td, ob_c + tc
        close_dr, close_cr = (closing_d - closing_c, Decimal('0')) if closing_d >= closing_c else (Decimal('0'), closing_c - closing_d)

        if ob_d > 0 or ob_c > 0 or td > 0 or tc > 0:
            rows.append({'account': acc, 'ob_debit': ob_d, 'ob_credit': ob_c, 'period_debit': pd, 'period_credit': pc, 'closing_debit': close_dr, 'closing_credit': close_cr})
            totals['ob_d'] += ob_d; totals['ob_c'] += ob_c; totals['pd'] += pd; totals['pc'] += pc; totals['cd'] += close_dr; totals['cc'] += close_cr

    return render(request, 'reports/trial_balance.html', {'rows': rows, 'date_to': date_to, **totals})


@login_required
def profit_loss(request):
    active_id = request.session.get('active_company_id')
    fy_start, fy_end = get_fy_dates(request)
    date_from = request.GET.get('date_from', fy_start.isoformat())
    date_to = request.GET.get('date_to', fy_end.isoformat())

    def get_account_balance(acc, df, dt):
        ob_d, ob_c = (acc.opening_balance, Decimal('0')) if acc.opening_balance_type == 'debit' else (Decimal('0'), acc.opening_balance)
        agg = JournalVoucherLine.objects.filter(voucher__company_id=active_id, account=acc, voucher__date__gte=df, voucher__date__lte=dt).aggregate(td=Sum('debit_amount'), tc=Sum('credit_amount'))
        td, tc = (agg['td'] or Decimal('0')) + ob_d, (agg['tc'] or Decimal('0')) + ob_c
        return td - tc if acc.category in ('assets', 'expenses') else tc - td

    income_accounts = Account.objects.filter(company_id=active_id, category='income', is_active=True).order_by('code')
    expense_accounts = Account.objects.filter(company_id=active_id, category='expenses', is_active=True).order_by('code')

    income_rows = [{'account': a, 'amount': get_account_balance(a, date_from, date_to)} for a in income_accounts]
    expense_rows = [{'account': a, 'amount': get_account_balance(a, date_from, date_to)} for a in expense_accounts]
    
    ti = sum(r['amount'] for r in income_rows); te = sum(r['amount'] for r in expense_rows)

    return render(request, 'reports/profit_loss.html', {'income_rows': income_rows, 'expense_rows': expense_rows, 'total_income': ti, 'total_expenses': te, 'net_profit': ti - te, 'date_from': date_from, 'date_to': date_to})


@login_required
def balance_sheet(request):
    active_id = request.session.get('active_company_id')
    fy_start, fy_end = get_fy_dates(request)
    as_of_date = request.GET.get('as_of_date', fy_end.isoformat())

    def get_balance(acc, as_of):
        ob_d, ob_c = (acc.opening_balance, Decimal('0')) if acc.opening_balance_type == 'debit' else (Decimal('0'), acc.opening_balance)
        agg = JournalVoucherLine.objects.filter(voucher__company_id=active_id, account=acc, voucher__date__lte=as_of).aggregate(td=Sum('debit_amount'), tc=Sum('credit_amount'))
        td, tc = (agg['td'] or Decimal('0')) + ob_d, (agg['tc'] or Decimal('0')) + ob_c
        return td - tc if acc.category in ('assets', 'expenses') else tc - td

    assets = Account.objects.filter(company_id=active_id, category='assets', is_active=True).order_by('code')
    liabilities = Account.objects.filter(company_id=active_id, category='liabilities', is_active=True).order_by('code')
    equity = Account.objects.filter(company_id=active_id, category='equity', is_active=True).order_by('code')
    
    asset_rows = [{'account': a, 'amount': get_balance(a, as_of_date)} for a in assets]
    liability_rows = [{'account': l, 'amount': get_balance(l, as_of_date)} for l in liabilities]
    equity_rows = [{'account': e, 'amount': get_balance(e, as_of_date)} for e in equity]

    # Retained earnings
    total_income = sum(get_balance(a, as_of_date) for a in Account.objects.filter(company_id=active_id, category='income', is_active=True))
    total_expenses = sum(get_balance(a, as_of_date) for a in Account.objects.filter(company_id=active_id, category='expenses', is_active=True))
    re = total_income - total_expenses

    ta = sum(r['amount'] for r in asset_rows); tl = sum(r['amount'] for r in liability_rows); teq = sum(r['amount'] for r in equity_rows)
    tle = tl + teq + re

    return render(request, 'reports/balance_sheet.html', {
        'asset_rows': asset_rows, 'liability_rows': liability_rows, 'equity_rows': equity_rows,
        'total_assets': ta, 'total_liabilities': tl, 'total_equity': teq, 'retained_earnings': re,
        'total_liabilities_equity': tle, 'as_of_date': as_of_date, 'balanced': abs(ta - tle) < Decimal('0.01')
    })


@login_required
def gst_report(request):
    active_id = request.session.get('active_company_id')
    fy_start, fy_end = get_fy_dates(request)
    date_from = request.GET.get('date_from', fy_start.isoformat())
    date_to = request.GET.get('date_to', fy_end.isoformat())

    gst_lines = JournalVoucherLine.objects.filter(voucher__company_id=active_id, has_gst=True, voucher__date__gte=date_from, voucher__date__lte=date_to).select_related('account', 'voucher').order_by('voucher__date')

    totals = gst_lines.aggregate(tt=Sum('taxable_value'), tc=Sum('cgst_amount'), ts=Sum('sgst_amount'), ti=Sum('igst_amount'))

    return render(request, 'reports/gst_report.html', {
        'gst_lines': gst_lines, 'total_taxable': totals['tt'] or 0, 'total_cgst': totals['tc'] or 0,
        'total_sgst': totals['ts'] or 0, 'total_igst': totals['ti'] or 0, 'date_from': date_from, 'date_to': date_to
    })


@login_required
def aging_report(request):
    active_id = request.session.get('active_company_id')
    as_of_date = request.GET.get('as_of_date', date.today().isoformat())
    as_of = date.fromisoformat(as_of_date)
    
    accounts = Account.objects.filter(company_id=active_id, account_type='receivable', is_active=True)
    report_data = []
    
    for acc in accounts:
        _, _, total_bal = acc.get_balance(as_of_date=as_of)
        if total_bal <= 0: continue
            
        buckets = {'current': Decimal('0'), '30_days': Decimal('0'), '60_days': Decimal('0'), '90_plus': Decimal('0'), 'total': total_bal}
        debits = JournalVoucherLine.objects.filter(voucher__company_id=active_id, account=acc, voucher__date__lte=as_of, debit_amount__gt=0).select_related('voucher').order_by('-voucher__date')
        
        rem = total_bal
        for d in debits:
            if rem <= 0: break
            days = (as_of - d.voucher.date).days; amt = min(d.debit_amount, rem)
            if days <= 30: buckets['current'] += amt
            elif days <= 60: buckets['30_days'] += amt
            elif days <= 90: buckets['60_days'] += amt
            else: buckets['90_plus'] += amt
            rem -= amt
            
        report_data.append({'account': acc, 'buckets': buckets})
        
    return render(request, 'reports/aging_report.html', {'report_data': report_data, 'as_of_date': as_of_date})


@login_required
def budget_report(request):
    active_id = request.session.get('active_company_id')
    month_str = request.GET.get('month', date.today().replace(day=1).isoformat())
    sel_month = date.fromisoformat(month_str).replace(day=1)
    next_month = (sel_month + timedelta(days=32)).replace(day=1)
    
    budgets = Budget.objects.filter(company_id=active_id, month=sel_month).select_related('account')
    rows = []
    for b in budgets:
        agg = JournalVoucherLine.objects.filter(voucher__company_id=active_id, account=b.account, voucher__date__gte=sel_month, voucher__date__lt=next_month).aggregate(td=Sum('debit_amount'), tc=Sum('credit_amount'))
        td, tc = agg['td'] or Decimal('0'), agg['tc'] or Decimal('0')
        actual = td - tc if b.account.category in ('assets', 'expenses') else tc - td
        rows.append({'account': b.account, 'budget': b.amount, 'actual': actual, 'variance': b.amount - actual, 'percent': (actual / b.amount * 100) if b.amount != 0 else 0})
        
    return render(request, 'reports/budget_report.html', {'rows': rows, 'sel_month': sel_month})
