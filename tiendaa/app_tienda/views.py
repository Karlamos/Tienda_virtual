from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from decimal import Decimal
from django.contrib.auth.models import Group
from .models import (
    Pedido, Producto, Cupon,
    ConfiguracionIVA, PedidoProducto, Factura, Devolucion
)
from .forms import *
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import logout # Importante importar esto




def logout_view(request):
    logout(request)
    return redirect('catalogo_publico')

def ver_carrito(request):
    carrito = request.session.get('carrito', {})
    total = Decimal('0.00')
    
    # Calculamos los subtotales aquí para no hacerlo en el HTML
    for item in carrito.values():
        item['subtotal_item'] = Decimal(item['precio']) * item['cantidad']
        total += item['subtotal_item']
        
    return render(request, 'carrito.html', {
        'carrito': carrito, 
        'total': total
    })



# Funciones de verificación de Rol
def es_bodeguero(user):
    return user.groups.filter(name='Bodeguero').exists() or user.is_superuser

def es_administrador(user):
    return user.groups.filter(name='Administrador').exists() or user.is_superuser

def es_financiero(user):
    return user.groups.filter(name='Financiero').exists() or user.is_superuser

@user_passes_test(es_bodeguero)
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('catalogo_publico')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'crear_producto.html', {'form': form, 'editando': True})

# --- ELIMINAR PRODUCTO ---
@user_passes_test(es_bodeguero)
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        return redirect('catalogo_publico')
    return render(request, 'confirmar_eliminar.html', {'producto': producto})

@user_passes_test(es_bodeguero)
def crear_producto(request):
    if request.method == 'POST':
        # IMPORTANTE: request.FILES es necesario para las imágenes
        form = ProductoForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            return redirect('catalogo_publico')
    else:
        form = ProductoForm()
    return render(request, 'crear_producto.html', {'form': form})


# --- VISTAS DE BODEGA ---
@user_passes_test(es_bodeguero)
def gestion_bodega(request):
    pedidos = Pedido.objects.all().order_by('-fecha')
    return render(request, 'ordenes.html', {'pedidos': pedidos})

