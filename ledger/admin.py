from django.contrib import admin
from django.utils.html import format_html
from .models import LedgerEntry

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('merchant_name', 'colored_entry_type', 'amount_in_rupees', 'description', 'created_at')
    list_filter = ('entry_type', 'merchant', 'created_at')
    search_fields = ('merchant__name', 'reference_id')
    
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

    def merchant_name(self, obj):
        return obj.merchant.name
    merchant_name.short_description = 'Merchant'

    def amount_in_rupees(self, obj):
        rupees_str = f"{abs(obj.amount_paise) / 100:.2f}"
        integer_part, decimal_part = rupees_str.split('.')
        if len(integer_part) > 3:
            last_three = integer_part[-3:]
            other_numbers = integer_part[:-3]
            chunks = []
            for i in range(len(other_numbers), 0, -2):
                start = max(i-2, 0)
                chunks.append(other_numbers[start:i])
            chunks.reverse()
            formatted = ','.join(chunks) + ',' + last_three
        else:
            formatted = integer_part
            
        sign = "+" if obj.entry_type == LedgerEntry.CREDIT else "-"
        return f"{sign}₹{formatted}.{decimal_part}"
    amount_in_rupees.short_description = 'Amount'

    def colored_entry_type(self, obj):
        color = 'green' if obj.entry_type == LedgerEntry.CREDIT else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_entry_type_display())
    colored_entry_type.short_description = 'Type'
