from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib import messages
from django.db.models import Sum, Count
from .forms import LoginForm, UserForm, UserEditForm
from .models import User
from apps.transactions.models import JournalVoucher
from apps.masters.models import Account


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    active_id = request.session.get('active_company_id')
    recent_vouchers = JournalVoucher.objects.filter(company_id=active_id).select_related('created_by').order_by('-date', '-created_at')[:5]
    total_vouchers = JournalVoucher.objects.filter(company_id=active_id).count()
    total_accounts = Account.objects.filter(company_id=active_id).count()
    from apps.transactions.models import JournalVoucherLine
    from decimal import Decimal
    from django.db.models import Q

    # Quick P&L snapshot
    income_accounts = Account.objects.filter(company_id=active_id, category='income')
    expense_accounts = Account.objects.filter(company_id=active_id, category='expenses')

    income_total = Decimal('0')
    expense_total = Decimal('0')
    for acc in income_accounts:
        credits = JournalVoucherLine.objects.filter(account=acc).aggregate(s=Sum('credit_amount'))['s'] or Decimal('0')
        debits = JournalVoucherLine.objects.filter(account=acc).aggregate(s=Sum('debit_amount'))['s'] or Decimal('0')
        income_total += (credits - debits)

    for acc in expense_accounts:
        debits = JournalVoucherLine.objects.filter(account=acc).aggregate(s=Sum('debit_amount'))['s'] or Decimal('0')
        credits = JournalVoucherLine.objects.filter(account=acc).aggregate(s=Sum('credit_amount'))['s'] or Decimal('0')
        expense_total += (debits - credits)

    net_profit = income_total - expense_total

    # Monthly Trend Data (Last 6 months)
    import json
    from datetime import date, timedelta
    from django.db.models.functions import ExtractMonth
    
    chart_labels = []
    income_data = []
    expense_data = []
    
    today = date.today()
    for i in range(5, -1, -1):
        first_day = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        chart_labels.append(first_day.strftime('%b %Y'))
        
        mon_inc = JournalVoucherLine.objects.filter(
            voucher__company_id=active_id,
            account__category='income',
            voucher__date__gte=first_day,
            voucher__date__lte=last_day
        ).aggregate(s=Sum('credit_amount'))['s'] or Decimal('0')
        income_data.append(float(mon_inc))
        
        mon_exp = JournalVoucherLine.objects.filter(
            voucher__company_id=active_id,
            account__category='expenses',
            voucher__date__gte=first_day,
            voucher__date__lte=last_day
        ).aggregate(s=Sum('debit_amount'))['s'] or Decimal('0')
        expense_data.append(float(mon_exp))

    context = {
        'recent_vouchers': recent_vouchers,
        'total_vouchers': total_vouchers,
        'total_accounts': total_accounts,
        'income_total': income_total,
        'expense_total': expense_total,
        'net_profit': net_profit,
        'chart_labels': json.dumps(chart_labels),
        'income_data': json.dumps(income_data),
        'expense_data': json.dumps(expense_data),
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def user_list(request):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    users = User.objects.all().order_by('username')
    return render(request, 'core/user_list.html', {'users': users})


@login_required
def user_create(request):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    form = UserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'User created successfully.')
        return redirect('user_list')
    return render(request, 'core/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
def user_edit(request, pk):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    user = User.objects.get(pk=pk)
    form = UserEditForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'User updated successfully.')
        return redirect('user_list')
    return render(request, 'core/user_form.html', {'form': form, 'title': 'Edit User'})


@login_required
def profile_view(request):
    form = UserEditForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'core/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/change_password.html', {
        'form': form
    })


@login_required
def admin_change_password(request, pk):
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    user = User.objects.get(pk=pk)
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Password for {user.username} updated successfully.')
            return redirect('user_list')
    else:
        form = SetPasswordForm(user)
    return render(request, 'core/change_password.html', {
        'form': form,
        'title': f'Change Password for {user.username}'
    })
