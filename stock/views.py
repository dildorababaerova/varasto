from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.contrib.auth.models import Group
import logging

from .models import Item, Cart, CartItem, Order, Warehouse, WarehouseItem, Workstation, Color
from .forms import AddToCartForm, CustomUserCreationForm, OrderCommentForm, OrderStatusForm, ItemForm, QuantityForm, WarehouseStaffRegistrationForm

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test



logger = logging.getLogger(__name__)


def home(request):
    # logger.debug("Это DEBUG сообщение")
    # logger.info("Это INFO сообщение")
    # logger.warning("Это WARNING сообщение")
    # logger.error("Это ERROR сообщение")
    return render(request, 'main.html')

@login_required
def stock_list(request):
    warehouse = Warehouse.objects.first()
    if not warehouse:
        warehouse = Warehouse.objects.create(name="Varasto")
        logger.info(f"Created new warehouse: {warehouse}")

    # Get selected category from request
    selected_category = request.GET.get('category')
    
    # Get warehouse items with quantities > 0
    warehouse_items = WarehouseItem.objects.filter(
        warehouse=warehouse,
        quantity__gt=0
    ).select_related('item')
    
    # Filter by category if selected
    if selected_category:
        warehouse_items = warehouse_items.filter(item__category=selected_category)
    
    logger.info(f"Found {warehouse_items.count()} available warehouse items")
    
    return render(request, 'stock_list.html', {
        'warehouse_items': warehouse_items,
        'warehouse': warehouse,
        'categories': Item.CATEGORY_CHOICES,
        'selected_category': selected_category
    })


@login_required
def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    workstations = Workstation.objects.all()  # Get all workstations
    colors = Color.objects.all()  # Get all colors
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
            quantity = form.cleaned_data['quantity']
            
            if quantity <= 0:
                messages.error(request, "Määrän tulee olla suurempi kuin nolla")
                return redirect('item_detail', item_id=item.id)
                
            if available <= 0:
                messages.error(request, "Tuote ei ole varastossa")
                return redirect('stock_list')
                
            if quantity > available:
                messages.error(request, 
                    f"Pyytämäsi määrä ({quantity}) ylittää varastosaldon ({available})")
                return redirect('item_detail', item_id=item.id)
            
            cart, created = Cart.objects.get_or_create(
                user=request.user, 
                is_ordered=False
            )
            
            # Get selected workstation and color from form
            workstation_id = request.POST.get('workstation')
            color_id = request.POST.get('color')
            
            try:
                workstation = Workstation.objects.get(id=workstation_id) if workstation_id else None
                color = Color.objects.get(id=color_id) if color_id else None
            except (Workstation.DoesNotExist, Color.DoesNotExist):
                messages.error(request, "Virheellinen työpiste tai väri")
                return redirect('item_detail', item_id=item.id)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item=item,
                defaults={
                    'quantity': quantity,
                    'comment': form.cleaned_data.get('comment', ''),
                    'workstation': workstation,
                    'color': color
                }
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.workstation = workstation
                cart_item.color = color
                cart_item.save()
            
            messages.success(request, f"{item.nimike} lisätty tilaukseen")
            return redirect('cart_view')
    else:
        form = AddToCartForm()
    
    return render(request, 'item_detail.html', {
        'item': item,
        'form': form,
        'warehouse_item': warehouse_item,
        'available': available,
        'workstations': workstations,
        'colors': colors,
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
            
            messages.success(request, 'Tilaus onnistui! Tilauksen tiedot on lähetetty sähköpostiisi.')
            return redirect('order_detail', order_id=order.id)
            
        except Exception as e:
            logger.error(f"Order creation error: {e}")
            messages.error(request, f'Virhe tilauksessa: {e}')
            return redirect('cart_view')
    
    # Add prefetch_related to optimize queries
    cart_items = cart.items.select_related('item', 'workstation', 'color').all()
    return render(request, 'cart.html', {
        'cart': cart,
        'cart_items': cart_items
    })


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
    order = get_object_or_404(Order.objects.select_related('user'), id=order_id)
    
    if not (request.user.is_superuser or is_warehouse_staff(request.user) or order.user == request.user):
        messages.error(request, "Sinulla ei ole pääsyä tähän tilaukseen.")
        return redirect('order_list')
    
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


def is_warehouse_staff(user):
    """Check if user is warehouse staff (has permission but not full admin)"""
    return user.is_authenticated and (
        user.is_staff or 
        user.groups.filter(name__iexact='Warehouse Staff').exists()
        )

def warehouse_staff_required(view_func):
    def test_func(user):
        return is_warehouse_staff(user)
    return user_passes_test(test_func)(view_func)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_warehouse_staff(u))
def warehouse_orders(request):
    status = request.GET.get('status', 'pending')
    orders = Order.objects.filter(status=status).order_by('created_at').select_related('user')
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        old_status = order.status
        # Only allow status changes
        new_status = request.POST.get('status')

        if new_status in dict(Order.STATUS_CHOICES).keys():
            order.status = new_status
            order.save()

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
    color_choices = Color.objects.all()

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 0))
        color_id = request.POST.get('color_id')
        
        if not item_id or quantity <= 0:
            messages.error(request, "Virheelliset tiedot")
            return redirect('manage_stock')
        
        try:
            item = Item.objects.get(id=item_id)
            warehouse = Warehouse.objects.first()  # Assuming single warehouse
            color = Color.objects.get(id=color_id) if color_id else None

            warehouse_item, created = WarehouseItem.objects.get_or_create(
                warehouse=warehouse,
                item=item,
                color=color,
                defaults={'quantity': quantity}
            )
            
            if not created:
                warehouse_item.quantity += quantity
                warehouse_item.save()
            
            messages.success(request, f"Tuote {item.nimike} päivitetty (+{quantity})")
            return redirect('manage_stock')
        
        except Item.DoesNotExist:
            messages.error(request, "Tuotetta ei löytynyt")
        except Color.DoesNotExist:
            messages.error(request, "Väriä ei löytynyt")
        except Exception as e:
            messages.error(request, f"Virhe: {str(e)}")
            return redirect('manage_stock')
    
    # Get all items for dropdown
    items = Item.objects.all().order_by('nimike')

    
    # Get warehouse items with pagination
    warehouse = Warehouse.objects.first()
    warehouse_items_list = WarehouseItem.objects.filter(warehouse=warehouse).select_related('item', 'color').order_by('-last_updated')
    
    paginator = Paginator(warehouse_items_list, 25)  # Show 25 items per page
    page_number = request.GET.get('page')
    warehouse_items = paginator.get_page(page_number)
    
    return render(request, 'manage_stock.html', {
        'items': items,
        'warehouse_items': warehouse_items,
        'color_choices': color_choices
    })


