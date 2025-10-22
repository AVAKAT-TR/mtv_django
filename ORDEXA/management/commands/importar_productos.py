import csv
from django.core.management.base import BaseCommand
from ORDEXA.models import Producto

class Command(BaseCommand):
    help = "Importa productos desde ORDEXA/productos.csv (con punto y coma) e ignora filas vacías."

    def handle(self, *args, **kwargs):
        file_path = "ORDEXA/productos.csv"
        total = 0

        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')

            for row in reader:
                # Limpieza de valores
                tipo = (row.get("tipo") or "").strip()
                codigo = (row.get("codigo") or "").strip()
                medida = (row.get("medida") or "").strip()
                precio_str = (row.get("precio") or "").replace("$", "").replace(".", "").replace(",", "").strip()

                # ⚠️ Saltar filas completamente vacías o separadores
                if not tipo and not codigo and not medida:
                    continue

                try:
                    precio = float(precio_str)
                except ValueError:
                    precio = 0

                Producto.objects.create(
                    tipo=tipo,
                    codigo=codigo,
                    medida=medida,
                    precio=precio
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {total} productos importados correctamente (ignorando filas vacías)."))
