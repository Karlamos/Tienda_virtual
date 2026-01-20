from django.db import models
from django.db import models
from django.contrib.auth.models import User

class ConfiguracionIVA(models.Model):
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=15.0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

# Módulo Financiero y Tributario [cite: 21]
class ConfiguracionIVA(models.Model):
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=15.0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    # Solo el financiero puede modificar esto vía permisos de Django [cite: 24]

# Módulo de Clientes y Ventas [cite: 7]
class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    # Este campo es el que activa el botón en el formulario
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)

    def __str__(self):
        return self.nombre




class Cupon(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    descuento_porcentaje = models.IntegerField()
    activo = models.BooleanField(default=True)

class Pedido(models.Model):

    ESTADOS = (
        ('Pendiente', 'Pendiente'),
        ('Enviado', 'Enviado'),
        ('Entregado', 'Entregado'),
    )
    cliente = models.ForeignKey(User, on_delete=models.CASCADE)
    direccion_envio = models.TextField() # [cite: 12]
    fecha = models.DateTimeField(auto_now_add=True)
    iva_aplicado = models.DecimalField(max_digits=5, decimal_places=2) # [cite: 25]
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente') # [cite: 17]


class PedidoProducto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)


class Factura(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE)
    documento_digital = models.FileField(upload_to='facturas/') # [cite: 14]


class Devolucion(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1) # <-- Muy importante
    motivo = models.TextField()
    fecha_devolucion = models.DateTimeField(auto_now_add=True)
    procesado = models.BooleanField(default=False)
    
