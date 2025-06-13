from django import forms
from .models import CartItem, Order

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