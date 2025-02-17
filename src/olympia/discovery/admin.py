from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.utils import translation
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe
from django.db.models import Prefetch

from olympia.addons.models import Addon
from olympia.discovery.models import DiscoveryItem
from olympia.hero.admin import SecondaryHeroAdmin, PrimaryHeroImageAdmin
from olympia.hero.models import SecondaryHero, PrimaryHeroImage
from olympia.shelves.admin import ShelfAdmin
from olympia.shelves.models import Shelf


# Popular locales, we typically don't want to show a string if it's not
# translated in those.
KEY_LOCALES_FOR_EDITORIAL_CONTENT = ('de', 'fr', 'es', 'pl', 'it', 'ja')


class SlugOrPkChoiceField(forms.ModelChoiceField):
    """A ModelChoiceField that supports entering slugs instead of PKs for
    convenience."""
    def clean(self, value):
        if (value and isinstance(value, str) and not value.isdigit()):
            try:
                value = self.queryset.values_list(
                    'pk', flat=True).get(slug=value)
            except self.queryset.model.DoesNotExist:
                value = value
        return super(SlugOrPkChoiceField, self).clean(value)


class PositionFilter(admin.SimpleListFilter):
    # Title for the filter section.
    title = 'presence in Disco Pane editorial content'

    # Parameter for the filter that will be used in the URL query. It's also
    # the name of the database field.
    parameter_name = 'position'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples.
        # - The first element in each tuple is the coded value for the option
        #   that will appear in the URL query.
        # - The second element is the human-readable name for the option that
        #   will appear
        in the right sidebar.
        """
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query
        string and retrievable via `self.value()`.
        """
        # Compare the requested value (either 'on' or 'off')
        # to decide how to filter the queryset.
        if self.value() == 'yes':
            return queryset.filter(**{self.parameter_name + '__gt': 0})
        if self.value() == 'no':
            return queryset.filter(**{self.parameter_name: 0})


class PositionChinaFilter(PositionFilter):
    title = 'presence in Disco Pane editorial content (China edition)'
    parameter_name = 'position_china'


class DiscoveryItemAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('css/admin/discovery.css',)
        }
    list_display = ('__str__',
                    'custom_addon_name', 'custom_heading', 'position',
                    'position_china',
                    )
    list_filter = (PositionFilter, PositionChinaFilter)
    raw_id_fields = ('addon',)
    readonly_fields = ('previews',)
    view_on_site = False

    def get_queryset(self, request):
        # Select `addon` as well as it's `_current_version`.
        # We are forced to use `prefetch_related` to ensure transforms
        # are being run, though, we only care about translations
        qset = (
            DiscoveryItem.objects.all()
            .prefetch_related(
                Prefetch(
                    'addon',
                    queryset=(
                        Addon.unfiltered.all()
                        .select_related('_current_version')
                        .only_translations()))))
        return qset

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'addon':
            kwargs['widget'] = ForeignKeyRawIdWidget(
                db_field.remote_field, self.admin_site,
                using=kwargs.get('using'))
            kwargs['queryset'] = Addon.objects.all()
            kwargs['help_text'] = db_field.help_text
            return SlugOrPkChoiceField(**kwargs)
        return super(DiscoveryItemAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)

    def build_preview(self, obj, locale):
        # FIXME: when disco in Firefox itself lands, change this preview to
        # match the one Firefox uses.
        # https://github.com/mozilla/addons-server/issues/11272
        return format_html(
            u'<div class="discovery-preview" data-locale="{}">'
            u'<h2 class="heading">{}</h2>'
            u'<div class="editorial-description">{}</div></div>',
            locale,
            mark_safe(obj.heading),
            mark_safe(obj.description))

    def previews(self, obj):
        translations = []
        for locale in ('en-US', ) + KEY_LOCALES_FOR_EDITORIAL_CONTENT:
            with translation.override(locale):
                translations.append(
                    conditional_escape(self.build_preview(obj, locale)))
        return mark_safe(''.join(translations))


class PrimaryHeroImageUpload(PrimaryHeroImage):
    """Just a proxy class to have all the hero related objects in one
    place under Discovery in django admin."""

    class Meta:
        proxy = True
        verbose_name_plural = 'primary hero images'


class SecondaryHeroShelf(SecondaryHero):
    """Just a proxy class to have all the hero shelf related objects in one
    place under Discovery in django admin."""

    class Meta(SecondaryHero.Meta):
        proxy = True
        verbose_name_plural = 'secondary hero shelves'


class ShelfModule(Shelf):
    class Meta:
        proxy = True
        verbose_name_plural = 'shelves'


admin.site.register(DiscoveryItem, DiscoveryItemAdmin)
admin.site.register(PrimaryHeroImageUpload, PrimaryHeroImageAdmin)
admin.site.register(SecondaryHeroShelf, SecondaryHeroAdmin)
admin.site.register(ShelfModule, ShelfAdmin)
