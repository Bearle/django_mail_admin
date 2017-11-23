import logging

from django.conf import settings
from django.contrib import admin
from django_mail_admin.models import Mailbox
from django.shortcuts import reverse

logger = logging.getLogger(__name__)
from django.utils.translation import ugettext_lazy as _

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
        mailbox.get_new_mail()


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


if admin_row_actions:
    def get_row_actions(self, obj):
        row_actions = [
            {
                'label': _('View emails'),
                # 'url': reverse('convert_stuff', args=[obj.id]),
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

if getattr(settings, 'DJANGO_MAILADMIN_ADMIN_ENABLED', True):
    # admin.site.register(Message, MessageAdmin)
    # admin.site.register(MessageAttachment, MessageAttachmentAdmin)
    admin.site.register(Mailbox, MailboxAdmin)
