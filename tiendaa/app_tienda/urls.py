from django.contrib import admin
from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView 
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', catalogo_publico, name='catalogo'),
    path('reporte/', reporte_financiero, name='reporte_financiero'),
    path('checkout/', checkout_view, name='checkout'),
    path('registro/', registro_view, name='registro'),
    path('logout/', logout_view, name='logout'),
    path('login/',auth_views.LoginView.as_view(template_name='login.html'),name='login'),
    path('carrito/', ver_carrito, name='carrito'),
    path('nuevo-producto/', crear_producto, name='crear_producto'),
    path('editar-producto/<int:producto_id>/', editar_producto, name='editar_producto'),
    path('eliminar-producto/<int:producto_id>/', eliminar_producto, name='eliminar_producto'),
    path('usuarios-tienda/usuarios/', lista_usuarios, name='lista_usuarios'),
    path('usuarios-tienda/nuevo-empleado/', crear_empleado, name='crear_empleado'),

]
