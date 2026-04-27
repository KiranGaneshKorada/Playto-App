from django.contrib import admin
from .models import Merchant, BankAccount

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_active', 'created_at')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('is_active', 'created_at')

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'bank_name', 'account_number', 'is_primary', 'is_active')
    search_fields = ('merchant__name', 'bank_name', 'account_number', 'ifsc_code')
    list_filter = ('is_primary', 'is_active', 'created_at')
