import csv
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from athletes.models import Athlete
from teams.models import Team


class Command(BaseCommand):
    help = 'alpha_academy_liste.txt dosyasındaki sporcuları içeri aktarır.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='alpha_academy_liste.txt',
            help='İçe aktarılacak liste dosyasının yolu.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = Path(options['file'])
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        if not file_path.exists():
            raise CommandError(f'Liste dosyası bulunamadı: {file_path}')

        created_count = 0
        skipped_count = 0
        team_count = 0

        with file_path.open('r', encoding='utf-8-sig', newline='') as source:
            rows = csv.reader(source, skipinitialspace=True)
            for line_number, row in enumerate(rows, start=1):
                if not row or not any(value.strip() for value in row):
                    continue
                if len(row) != 5:
                    raise CommandError(
                        f'{line_number}. satırda 5 alan bekleniyor, {len(row)} alan bulundu.'
                    )

                gender_code, first_name, last_name, birth_year, team_name = [
                    value.strip() for value in row
                ]
                gender = {'K': 'F', 'E': 'M'}.get(gender_code.upper())
                if not gender:
                    raise CommandError(
                        f'{line_number}. satırda geçersiz cinsiyet: {gender_code}'
                    )
                try:
                    birth_date = date(int(birth_year), 1, 1)
                except ValueError as error:
                    raise CommandError(
                        f'{line_number}. satırda geçersiz doğum yılı: {birth_year}'
                    ) from error

                team, team_created = Team.objects.get_or_create(name=team_name)
                if team_created:
                    team_count += 1

                duplicate = Athlete.objects.filter(
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                    team=team,
                ).exists()
                if duplicate:
                    skipped_count += 1
                    continue

                Athlete.objects.create(
                    parent='Belirtilmemiş',
                    parent_phone='Belirtilmemiş',
                    parent_email='',
                    first_name=first_name,
                    last_name=last_name,
                    phone_number='Belirtilmemiş',
                    birth_date=birth_date,
                    gender=gender,
                    school='Belirtilmemiş',
                    license_number='Belirtilmemiş',
                    joined_date=date(2026, 9, 1),
                    status='pending',
                    is_active=False,
                    team=team,
                )
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'{created_count} sporcu eklendi, {skipped_count} kayıt atlandı, '
            f'{team_count} takım oluşturuldu.'
        ))
