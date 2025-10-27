from django import template

register = template.Library()

@register.filter
def formato_moneda(value):
    try:
        valor = float(value)
        return f"{valor:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return value
