from django.contrib import admin
from .models import Item, Order, WarehouseItem, Warehouse

admin.site.register(Order)
admin.site.register(Warehouse)

# Register your models here.
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('koodi', 'nimike', 'lisanimike')
    search_fields = ('koodi', 'nimike')


@admin.register(WarehouseItem)
class WarehouseItemAdmin(admin.ModelAdmin):
    list_display = ('item', 'warehouse', 'quantity')
    list_editable = ('quantity',)
    search_fields = ('item__koodi', 'item__nimike')