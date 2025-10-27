from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    path("", views.orden_list, name="orden_list"),
    path("nueva/", views.crear_orden, name="orden_create"),
    path("pdf/<int:pk>/", views.orden_pdf, name="orden_pdf"),
    path("delete/<int:pk>/", views.orden_delete, name="orden_delete"),
    path("orden/<int:pk>/aprobar/", views.orden_aprobar, name="orden_aprobar"),
    path("orden/<int:pk>/rechazar/", views.orden_rechazar, name="orden_rechazar"),
]
