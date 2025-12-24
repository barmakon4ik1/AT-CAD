from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from .models import Translation, Language


class TranslatableModel:
    """
    Mixin for models that support translations via Translation model.
    """

    def get_translation(self, field: str, language: Language | None = None) -> str:
        """
        Returns translated value for given field and language.
        Fallback order:
        1. provided language
        2. default language
        3. empty string
        """

        content_type = ContentType.objects.get_for_model(self)

        # 1️⃣ Определяем язык
        if language is None:
            language = (
                Language.objects.filter(is_default=True).first()
            )

        if language is None:
            return ""

        # 2️⃣ Пытаемся получить перевод
        translation = Translation.objects.filter(
            content_type=content_type,
            object_id=self.pk,
            field=field,
            language=language,
        ).first()

        if translation:
            return translation.text

        # 3️⃣ Fallback на default язык (если был передан другой)
        if not language.is_default:
            default_language = Language.objects.filter(is_default=True).first()
            if default_language:
                translation = Translation.objects.filter(
                    content_type=content_type,
                    object_id=self.pk,
                    field=field,
                    language=default_language,
                ).first()
                if translation:
                    return translation.text

        return ""
