from database.supabase import supabase


def sign_up(email, password):
    response = supabase.auth.sign_up({
        "email": email,
        "password": password
    })

    return response


def sign_in(email, password):
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

    return response


def sign_out():
    supabase.auth.sign_out()