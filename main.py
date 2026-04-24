"""Example usage of the Higyrus API client.

Requires a .env file with HIGYRUS_CLIENT_ID, HIGYRUS_USER, HIGYRUS_PASSWORD
and HIGYRUS_BASE_URL.
"""

from datetime import date

import higyrus_client as higyrus


def main() -> None:
    health = higyrus.get_health()
    print("Health:", health)

    higyrus.login()
    print("Login OK")

    # Replace "REEMPLAZAR_ID_CUENTA" with a real account ID to test against
    # a live Higyrus tenant; uncomment to run.
    # posiciones = higyrus.get_posiciones(
    #     "REEMPLAZAR_ID_CUENTA",
    #     fecha=date.today(),
    #     incluir_parking=True,
    # )
    # print(f"{len(posiciones)} posiciones")
    # for pos in posiciones[:5]:
    #     print(
    #         f"  {pos.especie:<10} cant={pos.cantidadLiquidada:>8}  "
    #         f"precio={pos.precio:>10}  disp={pos.disponibleAjustado}"
    #     )
    _ = date  # silence unused-import when the example is commented


if __name__ == "__main__":
    main()
