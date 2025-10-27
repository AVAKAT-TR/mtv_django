from django.contrib import admin
from .models import Producto

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "codigo", "medida", "precio")
    search_fields = ("tipo", "codigo", "medida")
