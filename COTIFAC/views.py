from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import OrdenCompra
from .forms import OrdenForm, ItemFormSet

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# 🔹 Usuarios y login
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from reportlab.platypus import Paragraph
from .models import Producto
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.core.serializers import serialize
import json
from .models import Producto


from django.shortcuts import render, redirect
from django.forms import modelformset_factory

from .models import OrdenCompra, Item, Producto
from .forms import OrdenForm, ItemForm


# 👉 Auxiliar para formatear números con puntos de miles
def formato_numero(valor):
    try:
        valor = float(valor)
        return f"{valor:,.0f}".replace(",", ".")
    except:
        return valor


# -------------------- AUTENTICACIÓN --------------------

# 🔹 Login
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("orden_list")
            else:
                messages.error(request, "Tu cuenta aún no ha sido aprobada por el administrador.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "COTIFAC/login.html")


# 🔹 Logout
def logout_view(request):
    logout(request)
    return redirect("login")

# 🔹 Registro
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ese usuario ya existe.")
        else:
            # Crear usuario pero desactivado
            user = User.objects.create_user(username=username, password=password)
            user.is_active = False
            user.save()

            messages.success(request, "Registro enviado. Un administrador debe aprobar tu cuenta.")
            return redirect("login")

    return render(request, "COTIFAC/register.html")


# -------------------- ORDENES --------------------

@login_required
def orden_list(request):
    if request.user.is_superuser:
        ordenes = OrdenCompra.objects.all()
    else:
        ordenes = OrdenCompra.objects.filter(usuario=request.user)
    return render(request, "COTIFAC/orden_list.html", {"ordenes": ordenes})


@login_required
def crear_orden(request):
    ItemFormSet = modelformset_factory(Item, form=ItemForm, extra=5, can_delete=False)
    productos = Producto.objects.all()

    productos_json = {
        str(p.id): {
            "descripcion": f"{p.tipo} {p.codigo} {p.medida}",
            "precio": float(p.precio),
        }
        for p in productos
    }

    if request.method == "POST":
        form = OrdenForm(request.POST)
        formset = ItemFormSet(request.POST, queryset=Item.objects.none())

        if form.is_valid() and formset.is_valid():
            # --- Guardar la orden principal ---
            orden = form.save(commit=False)
            orden.usuario = request.user
            orden.save()

            # --- Guardar los ítems normales ---
            items = formset.save(commit=False)
            for item in items:
                item.orden = orden
                item.save()

            # --- Guardar productos especiales (hasta 4) ---
            for i in range(1, 5):
                esp_tipo = request.POST.get(f"especial_tipo_{i}", "").strip()
                esp_cant = request.POST.get(f"especial_cantidad_{i}", "").strip()
                esp_prec = request.POST.get(f"especial_precio_{i}", "").strip()

                if esp_tipo and esp_cant and esp_prec:
                    try:
                        cantidad = int(esp_cant)
                        precio = Decimal(esp_prec)
                    except:
                        continue  # Si algún valor no es numérico, salta esta fila

                    # 👇 Guardamos como item sin producto asociado (solo con la descripción)
                    Item.objects.create(
                        orden=orden,
                        producto=None,
                        descripcion=esp_tipo,  # se usa lo que escribas
                        cantidad=cantidad,
                        precio=precio,
                    )

            return redirect("orden_list")

    else:
        form = OrdenForm()
        formset = ItemFormSet(queryset=Item.objects.none())

    return render(request, "COTIFAC/orden_form.html", {
        "form": form,
        "formset": formset,
        "productos_json": json.dumps(productos_json),
    })


@login_required
def orden_delete(request, pk):
    orden = get_object_or_404(OrdenCompra, pk=pk)
    if request.user == orden.usuario or request.user.is_superuser:
        orden.delete()
    return redirect("orden_list")


@login_required
def orden_aprobar(request, pk):
    orden = get_object_or_404(OrdenCompra, pk=pk)
    if request.user.is_superuser:
        orden.estado = "aprobada"
        orden.save()
    return redirect("orden_list")


@login_required
def orden_rechazar(request, pk):
    orden = get_object_or_404(OrdenCompra, pk=pk)
    if request.user.is_superuser:
        orden.estado = "rechazada"
        orden.save()
    return redirect("orden_list")


@login_required
def orden_pdf(request, pk):
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    )
    from reportlab.platypus import PageBreak, ListFlowable, ListItem
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from decimal import Decimal
    import os

    orden = get_object_or_404(OrdenCompra, pk=pk)

    # --- Configuración del PDF ---


    response = HttpResponse(content_type='application/pdf')
    # Normalizar nombre del cliente (sin espacios ni caracteres raros)
    cliente_nombre = orden.comprador.strip().replace(" ", "_").replace("/", "_")
    response['Content-Disposition'] = f'attachment; filename=Cotizacion-{cliente_nombre}.pdf'

    doc = SimpleDocTemplate(response, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []
    styles = getSampleStyleSheet()

    # --- Estilos base ---
    title = ParagraphStyle('title', fontSize=18, alignment=1, leading=22, spaceAfter=6, fontName="Helvetica-Bold")
    subtitle = ParagraphStyle('subtitle', fontSize=11, alignment=1, textColor=colors.HexColor("#7a7a7a"), fontName="Helvetica-Oblique")
    normal = styles['Normal']
    normal.fontSize = 10
    bold = ParagraphStyle('bold', parent=normal, fontName="Helvetica-Bold")
    small = ParagraphStyle('small', parent=normal, fontSize=9)


    section = ParagraphStyle(
        'section',
        parent=bold,
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6
    )






    # --- Fondo (borde crema y centro blanco) ---
    from reportlab.pdfgen.canvas import Canvas
    def fondo(canvas, doc):
        canvas.saveState()
        # Fondo completo crema
        canvas.setFillColor(colors.HexColor("#d6dacb"))
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        # Rectángulo blanco central
        canvas.setFillColor(colors.white)
        canvas.rect(1*cm, 1*cm, A4[0]-2*cm, A4[1]-2*cm, fill=1, stroke=0)
        canvas.restoreState()

    # --- Logo ---
    from django.conf import settings
    logo_path = os.path.join(settings.BASE_DIR, "COTIFAC", "static", "images", "logoo.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5.1*cm, height=4*cm)
        logo.hAlign = 'CENTER'
        elements.append(Spacer(1, 10))
        elements.append(logo)

    elements.append(Paragraph("LA CASA DE LOS GANSOS", title))
    elements.append(Paragraph("Plumones y almohadas", subtitle))
    elements.append(Spacer(1, 12))

    # --- Encabezado de cotización ---
    # --- Encabezado de cotización ---
    titulo_cotizacion = Paragraph(
        f"<b>COTIZACIÓN N° {orden.id:06d}</b>",
        styles["Normal"]
    )

    # Línea de cotización centrada
    tabla_titulo = Table([[titulo_cotizacion]], colWidths=[17*cm])
    tabla_titulo.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(tabla_titulo)
    elements.append(Spacer(1, 6))

    # --- Datos del cliente, vendedor, fecha y estado ---
    info_data = [
        ["Cliente:", orden.comprador, "Fecha:", str(orden.fecha_emision)],
    ]


    tabla_info = Table(info_data, colWidths=[2*cm, 6*cm, 2*cm, 6*cm])
    tabla_info.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(tabla_info)
    elements.append(Spacer(1, 12))




        # --- Tabla de productos ---
    # --- Tabla de productos ---
    # --- Tabla de productos ---
    # --- Tabla de productos ---
    data = [["Producto/Descripción", "Unidades", "Precio unitario", "Total"]]

    for item in orden.items.all():
        # Si el producto existe, usa su nombre completo
        if item.producto:
            descripcion_final = f"{item.producto.tipo} {item.producto.codigo} {item.producto.medida}".strip()
        else:
            # Si es producto especial, mostrar solo lo que escribió el usuario
            descripcion_final = item.descripcion.strip() if item.descripcion else ""

        data.append([
            descripcion_final,
            str(item.cantidad),
            f"${formato_numero(item.precio)}",
            f"${formato_numero(item.subtotal())}"
        ])

    # --- Configuración visual igual que antes ---
    tabla = Table(data, colWidths=[10*cm, 2*cm, 3*cm, 3*cm])
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(tabla)
    elements.append(Spacer(1, 14))










    # --- Totales ---
    subtotal = sum(item.subtotal() for item in orden.items.all())
    descuento = subtotal * (Decimal(orden.descuento) / Decimal(100))
    total = subtotal - descuento

        # 👇 Redondear descuento limpio (sin .00)
    descuento_str = f"{orden.descuento:.0f}" if orden.descuento % 1 == 0 else f"{orden.descuento}"

    totales = [
    [Paragraph("Valor total:", styles["Normal"]),
     Paragraph(f"${formato_numero(subtotal)}", styles["Normal"])],
    [Paragraph(f"Descuento transferencia electrónica {descuento_str}%:", styles["Normal"]),
     Paragraph(f"- ${formato_numero(descuento)}", styles["Normal"])],
    [Paragraph("<b>Valor Final:</b>", styles["Normal"]),
     Paragraph(f"<b>${formato_numero(total)}</b>", styles["Normal"])],
]


    tabla_totales = Table(totales, colWidths=[13*cm, 4*cm])
    tabla_totales.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F2F2F2")),  # fondo gris claro solo en total
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(tabla_totales)
    elements.append(Spacer(1, 16))


    # --- Condiciones de pago ---
    # --- Guardamos el contenido principal (todo lo de arriba) ---
    def footer(canvas, doc):
        """Dibuja las condiciones de pago y el pie de contacto al fondo del PDF."""
        canvas.saveState()

        # Línea separadora gris
        canvas.setStrokeColor(colors.HexColor("#CCCCCC"))
        canvas.setLineWidth(0.5)
        canvas.line(2*cm, 5*cm, A4[0] - 2*cm, 5*cm)

        # Encabezado "CONDICIONES DE PAGO"
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(colors.HexColor("#333333"))
        canvas.drawString(2*cm, 4.6*cm, "CONDICIONES DE PAGO")

        # Texto con bullets
        canvas.setFont("Helvetica", 9)
        fecha_despacho = orden.fecha_vencimiento.strftime("%d-%m-%Y") if orden.fecha_vencimiento else "Por confirmar"

        text_lines = [
            "Pago mediante transferencia electrónica (con descuento) / Link de pago (3 cuotas sin interés).",
            "Incluye costos de despacho.",
            "Factibilidad de boleta/factura según requerimiento. (Favor informar con anterioridad).",
            "La entrega se realizará únicamente una vez confirmada la disponibilidad de los fondos en nuestra cuenta,",
            "independiente del medio de pago utilizado.",
            f"Fecha estimada de despacho (mediante empresa Blue Express Copec): {fecha_despacho}.",
            "Abono 50% previo a inicio de pedidos especiales."
        ]


        y = 4.2*cm
        for line in text_lines:
            # Dibuja el bullet
            canvas.circle(2.1*cm - 1.5, y + 2, 1.2, fill=1)
            # Texto de la línea
            canvas.drawString(2.4*cm, y, line)
            y -= 0.4*cm

        # Pie de contacto
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawCentredString(
            A4[0] / 2,
            1.2*cm,
            "Avenida Gramados 2 – Puerto Varas – Chile | lacasadelosgansos@gmail.com | +56 9 6357 6718"
        )

        canvas.restoreState()


    # --- Compilamos el PDF con fondo y footer ---

    # --------- PÁGINA 2: Políticas / Condiciones ----------
    elements.append(PageBreak())

    # Título de la página 2
    elements.append(Paragraph("LA CASA DE LOS GANSOS", title))
    elements.append(Paragraph("Plumones y almohadas", subtitle))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Condiciones de cambios y devoluciones</b>", styles["Normal"]))
    elements.append(Spacer(1, 8))

    # 1. Cambios voluntarios
    elements.append(Paragraph("1. Cambios voluntarios", section))
    elements.append(Paragraph(
        "Por motivos de higiene y por tratarse de productos de uso personal, no se aceptarán cambios ni "
        "devoluciones si el producto ha sido abierto o utilizado, salvo en caso de falla objetiva y "
        "comprobable de fabricación.", normal))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "Si el producto no ha sido abierto, se encuentra en su empaque original, sellado y sin uso, "
        "aceptaremos la solicitud de cambio presentada dentro de los 10 días corridos siguientes a su "
        "recepción por el cliente, previa evaluación del estado del producto.", normal))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "Los costos de envío asociados a este tipo de cambios serán de cargo del cliente.", normal))

    # 2. Derecho de retracto
    elements.append(Paragraph("2. Derecho de retracto", section))
    elements.append(Paragraph(
        "De acuerdo con el artículo 3 bis letra b) de la Ley N° 19.496 sobre Protección de los Derechos "
        "de los Consumidores, informamos que nuestros productos están excluidos del derecho de retracto, "
        "debido a que corresponden a bienes de uso personal e higiénico. Esta exclusión es informada "
        "previamente y aceptada expresamente por el cliente antes de completar la compra.", normal))

    # 3. Productos con fallas
    elements.append(Paragraph("3. Productos con fallas", section))
    elements.append(Paragraph(
        "Nuestros productos se confeccionan de manera artesanal, por lo que podrían presentar ligeras "
        "variaciones en las medidas informadas o en las terminaciones que presenta un producto respecto "
        "de otro; diferencias propias del proceso de fabricación. Estas variaciones no constituyen fallas. "
        "Asimismo, al tratarse de materiales de origen natural, como la pluma, podrían presentar un ligero "
        "olor propio del material aun después de su tratamiento. Esta condición no se considera un defecto.", normal))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("En caso de falla objetiva y comprobable, el cliente podrá optar por:", normal))

    # Lista con viñetas (corregida y alineada)
    from reportlab.lib.enums import TA_LEFT

    bullet_style = ParagraphStyle(
        'bullet_style',
        parent=normal,
        leftIndent=20,
        bulletIndent=10,
        spaceBefore=2,
        spaceAfter=2,
        alignment=TA_LEFT
    )

    items = [
        Paragraph("• Reparación gratuita", bullet_style),
        Paragraph("• Cambio del producto", bullet_style),
        Paragraph("• Devolución del dinero", bullet_style),
    ]

    for item in items:
        elements.append(item)

    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Este derecho podrá ejercerse dentro de los 6 meses siguientes a la recepción del producto.",
        normal
    ))


    # 4. Contacto
    elements.append(Paragraph("4. Contacto", section))
    elements.append(Paragraph(
        "Para gestionar un cambio, devolución o reclamo, contáctanos a "
        "lacasadelosgansos@gmail.com, indicando tu número de pedido, una breve descripción del caso "
        "y adjuntando imágenes de respaldo.", normal))



    doc.build(
        elements,
        onFirstPage=lambda canvas, doc: (fondo(canvas, doc), footer(canvas, doc)),
        onLaterPages=fondo
    )
    return response