@staff_member_required
def add_item(request, item_id=None):
    color_choices = Color.objects.all()
    color = None 

    if item_id:
        item = get_object_or_404(Item, id=item_id)
        warehouse_item = get_object_or_404(WarehouseItem, item=item)
        color = item.color 
    else:
        item = None
        warehouse_item = None

    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        quantity_form = QuantityForm(request.POST)
        
        if form.is_valid() and quantity_form.is_valid():
            # Handle new color creation
            selected_color_id = request.POST.get('color_id')
            new_color_name = form.cleaned_data.get('new_color')
            if selected_color_id and selected_color_id != '':
                color = get_object_or_404(Color, id=selected_color_id)
                form.instance.color = color
            elif new_color_name:
                color, created = Color.objects.get_or_create(color=new_color_name)
                form.instance.color = color
            
            # Save the item
            new_item = form.save()
            
            # Handle warehouse item
            warehouse_item, created = WarehouseItem.objects.get_or_create(
                warehouse=Warehouse.objects.first(),
                item=new_item,
                color=color,
                defaults={'quantity': quantity_form.cleaned_data['quantity']}
            )
            
            if not created:
                warehouse_item.quantity = quantity_form.cleaned_data['quantity']
                warehouse_item.color = color
                warehouse_item.save()
            
            messages.success(request, "Tuote tallennettu onnistuneesti!")
            return redirect('manage_stock')
        else:
            messages.error(request, "Tarkista lomakkeen tiedot")
    else:
        form = ItemForm(instance=item)
        initial_quantity = warehouse_item.quantity if warehouse_item else 0
        quantity_form = QuantityForm(initial={'quantity': initial_quantity})
    
    return render(request, 'add_item.html', {
        'form': form,
        'quantity_form': quantity_form,
        'is_edit': item_id is not None,
        'color_choices': color_choices,
        'color': color
    })

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('stock_list')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})


def register_warehouse_staff(request):
    if request.method == 'POST':
        form = WarehouseStaffRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                group = Group.objects.get(name__iexact='Warehouse Staff')
                user.groups.add(group)
                user.save()
                messages.success(request, 'Varaston henkilöstö rekisteröity onnistuneesti.')
            except Group.DoesNotExist:
                messages.error(request, 'Varaston henkilöstö -ryhmää ei löydy. Ole hyvä ja luo se ensin.')
            
            return redirect('login')
    else:
        form = WarehouseStaffRegistrationForm()
    return render(request, 'registration/register_warehouse_staff.html', {'form': form})


