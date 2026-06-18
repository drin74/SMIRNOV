# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='📧 Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'your@email.com'
        }),
        help_text='Введите действительный email адрес'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': '👤 Имя пользователя',
            'password1': '🔑 Пароль',
            'password2': '🔐 Подтверждение пароля',
        }
        help_texts = {
            'username': 'Не более 150 символов. Только буквы, цифры и @/./+/-/_',
            'password1': 'Минимум 8 символов',
            'password2': 'Введите тот же пароль для подтверждения',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Добавляем стили и placeholder
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Имя пользователя'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Пароль'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Подтвердите пароль'
        })

        # Перевод ошибок
        self.fields['username'].error_messages = {
            'required': 'Введите имя пользователя',
            'unique': 'Это имя уже занято',
            'invalid': 'Недопустимое имя',
        }
        self.fields['email'].error_messages = {
            'required': 'Введите email',
            'invalid': 'Введите действительный email адрес',
        }
        self.fields['password1'].error_messages = {
            'required': 'Введите пароль',
            'password_too_similar': 'Пароль слишком похож на другую информацию',
            'password_too_short': 'Пароль должен содержать минимум 8 символов',
            'password_too_common': 'Пароль слишком простой',
            'password_entirely_numeric': 'Пароль не может состоять только из цифр',
        }
        self.fields['password2'].error_messages = {
            'required': 'Подтвердите пароль',
            'password_mismatch': 'Пароли не совпадают',
        }


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='👤 Имя пользователя',
        widget=forms.TextInput(attrs={'placeholder': 'Имя пользователя'})
    )
    password = forms.CharField(
        label='🔑 Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Пароль'})
    )

    error_messages = {
        'invalid_login': 'Неверное имя пользователя или пароль',
        'inactive': 'Этот аккаунт не активен',
    }