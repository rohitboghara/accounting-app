from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CompanyProfile, Account
from .forms import CompanyProfileForm, AccountForm


@login_required
def company_profile(request):
    active_id = request.session.get('active_company_id')
    company = get_object_or_404(CompanyProfile, id=active_id) if active_id else CompanyProfile.objects.first()
    
    if request.method == 'POST':
        if not request.user.is_admin():
            messages.error(request, 'Only admins can edit company profile.')
            return redirect('company_profile')
        form = CompanyProfileForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company profile saved.')
            return redirect('company_profile')
    else:
        form = CompanyProfileForm(instance=company)
    return render(request, 'masters/company_profile.html', {'form': form, 'company': company, 'title': 'Company Profile'})

@login_required
def switch_company(request, pk):
    company = get_object_or_404(CompanyProfile, pk=pk)
    request.session['active_company_id'] = company.id
    messages.success(request, f"Switched to {company.name}")
    return redirect(request.GET.get('next', 'dashboard'))

@login_required
def company_list(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    companies = CompanyProfile.objects.all()
    return render(request, 'masters/company_list.html', {'companies': companies})

@login_required
def company_create(request):
    if not request.user.is_admin():
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    form = CompanyProfileForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        company = form.save()
        if not request.session.get('active_company_id'):
            request.session['active_company_id'] = company.id
        messages.success(request, "Company created successfully.")
        return redirect('company_list')
    return render(request, 'masters/company_profile.html', {'form': form, 'title': 'Create Company'})

@login_required
def account_list(request):
    active_id = request.session.get('active_company_id')
    category = request.GET.get('category', '')
    accounts = Account.objects.filter(company_id=active_id)
    if category:
        accounts = accounts.filter(category=category)
    accounts = accounts.order_by('code')
    return render(request, 'masters/account_list.html', {
        'accounts': accounts,
        'category_filter': category,
        'categories': Account.CATEGORY_CHOICES,
    })


@login_required
def account_create(request):
    if not request.user.is_admin():
        messages.error(request, 'Only admins can create accounts.')
        return redirect('account_list')
    form = AccountForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        account = form.save(commit=False)
        account.company_id = request.session.get('active_company_id')
        account.save()
        messages.success(request, 'Account created successfully.')
        return redirect('account_list')
    return render(request, 'masters/account_form.html', {'form': form, 'title': 'Create Account'})


@login_required
def account_edit(request, pk):
    active_id = request.session.get('active_company_id')
    if not request.user.is_admin():
        messages.error(request, 'Only admins can edit accounts.')
        return redirect('account_list')
    account = get_object_or_404(Account, pk=pk, company_id=active_id)
    form = AccountForm(request.POST or None, instance=account)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Account updated successfully.')
        return redirect('account_list')
    return render(request, 'masters/account_form.html', {'form': form, 'title': 'Edit Account', 'account': account})


@login_required
def account_delete(request, pk):
    active_id = request.session.get('active_company_id')
    if not request.user.is_admin():
        messages.error(request, 'Access denied.')
        return redirect('account_list')
    account = get_object_or_404(Account, pk=pk, company_id=active_id)
    if request.method == 'POST':
        account.delete()
        messages.success(request, 'Account deleted.')
        return redirect('account_list')
    return render(request, 'masters/account_confirm_delete.html', {'account': account})
