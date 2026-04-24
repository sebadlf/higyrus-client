"""Example usage of the Higyrus API client.

Requires a .env file with HIGYRUS_CLIENT_ID, HIGYRUS_USER, HIGYRUS_PASSWORD
and HIGYRUS_BASE_URL.
"""

import higyrus_client as higyrus


def main() -> None:
    health = higyrus.get_health()
    print("Health:", health)

    higyrus.login()
    print("Login OK")


if __name__ == "__main__":
    main()
