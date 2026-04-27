from django.contrib import admin
from django.utils.html import format_html
from .models import Payout, IdempotencyKey
from .services import release_held_funds

@admin.action(description="Mark selected as failed and refund")
def mark_failed_and_refund(modeladmin, request, queryset):
    for payout in queryset:
        if payout.state in [Payout.PENDING, Payout.PROCESSING]:
            payout.transition(Payout.FAILED)
            payout.failure_reason = 'Manually marked failed by admin'
            payout.save(update_fields=['failure_reason'])
            release_held_funds(payout)

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant_name', 'amount_in_rupees', 'colored_state', 'attempts', 'created_at')
    list_filter = ('state', 'created_at')
    search_fields = ('merchant__name', 'merchant__email', 'id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'processing_started_at', 'completed_at')
    actions = [mark_failed_and_refund]

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
        return f"₹{formatted}.{decimal_part}"
    amount_in_rupees.short_description = 'Amount'

    def colored_state(self, obj):
        colors = {
            Payout.COMPLETED: 'green',
            Payout.FAILED: 'red',
            Payout.PROCESSING: 'orange',
            Payout.PENDING: 'gray'
        }
        color = colors.get(obj.state, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_state_display())
    colored_state.short_description = 'State'

@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ('key', 'merchant', 'response_status', 'created_at', 'expires_at')
    search_fields = ('key', 'merchant__name')
