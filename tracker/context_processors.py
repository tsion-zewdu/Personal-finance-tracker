def user_categories(request):
    """Add user categories to context for all templates"""
    if request.user.is_authenticated:
        return {
            'user_categories': request.user.categories.all()
        }
    return {}