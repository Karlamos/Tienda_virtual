from django.contrib import admin
from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView 
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', catalogo_publico, name='catalogo_publico'),
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
    path('bodega/', gestion_bodega, name='gestion_bodega'),
    path('bodega/actualizar/<int:pedido_id>/', actualizar_estado_pedido, name='actualizar_estado_pedido'),
    path('bodega/devolucion/<int:pedido_id>/', registrar_devolucion, name='registrar_devolucion'),
    path('agregar-carrito/<int:producto_id>/', agregar_al_carrito, name='agregar_carrito'),
    path('eliminar-carrito/<int:producto_id>/', eliminar_del_carrito, name='eliminar_carrito'),
    path('actualizar-carrito/<int:producto_id>/', actualizar_carrito, name='actualizar_carrito'),
    path('pagar/', procesar_pago, name='procesar_pago'),
]

