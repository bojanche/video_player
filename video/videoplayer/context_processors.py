from .models import UserProfileInfo


def user_profile_photo(request):
    if not request.user.is_authenticated:
        return {'user_profile_photo_url': ''}

    profile = UserProfileInfo.objects.filter(user=request.user).first()
    if not profile or not profile.profile_pic:
        return {'user_profile_photo_url': ''}

    return {'user_profile_photo_url': profile.profile_pic.url}
