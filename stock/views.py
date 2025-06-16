from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
import logging

from .models import Item, Cart, CartItem, Order, Warehouse, WarehouseItem
from .forms import AddToCartForm, OrderCommentForm, OrderStatusForm


logger = logging.getLogger(__name__)


def home(request):
    logger.debug("Это DEBUG сообщение")
    logger.info("Это INFO сообщение")
    logger.warning("Это WARNING сообщение")
    logger.error("Это ERROR сообщение")
    return render(request, 'main.html')

@login_required
def stock_list(request):
    warehouse = Warehouse.objects.first()
    if not warehouse:
        warehouse = Warehouse.objects.create(name="Varasto")
        logger.info(f"Created new warehouse: {warehouse}")

    # Get warehouse items with quantities > 0 and their related items
    warehouse_items = WarehouseItem.objects.filter(
        warehouse=warehouse,
        quantity__gt=0
    ).select_related('item')
    
    logger.info(f"Found {warehouse_items.count()} available warehouse items")
    
    return render(request, 'stock_list.html', {
        'warehouse_items': warehouse_items,
        'warehouse': warehouse
    })
@login_required
def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    warehouse = Warehouse.objects.first()
    
    try:
        warehouse_item = WarehouseItem.objects.get(
            warehouse=warehouse,
            item=item
        )
        available = warehouse_item.quantity
    except WarehouseItem.DoesNotExist:
        warehouse_item = None
        available = 0
        messages.warning(request, "Tätä tuotetta ei ole varastossa")
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            if available <= 0:
                messages.error(request, "Tuote ei ole varastossa")
                return redirect('stock_list')
            if form.cleaned_data['quantity'] > available:
                messages.error(request, 
                    f"Pyytämäsi määrä ({form.cleaned_data['quantity']}) ylittää varastosaldon ({available})")
                return redirect('item_detail', item_id=item.id)
            
            cart, created = Cart.objects.get_or_create(
                user=request.user, 
                is_ordered=False
            )
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item=item,
                defaults={
                    'quantity': form.cleaned_data['quantity'],
                    'comment': form.cleaned_data.get('comment', '')
                }
            )
            
            if not created:
                cart_item.quantity += form.cleaned_data['quantity']
                cart_item.save()
            
            messages.success(request, f"{item.nimike} lisätty ostoskoriin")
            return redirect('cart_view')
    else:
        form = AddToCartForm()
    
    return render(request, 'item_detail.html', {
        'item': item,
        'form': form,
        'warehouse_item': warehouse_item,
        'available': available
    })

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(
        user=request.user, 
        is_ordered=False,
        defaults={'created_at': timezone.now()}
    )
    
    if request.method == 'POST':
        try:
            if not cart.items.exists():
                messages.error(request, 'Tilaukset on tyhjä. Lisää tuotteita ennen tilauksen lähettämistä.')
                return redirect('cart_view')
            
            # Tilauksen luodaa trancationissa
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    cart=cart,
                    status='pending'
                )
                cart.is_ordered = True
                cart.save()
                
                # process_order() transaction sisältä
                # Tämä metodi voi sisältää logiikan, joka vähentää saldoa varastosta
                order.process_order()
            
            order.send_new_order_notification()
            # logger.info(f"Order #{order.id} created, notifications sent.")
            
            messages.success(request, 'Tilaus onnistui! Tilauksen tiedot on lähetetty sähköpostiisi.')
            return redirect('order_detail', order_id=order.id)
            
        except Exception as e:
            logger.error(f"Order creation error: {e}")
            messages.error(request, f'Virhe tilauksessa: {e}')
            return redirect('cart_view')
    
    return render(request, 'cart.html', {'cart': cart})

def increase_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('cart_view')

def decrease_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart_view')

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('cart_view')

def cart_context(request):
    if request.user.is_authenticated:
        cart_items_count = CartItem.objects.filter(
            cart__user=request.user,
            cart__is_ordered=False
        ).count()
        return {'cart_items_count': cart_items_count}
    return {}

@login_required
def order_list(request):
    cart_items_count = CartItem.objects.filter(
        cart__user=request.user,
        cart__is_ordered=False
    ).count()
    
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'order_list.html', {
        'orders': orders,
        'cart_items_count': cart_items_count
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        form = OrderCommentForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, "Kommentti päivitetty")
            return redirect('order_detail', order_id=order.id)
    else:
        form = OrderCommentForm(instance=order)
    
    return render(request, 'order_detail.html', {
        'order': order,
        'form': form
    })

@login_required
def warehouse_orders(request):
    if not request.user.is_staff:
        return redirect('stock_list')
    
    status = request.GET.get('status', 'pending')
    orders = Order.objects.filter(status=status).order_by('created_at')
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        old_status = order.status
        form = OrderStatusForm(request.POST, instance=order)
        
        if form.is_valid():
            order = form.save()
            
            if old_status != order.status:
                order.send_status_notification()
                
                if order.status == 'ready':
                    order.send_ready_notification()
            
            messages.success(request, "Tilauksen tila päivitetty")
            return redirect('warehouse_orders')
    else:
        form = OrderStatusForm()
    
    return render(request, 'warehouse_orders.html', {
        'orders': orders,
        'current_status': status,
        'form': form,
    })

def test_email(request):
    try:
        send_mail(
            'Test Email',
            'This is a test email from Django.',
            settings.DEFAULT_FROM_EMAIL,
            [settings.WAREHOUSE_EMAIL],
            fail_silently=False,
        )
        return HttpResponse("Email sent successfully!")
    except Exception as e:
        return HttpResponse(f"Failed to send email: {str(e)}")
    

    # views.py (admin-only)
@staff_member_required
def manage_stock(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity'))
        item = get_object_or_404(Item, id=item_id)
        warehouse = Warehouse.objects.first()  # varaston oletetaan olevan yksi
        
        warehouse_item, created = WarehouseItem.objects.get_or_create(
            warehouse=warehouse,
            item=item,
            defaults={'quantity': quantity}
        )
        
        if not created:
            warehouse_item.quantity += quantity
            warehouse_item.save()
        
        messages.success(request, f"Tuote {item.nimike} uusittu (+{quantity})")
        return redirect('manage_stock')
    
    items = Item.objects.all()
    return render(request, 'manage_stock.html', {'items': items})