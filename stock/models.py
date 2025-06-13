from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
logger = logging.getLogger(__name__)

class Item(models.Model):
    koodi = models.CharField(max_length=255)
    nimike = models.CharField(max_length=255)
    lisanimike = models.CharField(max_length=255)
    # saldo = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.koodi} {self.nimike} {self.lisanimike}"

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_ordered = models.BooleanField(default=False)

    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    comment = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.item}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Odottaa'),
        ('delivered', 'Toimitettu'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True)
    
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
                cart_items = (
                    self.cart.items
                    .select_related('item')
                    .select_for_update()
                )

                for cart_item in cart_items:
                    item = cart_item.item
                    if item.saldo < cart_item.quantity:
                        raise ValueError(
                            f" {item.nimike} ({item.koodi}) ei ole riittävästi varastossa. "
                            f"Varastossa: {item.saldo}, Pyydetty: {cart_item.quantity}"
                        )
                    
                    item.saldo -= cart_item.quantity
                    item.save()
                    logger.info(
                        f"Varaston saldo päivitetty tuotteelle {item.koodi}: "
                        f"-{cart_item.quantity}, uusi saldo: {item.saldo}"
                    )
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