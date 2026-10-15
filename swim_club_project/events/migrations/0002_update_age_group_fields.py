from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="competitionevent",
            name="distance_m",
        ),
        migrations.RemoveField(
            model_name="competitionevent",
            name="category",
        ),
        migrations.AddField(
            model_name="competitionevent",
            name="age_group_start",
            field=models.CharField(max_length=150, verbose_name="Yaş Grubu (Başlangıç)"),
        ),
        migrations.AddField(
            model_name="competitionevent",
            name="age_group_end",
            field=models.CharField(max_length=150, verbose_name="Yaş Grubu (Bitiş) "),
        ),
    ]
