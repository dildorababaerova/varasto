from django import forms
from .models import CartItem, Order,Item, Color, WarehouseItem
from django.core.validators import EmailValidator, RegexValidator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

# AddToCartForm for adding items to the cart
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

# Order comment form for adding comments to orders
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

# Order status form for updating the status of orders
class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'comment']
        labels = {
            'status': 'Tila',
            'comment': 'Päivitys',
        }

# Color selection form with the option to add a new color
class ColorSelectWithAdd(forms.Select):
    template_name = 'widgets/color_select_with_add.html'

    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        attrs.update({'class': 'form-select'})
        self.attrs = attrs

### ISSUE ei käytetty
# ItemForm for creating and updating items with color selection
class ItemForm(forms.ModelForm):
    color = forms.ModelChoiceField(
        queryset=Color.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Valitse väri'
    )
    
    new_color = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kirjoita uuden värin nimi'
        }),
        label='Tai lisää uusi väri'
    )
    
    class Meta:
        model = Item
        # fields = ['koodi', 'nimike', 'category', 'is_frequently_used']  # ← ДОБАВЛЕНО поле
        fields = ['koodi', 'nimike', 'category']  # ← ДОБАВЛЕНО поле
        widgets = {
            'koodi': forms.TextInput(attrs={'class': 'form-control'}),
            'nimike': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}, choices=Item.CATEGORY_CHOICES),
            # 'is_frequently_used': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'koodi': 'Tuotekoodi',
            'nimike': 'Nimike',
            'category': 'Kategoria',
            # 'is_frequently_used': 'Usein käytetty'
        }


class QuantityForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Määrä varastossa'
    )


# Registration workers

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
        validators=[RegexValidator(r'^[\w.@+\-äöÄÖÅå]+$', 'Vaan kirjaimet ja välilyönnit')]
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


# Registration form for warehouse staff with group assignment
class WarehouseStaffRegistrationForm(UserCreationForm):
    username = forms.CharField(
        max_length=30,
        label=_('Käyttäjätunnus'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[
            RegexValidator(
                r'^[\w.@+\-äöÄÖÅå]+$',
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
        validators=[RegexValidator(r'^[\w.@+\-äöÄÖÅå]+$', 'Vaan kirjaimet ja välilyönnit')]
    )

    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email','password1', 'password2']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    # Save the user and assign to the warehouse staff group
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            print("Groups before:", user.groups.all())  # Debug
            warehouse_staff_group = Group.objects.get(name='Warehouse Staff')
            user.groups.add(warehouse_staff_group)
            print("Groups after:", user.groups.all())  # Debug
        return user
    

    # forms.py
class WarehouseStaffQuantityForm(forms.ModelForm):
    class Meta:
        model = WarehouseItem
        fields = ['quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            })
        }
        labels = {
            'quantity': 'Määrä'
        }