@user_passes_test(es_bodeguero)
def procesar_despacho(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if request.method == 'POST':
        pedido.estado = request.POST.get('estado')
        pedido.save()
    return redirect('gestion_bodega')

@user_passes_test(es_bodeguero)
def registrar_devolucion(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    if request.method == 'POST':
        prod_id = request.POST.get('producto_id')
        cant = int(request.POST.get('cantidad'))
        producto = Producto.objects.get(id=prod_id)
        
        # Crear registro de devolución
        Devolucion.objects.create(pedido=pedido, producto=producto, cantidad=cant, motivo="Devolución de cliente")
        
        # Retornar al inventario
        producto.stock += cant
        producto.save()
    return redirect('gestion_bodega')

@user_passes_test(es_bodeguero)
def actualizar_estado_pedido(request, pedido_id):
    pedido = Pedido.objects.get(id=pedido_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        pedido.estado = nuevo_estado
        pedido.save()
    return redirect('gestion_bodega')

# --- VISTAS MÓDULO FINANCIERO (3.3) ---
@user_passes_test(es_financiero)
def configuracion_iva(request):
    config = ConfiguracionIVA.objects.last()
    if request.method == 'POST':
        nuevo_iva = request.POST.get('porcentaje')
        ConfiguracionIVA.objects.create(porcentaje=nuevo_iva) # Creamos uno nuevo para mantener historial
        return redirect('configuracion_iva')
    return render(request, 'financiero/iva.html', {'config': config})

# --- VISTAS DE ADMINISTRADOR ---
@user_passes_test(es_administrador)
def gestionar_cupones(request):
    cupones = Cupon.objects.all()
    # Lógica para crear o desactivar cupones
    return render(request, 'admin/cupones.html', {'cupones': cupones})

def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            # 1. Guardamos el usuario pero no en la base de datos aún si usas un UserCreationForm personalizado
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            user.set_password(password)
            user.save()
            # 2. Obtenemos o creamos el grupo 'cliente'
            # Esto evita el error "Group matching query does not exist"
            grupo, created = Group.objects.get_or_create(name='cliente')
            if created:
                print("¡Se ha creado el grupo cliente por primera vez!")
            # 3. Asignamos el usuario al grupo
            user.groups.add(grupo)
            
            return redirect('login') # O a la página que prefieras
    else:
        form = RegistroForm()
    
    return render(request, 'registro.html', {'form': form})



@login_required(login_url='/login/')
def checkout_view(request):
    carrito = request.session.get('carrito', {})

    if not carrito:
        return redirect('/catalogo_publico/')

    if request.method == 'POST':
        direccion = request.POST.get('direccion')
        codigo_cupon = request.POST.get('cupon')

        if not direccion:
            return render(request, 'checkout.html', {
                'error': 'La dirección es obligatoria',
                'carrito': carrito
            })

        subtotal = Decimal('0.00')

        for item in carrito.values():
            subtotal += Decimal(item['precio']) * item['cantidad']

        # IVA dinámico
        iva_config = ConfiguracionIVA.objects.last()
        iva_porcentaje = iva_config.porcentaje
        iva_valor = subtotal * (iva_porcentaje / 100)

        descuento = Decimal('0.00')
        cupon_obj = None

        if codigo_cupon:
            try:
                cupon_obj = Cupon.objects.get(
                    codigo=codigo_cupon,
                    activo=True
                )
                descuento = subtotal * (Decimal(cupon_obj.descuento_porcentaje) / 100)
            except Cupon.DoesNotExist:
                pass

        total = subtotal - descuento + iva_valor

        pedido = Pedido.objects.create(
            cliente=request.user,
            direccion_envio=direccion,
            iva_aplicado=iva_porcentaje,
            subtotal=subtotal,
            descuento=descuento,
            total=total
        )

        # Guardar productos y descontar stock
        for item in carrito.values():
            producto = Producto.objects.get(id=item['id'])

            PedidoProducto.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=item['cantidad'],
                precio_unitario=item['precio']
            )

            producto.stock -= item['cantidad']
            producto.save()

        # Factura ficticia
        Factura.objects.create(
            pedido=pedido,
            documento_digital='facturas/factura_placeholder.pdf'
        )

        request.session['carrito'] = {}

        return render(request, 'confirmacion.html', {
            'pedido': pedido
        })

    return render(request, 'checkout.html', {'carrito': carrito})
    


# Función para verificar si el usuario es del área financiera
def es_financiero(user):
    return user.groups.filter(name='Financiero').exists() or user.is_superuser


@user_passes_test(es_financiero)
def reporte_financiero(request):
    ingresos = Pedido.objects.filter(
        estado='Entregado'
    ).aggregate(Sum('total'))['total__sum'] or 0

    pendientes = Pedido.objects.filter(
        estado='Pendiente'
    ).count()

    return render(request, 'reporte.html', {
        'ingresos': ingresos,
        'pendientes': pendientes
    })


def catalogo_publico(request):
    productos = Producto.objects.all()
    return render(request, 'catalogo.html', {
        'productos': productos
    })


@user_passes_test(lambda u: u.is_superuser)
def crear_empleado(request):
    if request.method == 'POST':
        form = CrearEmpleadoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_usuarios') # O a donde prefieras
    else:
        form = CrearEmpleadoForm()
    return render(request, 'crear_empleado.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def lista_usuarios(request):
    usuarios = User.objects.all().order_by('-date_joined')
    return render(request, 'lista_usuarios.html', {'usuarios': usuarios})

# Añade esta vista para generar el documento de salida física
@user_passes_test(es_bodeguero)
def imprimir_orden_despacho(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    # Obtenemos los productos asociados a ese pedido
    items = PedidoProducto.objects.filter(pedido=pedido)
    return render(request, 'bodega/orden_despacho_print.html', {
        'pedido': pedido,
        'items': items
    })
    
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = request.session.get('carrito', {})

    id_str = str(producto.id)
    if id_str in carrito:
        # Validar que no agregue más del stock disponible desde el catálogo
        if carrito[id_str]['cantidad'] < producto.stock:
            carrito[id_str]['cantidad'] += 1
    else:
        carrito[id_str] = {
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': str(producto.precio_base),
            'cantidad': 1,
            'stock': producto.stock, # <--- IMPORTANTE: Guardamos el stock aquí
            'imagen': producto.imagen.url if producto.imagen else ''
        }

    request.session['carrito'] = carrito
    return redirect('catalogo_publico')

def eliminar_del_carrito(request, producto_id):
    carrito = request.session.get('carrito', {})
    if str(producto_id) in carrito:
        del carrito[str(producto_id)]
        request.session['carrito'] = carrito
    return redirect('carrito')

def actualizar_carrito(request, producto_id):
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))
        producto = get_object_or_404(Producto, id=producto_id)
        carrito = request.session.get('carrito', {})

        # Validación de Stock
        if cantidad > producto.stock:
            cantidad = producto.stock # Forzamos al máximo disponible

        id_str = str(producto_id)
        if id_str in carrito:
            carrito[id_str]['cantidad'] = cantidad
            request.session['carrito'] = carrito
            
    return redirect('carrito')

def procesar_pago(request):
    carrito = request.session.get('carrito', {})
    
    for item_id, item in carrito.items():
        producto = Producto.objects.get(id=item['id'])
        # Restamos del stock
        producto.stock -= int(item['cantidad'])
        producto.save()
        
    # Limpiamos el carrito después del pago
    request.session['carrito'] = {}
    return redirect('catalogo')