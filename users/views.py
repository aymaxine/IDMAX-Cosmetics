from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
import logging

# Set up logging
logger = logging.getLogger(__name__)

def register(request):
    """View for user registration"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            try:
                # Save the user
                user = form.save()

                # Create customer group if it doesn't exist
                customer_group, created = Group.objects.get_or_create(name='Customer')

                # Add user to customer group
                user.groups.add(customer_group)

                # Log the registration
                logger.info(f"New user registered: {user.username}")

                # Display success message
                messages.success(request, f'Your account has been created! You can now log in.')
                return redirect('login')
            except Exception as e:
                logger.error(f"Error during user registration: {e}")
                messages.error(request, "There was an error creating your account. Please try again.")
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    """View for user profile management"""
    # Check if profile exists, create if it doesn't
    from .models import Profile
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        # Create a profile for the user
        profile = Profile.objects.create(user=request.user)
        logger.info(f"Created missing profile for user {request.user.username}")
        messages.info(request, "We've created a profile for you. Please update your information.")
    except Exception as e:
        logger.error(f"Error retrieving profile for user {request.user.username}: {e}")
        messages.error(request, "There was an error accessing your profile. Please try again later.")
        return redirect('store:home')

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            try:
                u_form.save()
                p_form.save()
                messages.success(request, f'Your account has been updated!')
                return redirect('profile')
            except Exception as e:
                logger.error(f"Error updating profile for user {request.user.username}: {e}")
                messages.error(request, "There was an error updating your profile. Please try again.")
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'users/profile.html', context)


@login_required
def user_list(request):
    """View for listing users (admin only)"""
    # Check if the user is admin
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('store:home')

    try:
        users = User.objects.all().order_by('-date_joined')
        return render(request, 'users/user_list.html', {'users': users})
    except Exception as e:
        logger.error(f"Error retrieving user list: {e}")
        messages.error(request, "There was an error retrieving the user list.")
        return redirect('store:home')