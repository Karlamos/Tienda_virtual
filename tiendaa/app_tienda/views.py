from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from decimal import Decimal
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from .models import (
    Pedido, Producto, Cupon,
    ConfiguracionIVA, PedidoProducto, Factura, Devolucion
)
from .forms import *
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import logout 
from django.contrib.admin.views.decorators import staff_member_required




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
    return render(request, 'bodega/ordenes.html', {'pedidos': pedidos})

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
    return render(request, 'financiero/configurar_iva.html', {'config': config})

# --- VISTAS DE ADMINISTRADOR ---
@user_passes_test(es_administrador)
@user_passes_test(lambda u: u.groups.filter(name='Administrador').exists() or u.is_superuser)
def gestionar_cupones(request):
    if request.method == 'POST':
        # .strip() elimina espacios accidentales
        codigo = request.POST.get('codigo', '').strip().upper()
        porcentaje = request.POST.get('descuento')

        if codigo and porcentaje:
            # Usamos update_or_create para evitar errores si el código se repite
            # o simplemente .create()
            Cupon.objects.create(
                codigo=codigo, 
                descuento_porcentaje=int(porcentaje),
                activo=True
            )
            return redirect('gestionar_cupones') # Recarga la página para mostrar el nuevo

    # Obtenemos todos los cupones para mostrarlos en la tabla
    cupones = Cupon.objects.all().order_by('-fecha_creacion')
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
from django.http import HttpResponse
from django.template.loader import render_to_string
# (Mantén tus otros imports igual)

@login_required(login_url='/login/')
def checkout_view(request):
    carrito = request.session.get('carrito', {})

    if not carrito:
        return redirect('/catalogo_publico/')

    if request.method == 'POST':
        direccion = request.POST.get('direccion')
        # Limpiamos el código del cupón (quitar espacios y poner en mayúsculas)
        codigo_cupon = request.POST.get('cupon', '').strip().upper()

        if not direccion:
            return render(request, 'checkout.html', {
                'error': 'La dirección es obligatoria',
                'carrito': carrito
            })

        subtotal = Decimal('0.00')
        for item in carrito.values():
            subtotal += Decimal(str(item['precio'])) * item['cantidad']

        # 1. LÓGICA DE CUPÓN: Validar si existe y está activo
        descuento = Decimal('0.00')
        if codigo_cupon:
            try:
                cupon_obj = Cupon.objects.get(codigo=codigo_cupon, activo=True)
                # Calculamos el porcentaje sobre el subtotal
                descuento = (subtotal * Decimal(str(cupon_obj.descuento_porcentaje / 100))).quantize(Decimal('0.01'))
            except Cupon.DoesNotExist:
                # Si el cupón no es válido, el descuento sigue en 0
                pass

        # 2. IVA DINÁMICO: Se aplica sobre el subtotal ya descontado
        iva_config = ConfiguracionIVA.objects.last()
        iva_porcentaje = iva_config.porcentaje if iva_config else Decimal('15.00')
        
        # El impuesto se calcula sobre (Subtotal - Descuento)
        base_imponible = subtotal - descuento
        iva_valor = (base_imponible * (iva_porcentaje / 100)).quantize(Decimal('0.01'))

        # 3. TOTAL FINAL (Redondeado a 2 decimales para evitar el error de tus fotos)
        total = (base_imponible + iva_valor).quantize(Decimal('0.01'))

        # 4. CREAR EL PEDIDO
        pedido = Pedido.objects.create(
            cliente=request.user,
            direccion_envio=direccion,
            iva_aplicado=iva_porcentaje,
            subtotal=subtotal,
            descuento=descuento,
            total=total
        )

        # 5. GUARDAR PRODUCTOS Y ACTUALIZAR STOCK
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

        # 6. REGISTRO DE FACTURA
        Factura.objects.create(
            pedido=pedido,
            documento_digital='facturas/factura_placeholder.pdf'
        )

        # Limpiar carrito y enviar datos a la confirmación
        request.session['carrito'] = {}

        return render(request, 'confirmacion.html', {
            'pedido': pedido,
            'iva_total': iva_valor # Pasamos el IVA calculado para el diseño
        })

    return render(request, 'checkout.html', {'carrito': carrito})

# Vista para la Factura Digital (Módulo 3.1)
@login_required
def ver_factura(request, pedido_id):
# Traemos el pedido (solo si pertenece al usuario logueado)
    pedido = get_object_or_404(Pedido, id=pedido_id, cliente=request.user)
    
    # Calculamos el IVA total para que se muestre correctamente en el diseño
    # Basado en la lógica de tu checkout
    iva_total = (pedido.subtotal - pedido.descuento) * (pedido.iva_aplicado / 100)
    
    # USAMOS confirmacion.html porque ya tiene tu diseño y colores
    return render(request, 'confirmacion.html', {
        'pedido': pedido,
        'iva_total': iva_total
    })

# Reporte Financiero Completo (Módulo 3.3)
@user_passes_test(es_financiero)
def reporte_financiero(request):
    # Cálculos globales (Resumen de las tarjetas)
    ingresos_reales = Pedido.objects.filter(estado='Entregado').aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    por_cobrar = Pedido.objects.exclude(estado='Entregado').aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    
    # Cálculo de pérdidas por devoluciones
    from django.db.models import F
    devoluciones_monto = Devolucion.objects.aggregate(
        total=Sum(F('cantidad') * F('producto__precio_base'))
    )['total'] or Decimal('0.00')
    
    # Lista de TODAS las facturas para la tabla del template
    todas_las_facturas = Pedido.objects.all().order_by('-fecha')
    
    return render(request, 'financiero/reporte.html', {
        'ingresos': ingresos_reales,
        'pendientes_monto': por_cobrar,
        'devoluciones_monto': devoluciones_monto,
        'facturas': todas_las_facturas  # Esta es la lista que recorreremos
    })



@login_required(login_url='/login/')
def mis_compras(request):
    # Obtenemos solo los pedidos del usuario actual, ordenados por los más recientes
    pedidos = Pedido.objects.filter(cliente=request.user).order_by('-fecha')
    return render(request, 'mis_compras.html', {'pedidos': pedidos})

@staff_member_required
def alternar_estado_usuario(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    # Cambia el estado al opuesto
    usuario.is_active = not usuario.is_active
    usuario.save()
    return redirect('lista_usuarios')