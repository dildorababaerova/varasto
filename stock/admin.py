from django.contrib import admin
from .models import Item, Order, WarehouseItem, Warehouse, Workstation, Color

admin.site.register(Order)
admin.site.register(Warehouse)
admin.site.register(Workstation)
admin.site.register(Color)


# Register your models here.
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('koodi', 'nimike','category')
    search_fields = ('koodi', 'nimike', 'category')


@admin.register(WarehouseItem)
class WarehouseItemAdmin(admin.ModelAdmin):
    list_display = ('item', 'warehouse', 'quantity')
    list_editable = ('quantity',)
    search_fields = ('item__koodi', 'item__nimike')