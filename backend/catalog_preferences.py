"""Pure matching rules shared by dealer product preferences and tests."""


def normalize_company(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def company_preference_matches(
    selected_companies: object,
    manufacturer: object,
    brand: object,
) -> bool:
    """No company checkboxes means all; otherwise match company or product brand."""
    if isinstance(selected_companies, str):
        selected_companies = selected_companies.split(",")
    elif selected_companies is not None and not isinstance(selected_companies, (list, tuple, set)):
        selected_companies = [selected_companies]
    selected = {normalize_company(value) for value in (selected_companies or []) if normalize_company(value)}
    if not selected:
        return True
    product_companies = {normalize_company(manufacturer), normalize_company(brand)} - {""}
    return bool(selected.intersection(product_companies))


def product_type_preference_matches(
    category_selected: bool,
    selected_product_types: object,
    product_type_id: object,
) -> bool:
    """A category with no child checks means all its product types."""
    if not category_selected:
        return False
    if isinstance(selected_product_types, str):
        selected_product_types = [selected_product_types]
    selected = {str(value) for value in (selected_product_types or []) if value}
    return not selected or str(product_type_id or "") in selected


def dealer_category_preference_matches(
    selected_category_ids: object,
    product_category_id: object,
    product_type_id: object,
    category_parents: dict[str, str | None],
) -> bool:
    """Match a dealer's category tree; no selected categories means any category.

    The profile stores both a selected child and its parent. Selecting a parent
    alone opts into every product type below it, while selecting child types
    opts into only those children.
    """
    if isinstance(selected_category_ids, str):
        selected_category_ids = selected_category_ids.split(",")
    elif selected_category_ids is not None and not isinstance(selected_category_ids, (list, tuple, set)):
        selected_category_ids = [selected_category_ids]
    selected = {str(value).strip() for value in (selected_category_ids or []) if str(value).strip()}
    if not selected:
        return True

    product_category = str(product_category_id or "")
    product_type = str(product_type_id or "")
    selected_children = {
        category_id
        for category_id in selected
        if str(category_parents.get(category_id) or "") == product_category
    }
    # A selected child implies its parent even for legacy rows that were saved
    # before the profile writer began persisting both IDs.
    parent_selected = product_category in selected or bool(selected_children)
    if not parent_selected:
        return False
    if not selected_children:
        return True
    return bool(product_type and product_type in selected_children)
