from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
logger = logging.getLogger(__name__)

# Add a property to the User model to check if the user is a warehouse staff member
User.add_to_class('is_warehouse_staff', property(lambda u: u.groups.filter(name__iexact='Warehouse Staff').exists()))




# Color model for representing colors
class Color(models.Model):
    color = models.CharField(max_length=100, unique=True,  default="")

    class Meta:
        managed = True
        verbose_name = 'Väri'
        verbose_name_plural = 'Värit'
        
    def __str__(self):
        return f"{self.color}"

# Item model for representing items
class Item(models.Model):
    CATEGORY_CHOICES = [
        ('integraalit', 'Integraalit'),
        ('elastomeerit', 'Elastomeerit'),
        ('kovat', 'Kovat'),

 ]
    
    koodi = models.CharField(max_length=50)
    nimike = models.CharField(max_length=100, null=True, blank=True, default=' - ')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='integraalit')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        managed = True
        verbose_name = 'Tuote'
        verbose_name_plural = 'Tuotteet'
        constraints=[
            models.UniqueConstraint(fields=['koodi', 'color'], name='unique_item_code_name')
        ]
        
    def __str__(self):
        return f"{self.koodi} {self.nimike}"
    


class Warehouse(models.Model):
    name = models.CharField(max_length=20, default="Varasto")
    items = models.ManyToManyField(Item, through='WarehouseItem')

    def __str__(self):
        return f"{self.name} "
    
    class Meta:
        managed = True
        verbose_name = 'Varasto'
        verbose_name_plural = 'Varastot'


class WarehouseItem(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('warehouse', 'item', 'color')
        verbose_name = 'Varaston tuote'
        verbose_name_plural = 'Varaston tuotteet'

    def __str__(self):
        if self.item:
            return f"{self.item.koodi} {self.item.nimike} - Määrä: {self.quantity}"
        return f"Varastossa #{self.id} (ei ole tuotetta)"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_ordered = models.BooleanField(default=False)

    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"

class Workstation(models.Model):
    name_workstation = models.CharField(max_length=255, unique=True, default="")

    class Meta:
        managed = True
        verbose_name = 'Työpiste'
        verbose_name_plural = 'Työpisteet'
        
    def __str__(self):
        return f"{self.name_workstation}"
    


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    comment = models.TextField(blank=True)
    workstation = models.ForeignKey(Workstation, on_delete=models.SET_NULL, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        desc = f"{self.quantity}x {self.item}"
        if self.workstation:
            desc += f" ({self.workstation})"
        if self.color:
            desc += f" [{self.color}]"
        return desc
    

    

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Odottaa'),
        ('processing', 'Käsitelyssä'),
        ('delivered', 'Toimitettu'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True)

        
    class Meta:
        managed = True
        ordering = ['-created_at']
        verbose_name = 'Tilaus'
        verbose_name_plural = 'Tilaukset'
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"
    
    
    def save(self, *args, **kwargs):
        # Send email notification when status changes
        if self.pk:
            old_status = Order.objects.get(pk=self.pk).status
            if old_status != self.status:
                self.send_status_notification()
        super().save(*args, **kwargs)

    def process_order(self):
        """Uusittu tilauksen käsittely."""
        try:
            with transaction.atomic():
                #  Tarkistetaan, että tilaus on valmis käsiteltäväksi
                warehouse = Warehouse.objects.first()
                cart_items = (
                    self.cart.items
                    .select_related('item')
                    .select_for_update()
                )

                for cart_item in cart_items:
                    warehouse_item = WarehouseItem.objects.select_for_update().get(
                    warehouse=warehouse,
                    item=cart_item.item
                )
                    # if warehouse_item.quantity < cart_item.quantity:
                        # raise ValueError(
                            # f" {cart_item.item.nimike} ({cart_item.item.koodi}) ei ole riittävästi varastossa. "
                            # f"Varastossa: {warehouse_item.quantity}, Pyydetty: {cart_item.quantity}"
                        # )
                    
                    warehouse_item.quantity -= cart_item.quantity
                    warehouse_item.save()
                    logger.info(
                        f"Varaston saldo päivitetty tuotteelle {cart_item.item.koodi}: "
                        f"-{cart_item.quantity}, uusi saldo: {warehouse_item.quantity}"
                    )
        except WarehouseItem.DoesNotExist:
            raise ValueError(f" Valittu {cart_item.item.nimike} tuote ei ole varastossa.")
        except Exception as e:
            logger.error(f"Virhe tilauksen käsittelyssä: {e}")
            raise
    
    def send_status_notification(self):
        try:
            subject = f"Tilauksesi tila on muuttunut ({self.get_status_display()})"

            # renderoidaan template HTML
            html_content = render_to_string(
                'emails/status_notification.html',
                {'order': self}
            )
            
            # Luodaan email viesti
            msg = EmailMultiAlternatives(
                subject,
                strip_tags(html_content),  # Tekstiversio
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"Status notification sent for order #{self.id}")
        except Exception as e:
            logger.error(f"Error sending status notification: {e}")
    
    def send_ready_notification(self):
        try:
            subject = f"Tilauksesi on valmis noudettavaksi! (Tilaus #{self.id})"
            
            # render HTML template
            if self.status != 'completed':
                logger.warning(f"Order #{self.id} is not completed, skipping ready notification.")
                return
            html_content = render_to_string(
                'emails/ready_notification.html',
                {'order': self}
            )

            # Luodaan email viesti
            msg = EmailMultiAlternatives(
                subject,
                strip_tags(html_content),  # Tekstiversio
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            self.is_notified = True
            self.save()
            logger.info(f"Ready notification sent for order #{self.id}")
        except Exception as e:
            logger.error(f"Error sending ready notification: {e}")

    def send_new_order_notification(self):
        try:
            subject = f"Uusi tilaus saapunut (Tilaus #{self.id})"
            
            # render HTML template
            html_content = render_to_string(
                'emails/new_order_notification.html',
                {'order': self}
            )

            # Create email message
            msg = EmailMultiAlternatives(
                subject,
                strip_tags(html_content),  # Text version
                settings.DEFAULT_FROM_EMAIL,
                [settings.WAREHOUSE_EMAIL],  # Send to warehouse
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"New order notification sent for order #{self.id}")
        except Exception as e:
            logger.error(f"Error sending new order notification: {e}")


def format_database_error(error):
    """
    Muuntaa tietokantavirheet käyttäjäystävällisiksi viesteiksi.
    """
    error_str = str(error)
    
    if 'unique_item_code_name' in error_str:
        return "⚠️ Tuote on jo olemassa\n\n" \
            "tällä tuotekoodilla ja värillä on jo tuote järjestelmässä.\n\n" \
            "Käytä toista tuotekoodia tai valitse eri väri tai muokkaa olemassa olevaa tuotetta."
    
    else:
        return "⚠️ Tallennusvirhe\n\n" \
            "Tapahtui odottamaton virhe tuotetta tallennettaessa.\n\n" \
            "• Tarkasta kaikki kentät tai yritä uudelleen"

    