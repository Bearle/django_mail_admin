import logging

from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.forms.widgets import TextInput
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from django_mail_admin.models import Mailbox, IncomingAttachment, IncomingEmail, TemplateVariable, OutgoingEmail, \
    Outbox, EmailTemplate, STATUS, Log, Attachment
from django_mail_admin.signals import message_received
from django_mail_admin.utils import convert_header_to_unicode
from .fields import CommaSeparatedEmailField
from .forms import OutgoingEmailAdminForm

logger = logging.getLogger(__name__)

# Admin row actions
if 'django_admin_row_actions' in settings.INSTALLED_APPS:
    try:
        from django_admin_row_actions import AdminRowActionsMixin
    except ImportError:
        admin_row_actions = False
    else:
        admin_row_actions = True
else:
    admin_row_actions = False


def get_parent():
    """
    Optionally adds AdminRowActionsMixin to admin.ModelAdmin if django_admin_row_actions is installed
    :return: class to inherit from
    """
    if admin_row_actions:
        class BaseAdmin(AdminRowActionsMixin, admin.ModelAdmin):
            pass
    else:
        class BaseAdmin(admin.ModelAdmin):
            pass

    return BaseAdmin


def get_new_mail(mailbox_admin, request, queryset):
    for mailbox in queryset.all():
        logger.debug('Receiving mail for %s' % mailbox)
        got_mail = mailbox.get_new_mail()
        if len(got_mail) > 0:
            messages.success(request, _('Got {} new letters for mailbox "{}"').format(str(len(got_mail)), mailbox.name))
        else:
            messages.info(request, _('No new mail for mailbox "{}"').format(mailbox.name))


get_new_mail.short_description = _('Get new mail')


def switch_active(mailbox_admin, request, queryset):
    for mailbox in queryset.all():
        mailbox.active = not mailbox.active
        mailbox.save()


switch_active.short_description = _('Switch active status')


class MailboxAdmin(get_parent()):
    list_display = (
        'name',
        'uri',
        'from_email',
        'active',
        'last_polling',
    )
    readonly_fields = ['last_polling', ]
    actions = [get_new_mail, switch_active]


class IncomingAttachmentInline(admin.TabularInline):
    model = IncomingAttachment
    extra = 0
    readonly_fields = ['headers', ]


def resend_message_received_signal(incoming_email_admin, request, queryset):
    for message in queryset.all():
        logger.debug('Resending \'message_received\' signal for %s' % message)
        message_received.send(sender=incoming_email_admin, message=message)


resend_message_received_signal.short_description = (
    _('Re-send message received signal')
)


def mark_as_unread(incoming_email_admin, request, queryset):
    for msg in queryset.all():
        msg.read = None
        msg.save()


mark_as_unread.short_description = _('Mark as unread')


def mark_as_read(incoming_email_admin, request, queryset):
    for msg in queryset.all():
        msg.read = timezone.now()
        msg.save()


mark_as_read.short_description = _('Mark as read')


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


class IncomingEmailAdmin(admin.ModelAdmin):
    def html(self, msg):
        return mark_safe(msg.html)

    def attachment_count(self, msg):
        return msg.attachments.count()

    attachment_count.short_description = _('Attachment count')

    def subject(self, msg):
        return convert_header_to_unicode(msg.subject)

    def mailbox_link(self, msg):
        return mark_safe('<a href="' + reverse('admin:django_mail_admin_mailbox_change', args=[msg.mailbox.pk])
                         + '">' + msg.mailbox.name + '</a>')

    mailbox_link.short_description = _('Mailbox')

    def reply_link(self, msg):
        if msg.in_reply_to:
            return mark_safe(
                '<a href="' + reverse('admin:django_mail_admin_outgoingemail_change',
                                      args=[msg.in_reply_to.pk]) + '">' + msg.in_reply_to.subject + '</a>')
        else:
            return ''

    reply_link.short_description = _('Reply to')

    def from_address(self, msg):
        f = msg.from_address
        if len(f) > 0:
            return ','.join(f)
        else:
            return ''

    from_address.short_description = _('From')

    def envelope_headers(self, msg):
        email = msg.get_email_object()
        return '\n'.join(
            [('%s: %s' % (h, v)) for h, v in email.items()]
        )

    inlines = [
        IncomingAttachmentInline,
    ]

    fieldsets = [
        (None, {'fields': [('mailbox', 'message_id'), 'read']}),
        (None, {'fields': [('from_header', 'in_reply_to'), 'to_header']}),
        (None, {'fields': ['text', 'html']}),
    ]

    list_display = (
        'subject',
        'from_address',
        'processed',
        'read',
        'mailbox_link',
        'attachment_count',
        'reply_link'
    )
    ordering = ['-processed']
    list_filter = (
        ('mailbox__name', custom_titled_filter(_('Mailbox name'))),
        'processed',
        'read',
    )
    exclude = (
        'body',
    )
    raw_id_fields = (
        'in_reply_to',
    )
    readonly_fields = (
        'envelope_headers',
        'message_id',
        'text',
        'html',
    )
    search_fields = ['mailbox__name', 'subject', 'from_header', 'in_reply_to__subject']
    actions = [resend_message_received_signal, mark_as_unread, mark_as_read]

    def has_add_permission(self, request):
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = IncomingEmail.objects.filter(id=object_id).first()
        if obj:
            if not obj.read:
                obj.read = timezone.now()
                obj.save()
        return super(IncomingEmailAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context,
        )


class IncomingAttachmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('message',)
    list_display = ('message', 'document',)


if admin_row_actions:
    def get_row_actions(self, obj):
        row_actions = [
            {
                'label': _('View emails'),
                'url': reverse('admin:django_mail_admin_incomingemail_changelist') + '?mailbox__name=' + obj.name,
                'tooltip': _('View emails'),
            }, {
                'divided': True,
                'label': _('Get new mail'),
                'action': 'get_new_mail',  # calls model's get_new_mail
            },
        ]
        row_actions += super(MailboxAdmin, self).get_row_actions(obj)
        return row_actions


    MailboxAdmin.get_row_actions = get_row_actions


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'subject')


class TemplateVariableInline(admin.TabularInline):
    model = TemplateVariable
    extra = 1


def get_message_preview(instance):
    return ('{0}...'.format(instance.message[:25]) if len(instance.message) > 25
            else instance.message)


get_message_preview.short_description = _('Message')


class AttachmentInline(admin.TabularInline):
    model = Attachment.emails.through
    extra = 1
    verbose_name = _("Attachment")
    verbose_name_plural = _("Attachments")


class CommaSeparatedEmailWidget(TextInput):
    def __init__(self, *args, **kwargs):
        super(CommaSeparatedEmailWidget, self).__init__(*args, **kwargs)
        self.attrs.update({'class': 'vTextField'})

    def _format_value(self, value):
        # If the value is a string wrap it in a list so it does not get sliced.
        if not value:
            return ''
        if isinstance(value, str):
            value = [value, ]
        return ','.join([item for item in value])


def requeue(modeladmin, request, queryset):
    """An admin action to requeue emails."""
    queryset.update(status=STATUS.queued)


requeue.short_description = _('Requeue selected emails')


class LogInline(admin.TabularInline):
    model = Log
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('date')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class OutgoingEmailAdmin(admin.ModelAdmin):
    inlines = (TemplateVariableInline, AttachmentInline, LogInline)
    list_display = ['id', 'to_display', 'subject', 'template', 'from_email', 'status', 'scheduled_time', 'priority']
    formfield_overrides = {
        CommaSeparatedEmailField: {'widget': CommaSeparatedEmailWidget}
    }
    actions = [requeue]
    form = OutgoingEmailAdminForm

    def to_display(self, instance):
        return ', '.join(instance.to)

    to_display.short_description = _('To')

    def get_form(self, request, obj=None, **kwargs):
        # Try to get active Outbox and prepopulate from_email field
        form = super(OutgoingEmailAdmin, self).get_form(request, obj, **kwargs)
        configurations = Outbox.objects.filter(active=True)
        if not (len(configurations) > 1 or len(configurations) == 0):
            form.base_fields['from_email'].initial = configurations.first().email_host_user
        return form

    def save_model(self, request, obj, form, change):
        super(OutgoingEmailAdmin, self).save_model(request, obj, form, change)
        # If we have an email to reply to, specify replied headers
        if form.cleaned_data['reply']:
            if not obj.headers:
                obj.headers = {}

            obj.headers.update(form.cleaned_data['reply'].get_reply_headers(obj.headers))
            obj.save()
        # TODO: add setting to only queue emails after pressing a button/etc.
        obj.queue()


class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'file',)


class OutboxAdmin(admin.ModelAdmin):
    list_display = ('name', 'email_host', 'email_host_user', 'email_port', 'id', 'active')
    list_filter = ('active',)


class LogAdmin(admin.ModelAdmin):
    list_display = ('email', 'status', 'date', 'message')


if getattr(settings, 'DJANGO_MAILADMIN_ADMIN_ENABLED', True):
    admin.site.register(IncomingEmail, IncomingEmailAdmin)
    admin.site.register(IncomingAttachment, IncomingAttachmentAdmin)
    admin.site.register(Mailbox, MailboxAdmin)
    admin.site.register(EmailTemplate, EmailTemplateAdmin)
    # Without this attachment inline won't have add/edit buttons
    admin.site.register(Attachment, AttachmentAdmin)
    admin.site.register(OutgoingEmail, OutgoingEmailAdmin)
    admin.site.register(Outbox, OutboxAdmin)
    admin.site.register(Log, LogAdmin)
