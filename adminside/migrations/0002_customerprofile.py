# Create this migration file: adminside/migrations/0002_customerprofile.py
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('adminside', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('company', models.CharField(blank=True, max_length=100)),
                ('address_line1', models.CharField(blank=True, max_length=255)),
                ('address_line2', models.CharField(blank=True, max_length=255)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('postal_code', models.CharField(blank=True, max_length=20)),
                ('country', models.CharField(blank=True, max_length=100)),
                ('tax_id', models.CharField(blank=True, max_length=50)),
                ('business_type', models.CharField(choices=[('retail', 'Retail'), ('wholesale', 'Wholesale'), ('distributor', 'Distributor'), ('other', 'Other')], default='retail', max_length=50)),
                ('account_status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended'), ('pending', 'Pending Approval')], default='pending', max_length=20)),
                ('deactivated_at', models.DateTimeField(blank=True, null=True)),
                ('deactivation_reason', models.TextField(blank=True)),
                ('total_orders', models.IntegerField(default=0)),
                ('total_spent', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('last_order_date', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deactivated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deactivated_customers', to=settings.AUTH_USER_MODEL)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Customer Profile',
                'verbose_name_plural': 'Customer Profiles',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterField(
            model_name='activitylog',
            name='action',
            field=models.CharField(choices=[('CREATE', 'Created'), ('UPDATE', 'Updated'), ('DELETE', 'Deleted'), ('LOGIN', 'Logged in'), ('LOGOUT', 'Logged out'), ('ACTIVATE', 'Activated'), ('DEACTIVATE', 'Deactivated')], max_length=10),
        ),
    ]