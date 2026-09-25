from functions import database

def register(usertype, firstname, lastname, email, password, confirm):
    usertype = usertype.strip()
    firstname = firstname.strip()
    lastname = lastname.strip()
    email = email.strip()
    password = password.strip()
    confirm = confirm.strip()

    if password != confirm:
        return 1

    user = database.search(email)

    if user is not None:
        return 0

    database.insert(
        email,
        firstname,
        lastname,
        password,
        usertype,
        0,
        0,
        0
    )

    return 2


def login(email, password):
    email = email.strip()
    password = password.strip()

    user = database.search(email)

    if user is None:
        return 0

    if password != user["password"]:
        return 0

    if user["role"] == "customer":
        return 1

    elif user["role"] == "rider":
        return 2

    return 0