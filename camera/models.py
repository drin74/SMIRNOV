from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User  # ← Добавьте это!
import os


class UploadedVideo(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    video_file = models.FileField(upload_to='videos/%Y/%m/%d/', verbose_name="Видео файл")
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name="Дата загрузки")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Загрузил",null=True,blank=True )

    class Meta:
        verbose_name = "Видео"
        verbose_name_plural = "Видео"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def get_file_name(self):
        return os.path.basename(self.video_file.name)

    def get_file_size(self):
        if self.video_file:
            size = self.video_file.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.2f} {unit}"
                size /= 1024
        return "0 B"

