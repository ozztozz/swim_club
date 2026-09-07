from django.db import migrations


def move_team_fees_to_history(apps, schema_editor):
    Team = apps.get_model('teams', 'Team')
    TeamFeeHistory = apps.get_model('finance', 'TeamFeeHistory')

    for team in Team.objects.all().iterator():
        TeamFeeHistory.objects.get_or_create(
            team_id=team.pk,
            start_date=team.created_at.date(),
            defaults={'monthly_fee': team.monthly_fee},
        )


def reverse_move_team_fees(apps, schema_editor):
    Team = apps.get_model('teams', 'Team')
    TeamFeeHistory = apps.get_model('finance', 'TeamFeeHistory')

    for team in Team.objects.all().iterator():
        fee = TeamFeeHistory.objects.filter(team_id=team.pk).order_by('-start_date').first()
        if fee:
            team.monthly_fee = fee.monthly_fee
            team.save(update_fields=['monthly_fee'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_athletefeehistory_teamfeehistory'),
        ('teams', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(move_team_fees_to_history, reverse_move_team_fees),
        migrations.RemoveField(
            model_name='team',
            name='monthly_fee',
        ),
    ]
