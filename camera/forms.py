from django import forms
from .models import UploadedVideo

class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedVideo
        fields = ['title', 'video_file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название видео'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Описание (необязательно)',
                'rows': 3
            }),
        }