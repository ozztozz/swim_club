from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# =========================================================
# BUTTON
# =========================================================

@register.inclusion_tag(
    "components/ui/button.html"
)
def button(
    text="",
    variant="primary",
    size="md",
    icon="",
    type="button",
    href="",
    disabled=False,
    **kwargs,
):

    return {
        "text": text,
        "variant": variant,
        "size": size,
        "icon": icon,
        "type": type,
        "href": href,
        "disabled": disabled,
        "class": kwargs.get("class", ""),
    }


# =========================================================
# BADGE
# =========================================================

@register.inclusion_tag(
    "components/ui/badge.html"
)
def badge(
    text="",
    variant="neutral",
    size="sm",
):

    return {
        "text": text,
        "variant": variant,
        "size": size,
    }


# =========================================================
# INPUT
# =========================================================

@register.inclusion_tag(
    "components/ui/input.html"
)
def input(
    name="",
    label="",
    value="",
    placeholder="",
    type="text",
    error="",
    required=False,
    disabled=False,
    id="",
):

    return {
        "name": name,
        "label": label,
        "value": value,
        "placeholder": placeholder,
        "type": type,
        "error": error,
        "required": required,
        "disabled": disabled,
        "id": id or name,
    }


# =========================================================
# CARD
# =========================================================

@register.inclusion_tag(
    "components/ui/card.html"
)
def card(
    title="",
):

    return {
        "title": title,
    }

@register.inclusion_tag(
    "components/ui/select.html"
)
def select(
    name="",
    label="",
    options=None,
    value="",
    placeholder="Seçiniz",
    error="",
    required=False,
    id="",
):

    return {
        "name": name,
        "label": label,
        "options": options or [],
        "value": value,
        "placeholder": placeholder,
        "error": error,
        "required": required,
        "id": id or name,
    }

@register.inclusion_tag(
    "components/ui/list-item.html"
)
def list_item(
    title="",
    subtitle="",
    meta="",
    href="#",
    avatar="",
    arrow=True,
):

    return {
        "title": title,
        "subtitle": subtitle,
        "meta": meta,
        "href": href,
        "avatar": avatar,
        "arrow": arrow,
    }