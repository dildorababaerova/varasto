from django.contrib import admin
from .models import Item, Order, WarehouseItem

# Register your models here.
admin.site.register(Item)

admin.site.register(Order)

@admin.register(WarehouseItem)
class WarehouseItemAdmin(admin.ModelAdmin):
    list_display = ('item', 'warehouse', 'quantity')
    list_editable = ('quantity',)
    search_fields = ('item__koodi', 'item__nimike')