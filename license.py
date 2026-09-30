from database import has_valid_license


def can_download(user_id):
    return has_valid_license(user_id)
