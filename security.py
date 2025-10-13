import argon2


class PasswordHasher:
    def __init__(self):
        self.hasher = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
            salt_len=16
        )

    def hash_password(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify_password(self, hashed_password: str, password: str) -> bool:
        try:
            return self.hasher.verify(hashed_password, password)
        except (argon2.exceptions.VerifyMismatchError,
                argon2.exceptions.VerificationError,
                argon2.exceptions.InvalidHashError):
            return False


password_hasher = PasswordHasher()