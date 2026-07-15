import secrets
import string

from models import Reservation

ALPHANUMERIC: str = string.ascii_uppercase + string.digits


def __generate_reservation_code__(length: int = 8) -> str:
    return ''.join(
        secrets.choice(ALPHANUMERIC)
        for _ in range(length)
    )


def generate_unique_reservation_code(length: int = 8) -> str:
    for _ in range(10):
        code = __generate_reservation_code__(length)

        if not Reservation.objects.filter(
                reservation_code=code
        ).exists():
            return code

    raise RuntimeError('Could not generate unique reservation code.')
