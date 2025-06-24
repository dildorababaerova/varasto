# stock/context_processors.py
def user_groups(request):
    return {
        'is_warehouse_staff': request.user.groups.filter(name='Warehouse Staff').exists()
    }