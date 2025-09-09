from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand
from django.db import transaction
from oauth.models import OauthUser


class Command(BaseCommand):
    help = 'Bootstrapping database with necessary items'

    def add_arguments(self, parser):
        parser.add_argument('admins', type=str, help='coma-separated list of admins to create')

    @transaction.atomic()
    def handle(self, *args, **options):
        for username in options['admins'].split(','):
            if not OauthUser.objects.filter(username=username).exists():
                print(f'Creating new admins {username}')
                user = OauthUser.objects.create_user(username, password="ChangeMe123!", is_staff=True, is_superuser=True)
