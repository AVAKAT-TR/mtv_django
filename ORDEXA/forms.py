from django import forms
from .models import OrdenCompra, Item, Producto
from django.forms import inlineformset_factory


# --------------------
# FORMULARIO ORDEN DE COMPRA
# --------------------
class OrdenForm(forms.ModelForm):
    monto_total = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )

    class Meta:
        model = OrdenCompra
        fields = ['comprador', 'fecha_emision', 'fecha_vencimiento', 'monto_total']
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_monto_total(self):
        data = self.cleaned_data['monto_total']
        if isinstance(data, str):
            data = data.replace(".", "").replace(",", ".")
        try:
            return float(data)
        except:
            raise forms.ValidationError("El monto no es un número válido")


# --------------------
# FORMULARIO DE ÍTEMS (LÍNEAS DE PRODUCTOS)
# --------------------
class ItemForm(forms.ModelForm):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        required=False,
        label="Producto",
        widget=forms.Select(attrs={"onchange": "actualizarPrecio(this)"})
    )

    class Meta:
        model = Item
        fields = ["producto", "descripcion", "cantidad", "precio"]
        widgets = {
            "descripcion": forms.TextInput(attrs={"readonly": "readonly"}),
            "precio": forms.NumberInput(attrs={"readonly": "readonly"}),
        }


# --------------------
# FORMSET (MÚLTIPLES ÍTEMS POR ORDEN)
# --------------------
ItemFormSet = inlineformset_factory(
    OrdenCompra,
    Item,
    form=ItemForm,
    extra=5,          # cantidad de filas vacías
    can_delete=False
)
