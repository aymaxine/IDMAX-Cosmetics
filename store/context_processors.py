from .models import Cart, Wishlist, ComparisonList

def cart_processor(request):
    """
    Context processor to add cart information to all templates.
    This makes the cart item count available in all templates.
    """
    cart_items_count = 0

    try:
        if request.user.is_authenticated:
            # Get cart for authenticated user
            cart = Cart.objects.filter(user=request.user).first()
        else:
            # Get cart for anonymous user using session
            session_id = request.session.session_key
            if session_id:
                cart = Cart.objects.filter(session_id=session_id).first()
            else:
                cart = None

        # Count items in cart
        if cart:
            cart_items_count = cart.get_total_items()
    except Exception:
        # Fail silently if there's an error
        pass

    return {'cart_items_count': cart_items_count}


def wishlist_processor(request):
    """
    Context processor to add wishlist information to all templates.
    This makes the wishlist item count available in all templates.
    """
    wishlist_items_count = 0

    try:
        if request.user.is_authenticated:
            # Get wishlist for authenticated user
            wishlist = Wishlist.objects.filter(user=request.user).first()

            # Count items in wishlist
            if wishlist:
                wishlist_items_count = wishlist.get_total_items()
    except Exception:
        # Fail silently if there's an error
        pass

    return {'wishlist_items_count': wishlist_items_count}


def comparison_processor(request):
    """
    Context processor to add comparison list information to all templates.
    This makes the comparison item count available in all templates.
    """
    comparison_items_count = 0

    try:
        if request.user.is_authenticated:
            # Get comparison list for authenticated user
            comparison_list = ComparisonList.objects.filter(user=request.user).first()
        else:
            # Get comparison list for anonymous user using session
            session_id = request.session.session_key
            if session_id:
                comparison_list = ComparisonList.objects.filter(session_id=session_id).first()
            else:
                comparison_list = None

        # Count items in comparison list
        if comparison_list:
            comparison_items_count = comparison_list.get_products_count()
    except Exception:
        # Fail silently if there's an error
        pass

    return {'comparison_items_count': comparison_items_count}
