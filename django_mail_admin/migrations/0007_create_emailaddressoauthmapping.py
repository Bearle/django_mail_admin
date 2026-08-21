from django.db import migrations, models
import django.utils.translation

class Migration(migrations.Migration):

    dependencies = [
        ('django_mail_admin', '0006_incomingattachment_django_mail_message_dea8fb_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailAddressOAuthMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('send_as_email', models.EmailField(max_length=254, unique=True, verbose_name=django.utils.translation.gettext_lazy('Send As Email Address'))),
                ('oauth_username', models.EmailField(max_length=254, verbose_name=django.utils.translation.gettext_lazy('OAuth Username'))),
            ],
            options={
                'verbose_name': django.utils.translation.gettext_lazy('Email OAuth Mapping'),
                'verbose_name_plural': django.utils.translation.gettext_lazy('Email OAuth Mappings'),
            },
        ),
    ]
