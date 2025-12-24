from django.contrib.contenttypes.models import ContentType

from .models import Translation, Language


def get_translation(
    obj,
    field: str,
    language_code: str,
    fallback: bool = True,
    default: str = "",
) -> str:
    """
    Get translated text for any model instance.

    :param obj: model instance
    :param field: field name to translate (name, description, title, ...)
    :param language_code: language code (en, ru, de)
    :param fallback: try default language if not found
    :param default: value returned if translation not found
    """

    content_type = ContentType.objects.get_for_model(obj.__class__)

    try:
        language = Language.objects.get(code=language_code, is_active=True)
    except Language.DoesNotExist:
        return default

    translation = Translation.objects.filter(
        content_type=content_type,
        object_id=obj.pk,
        field=field,
        language=language,
    ).first()

    if translation:
        return translation.text

    if fallback:
        default_language = Language.objects.filter(is_default=True).first()
        if default_language and default_language != language:
            fallback_translation = Translation.objects.filter(
                content_type=content_type,
                object_id=obj.pk,
                field=field,
                language=default_language,
            ).first()
            if fallback_translation:
                return fallback_translation.text

    return default
