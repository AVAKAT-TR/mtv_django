from django.db import models
from django.contrib.auth.models import User

class OrdenCompra(models.Model):
    comprador = models.CharField(max_length=200)
    vendedor = models.CharField(max_length=200, blank=True, null=True)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)  # 👈 usuario que creó la orden
    estado = models.CharField(max_length=20, choices=[
        ("pendiente", "Pendiente"),
        ("aprobada", "Aprobada"),
        ("rechazada", "Rechazada"),
    ], default="pendiente")

    def __str__(self):
        return f"Orden {self.id} - {self.comprador}"


class Item(models.Model):
    orden = models.ForeignKey(OrdenCompra, related_name="items", on_delete=models.CASCADE)
    producto = models.ForeignKey('Producto', on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField(max_length=200, blank=True)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio

class Producto(models.Model):
    tipo = models.CharField(max_length=100)
    codigo = models.CharField(max_length=100)
    medida = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=12, decimal_places=0)

    def __str__(self):
        tipo = self.tipo or ""
        codigo = self.codigo or ""
        medida = self.medida or ""
        precio = f"${self.precio:,.0f}" if self.precio else "$0"
        return f"{tipo} - {codigo} {medida} ({precio})".strip()
