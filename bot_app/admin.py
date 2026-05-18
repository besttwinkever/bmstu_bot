from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from oauth.models import OauthUser

from bot_app.models import TgUser, Discipline, Notification
from bot_app.services.auth import AuthService


# Однократно проставляем заголовки админки — иначе Django + перевод
# показывают «Администрирование Django», что не подходит проекту МГТУ.
admin.site.site_title = 'Панель администратора'
admin.site.site_header = 'Панель администратора'
admin.site.index_title = 'Панель администратора'


@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'messenger_id')
    list_filter = ('platform',)
    search_fields = (
        'user__username', 'user__first_name', 'user__last_name',
        'messenger_id',
    )


# OauthUser должен идти под полноценным UserAdmin
try:
    admin.site.unregister(OauthUser)
except admin.sites.NotRegistered:
    pass


@admin.register(OauthUser)
class OauthUserAdmin(DjangoUserAdmin):
    pass


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('name', 'teachers_list', 'groups_list')
    search_fields = ('name',)
    filter_horizontal = ('teachers', 'groups')

    def get_queryset(self, request):
        # Без prefetch list_display даёт N+1 — по два запроса на каждую дисциплину.
        return super().get_queryset(request).prefetch_related('teachers', 'groups')

    @admin.display(description='Преподаватели')
    def teachers_list(self, obj):
        return ', '.join(t.get_full_name() or t.username for t in obj.teachers.all()) or '—'

    @admin.display(description='Учебные группы')
    def groups_list(self, obj):
        return ', '.join(g.name for g in obj.groups.all()) or '—'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'groups':
            kwargs['queryset'] = Group.objects.exclude(
                name__in=AuthService.role_group_names()
            ).order_by('name')
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == 'teachers':
            field.label_from_instance = lambda obj: obj.get_full_name() or obj.username
        return field


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('discipline', 'short_text', 'created_at', 'scheduled_at', 'is_sent')
    list_filter = ('is_sent', 'discipline')
    search_fields = ('text', 'discipline__name')
    ordering = ('-created_at',)

    @admin.display(description='Текст')
    def short_text(self, obj):
        text = obj.text or ''
        return f'{text[:80]}...' if len(text) > 80 else text
