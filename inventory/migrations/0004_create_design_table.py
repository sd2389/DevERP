from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_delete_inventorydesign'),
    ]

    operations = [
        migrations.CreateModel(
            name='Design',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('design_id', models.CharField(max_length=50)),
                ('design_no', models.CharField(max_length=100, unique=True)),
                ('image_base_path', models.CharField(blank=True, max_length=255)),
                ('date', models.DateField()),
                ('brand', models.CharField(blank=True, max_length=100)),
                ('gender', models.CharField(max_length=20)),
                ('category', models.CharField(max_length=100)),
                ('collection', models.CharField(blank=True, max_length=100)),
                ('subcategory', models.CharField(blank=True, max_length=100)),
                ('producttype', models.CharField(max_length=100)),
                ('occation', models.CharField(blank=True, max_length=100)),
                ('gwt', models.DecimalField(decimal_places=3, max_digits=10)),
                ('nwt', models.DecimalField(decimal_places=3, max_digits=10)),
                ('dwt', models.DecimalField(decimal_places=3, max_digits=10)),
                ('dpcs', models.IntegerField()),
                ('swt', models.DecimalField(decimal_places=3, max_digits=10)),
                ('spcs', models.IntegerField()),
                ('miscwt', models.DecimalField(decimal_places=3, max_digits=10)),
                ('miscpcs', models.IntegerField()),
                ('remarks', models.TextField(blank=True)),
                ('titleline', models.CharField(blank=True, max_length=255)),
                ('isNew', models.BooleanField(default=False)),
                ('length', models.CharField(blank=True, max_length=50)),
                ('width', models.CharField(blank=True, max_length=50)),
                ('size', models.CharField(blank=True, max_length=50)),
                ('margin', models.DecimalField(decimal_places=2, max_digits=8)),
                ('duty', models.DecimalField(decimal_places=2, max_digits=8)),
                ('totamt', models.DecimalField(decimal_places=2, max_digits=12)),
                ('vendor_code', models.CharField(blank=True, max_length=100)),
                ('parent_designno', models.CharField(blank=True, max_length=100)),
                ('package', models.CharField(blank=True, max_length=100)),
                ('stock_qty', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('last_synced', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'inventory_design',
                'indexes': [
                    models.Index(fields=['design_no'], name='inv_des_dno_idx'),
                    models.Index(fields=['category'], name='inv_des_cat_idx'),
                    models.Index(fields=['is_active'], name='inv_des_act_idx'),
                    models.Index(fields=['gender'], name='inv_des_gen_idx'),
                    models.Index(fields=['collection'], name='inv_des_col_idx'),
                    models.Index(fields=['producttype'], name='inv_des_pt_idx'),
                    models.Index(fields=['subcategory'], name='inv_des_sub_idx'),
                ],
            },
        ),
    ] 