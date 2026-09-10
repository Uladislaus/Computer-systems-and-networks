from docfactory.catalog import CATALOG, categories, get_doc_type

__all__ = ["CATALOG", "get_doc_type", "categories", "generate"]


def generate(*args, **kwargs):
    from docfactory.generators import generate as _generate

    return _generate(*args, **kwargs)
