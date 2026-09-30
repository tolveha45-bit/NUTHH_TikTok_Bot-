from database import has_valid_license


def user_can_download(user_id):
    return has_valid_license(user_id)
