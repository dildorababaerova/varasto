from django import forms
from .models import CartItem, Order,Item
from django.core.validators import EmailValidator, RegexValidator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class AddToCartForm(forms.ModelForm):
    
    quantity = forms.IntegerField(min_value=1, label="Määrä")
    comment = forms.CharField(
        required=False,
        max_length=200,
        # widget=forms.Textarea(attrs={'rows': 2}),
        label="Lisäkommentti",
    )
    
    class Meta:
        model = CartItem
        fields = ['quantity', 'comment']

class OrderCommentForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'comment': 'Lisäkommentti',
        }

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'comment']
        labels = {
            'status': 'Tila',
            'comment': 'Päivitys',
        }

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['koodi', 'nimike', 'category' ]
        widgets = {
            'koodi': forms.TextInput(attrs={'class': 'form-control'}),
            'nimike': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(choices=Item.CATEGORY_CHOICES)
            
        }
        labels = {
            'koodi': 'Tuotekoodi',
            'nimike': 'Nimike',
            'category': 'Kategoria',
            
        }

class QuantityForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Määrä varastossa'
    )


# Regidtration workers

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        max_length=30,
        label=_('Käyttäjätunnus'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[
            RegexValidator(
                r'^[\w.@+-]+$',
                _('Käyttäjätunnuksessa saa olla vain kirjaimia, numeroita ja @/./+/-/_ -merkkejä.')
            ),
            
        ]
    )

    first_name = forms.CharField(
        max_length=30,
        label=_('Etunimi'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[RegexValidator(
        r'^[\w.@+\-äöÄÖÅå]+$',
        _('Käyttäjätunnuksessa saa olla vain kirjaimia, numeroita ja @/./+/-/_ -merkkejä.')
        )]
        )

    

    last_name = forms.CharField(
        max_length=30,
        label=_('Sukunimi'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[RegexValidator(r'^[a-zA-Z\s\-]+$', 'Vaan kirjaimet ja välilyönnit')]
    )

    # phone_number = forms.CharField(
    #     max_length=20,
    #     label=_('Puhelinnumero'),
    #     widget=forms.TextInput(attrs={'class': 'form-control'}),
    #     validators=[RegexValidator(r'^(?:\+358[\d\s-]{9,13}|0[\d\s-]{9,13})$', 'Syötä kelvollinen puhelinnumero (esim. +358401234567 tai 0401234567).')]
    # )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

