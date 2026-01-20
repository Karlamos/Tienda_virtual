from django import forms
from django.contrib.auth.models import User, Group
from .models import Producto 

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password2'):
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data



class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        # Asegúrate de agregar 'imagen' aquí adentro
        fields = ['nombre', 'precio_base', 'stock', 'imagen'] 
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'precio_base': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CrearEmpleadoForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    # Definimos las opciones de roles manualmente o desde la DB
    ROL_CHOICES = [
        ('Bodeguero', 'Bodeguero'),
        ('Administrador', 'Administrador'),
        ('Financiero', 'Financiero'),
    ]
    rol = forms.ChoiceField(choices=ROL_CHOICES, label="Asignar Rol")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            # Asignar el grupo según el rol seleccionado
            nombre_rol = self.cleaned_data.get('rol')
            grupo, created = Group.objects.get_or_create(name=nombre_rol)
            user.groups.add(grupo)
        return user