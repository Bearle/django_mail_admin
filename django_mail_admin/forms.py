from django import forms

from django_mail_admin.models import OutgoingEmail, IncomingEmail


class OutgoingEmailAdminForm(forms.ModelForm):
    reply = forms.ModelChoiceField(queryset=IncomingEmail.objects.all(), label='Reply to', required=False)

    class Meta:
        model = OutgoingEmail
        fields = '__all__'
