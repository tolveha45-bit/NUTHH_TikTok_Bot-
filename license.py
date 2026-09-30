from database import user_has_valid_license


def can_download(user_id):
    return user_has_valid_license(user_id)
