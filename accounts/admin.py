from django.contrib import admin
from .models import PasswordResetRequest
from django.utils import timezone
from django.contrib.auth.forms import PasswordResetForm

@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'requested_at', 'is_approved', 'processed_at')
    list_filter = ('is_approved',)
    actions = ['approve_and_send_reset']

    def approve_and_send_reset(self, request, queryset):
        for obj in queryset:
            if not obj.is_approved:
                obj.is_approved = True
                # Send Django's password reset email
                reset_form = PasswordResetForm({'email': obj.user.username})
                if reset_form.is_valid():
                    reset_form.save(
                        request=request,
                        use_https=False,
                        from_email=None,
                        email_template_name='accounts/password_reset_email.html', # or default
                    )
                    obj.processed_at = timezone.now()
                obj.save()
        self.message_user(request, "Selected requests approved and reset emails sent.")
    approve_and_send_reset.short_description = "Approve selected requests & send reset email"
