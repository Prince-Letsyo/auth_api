from typing import Any
from pwdlib import PasswordHash
from zxcvbn import  zxcvbn
import re


class PasswordValidator:
    def __init__(self):
        self.pwd_context: PasswordHash = PasswordHash.recommended()
        self.min_score: int = 2  # zxcvbn score (0-4, 2 = good)
        self.max_similarity: float = 0.8  # 80% similarity threshold
        self.common_passwords: set[str] = {
            "password",
            "123456",
            "qwerty",
            "admin",
            "letmein",
        }

    def normalize_string(self, s: str) -> str:
        """Normalize string for similarity comparison"""
        return re.sub(r"\s+", "", s.lower())

    def calculate_similarity(self, password: str, other_field: str) -> float:
        """Calculate similarity ratio between password and another field"""
        norm_password: str = self.normalize_string(s=password)
        norm_field: str = self.normalize_string(s=other_field)

        if len(norm_password) == 0 or len(norm_field) == 0:
            return 0.0

        min_len: int = min(len(norm_password), len(norm_field))
        max_len: int = max(len(norm_password), len(norm_field))

        if norm_password in norm_field or norm_field in norm_password:
            return min_len / max_len

        common_chars = sum(
            1 for i in range(min_len) if norm_password[i] == norm_field[i]
        )
        return common_chars / max_len

    def is_too_similar(
        self, password: str, username: str, email: str
    ) -> tuple[bool, str]:
        """Check if password is too similar to username or email"""
        similarity_username: float = self.calculate_similarity(password, other_field=username)
        similarity_email: float = self.calculate_similarity(password, other_field=email.split(sep="@")[0])

        if similarity_username > self.max_similarity:
            return (
                True,
                f"Password is too similar to username (similarity: {similarity_username:.1%})",
            )
        if similarity_email > self.max_similarity:
            return (
                True,
                f"Password is too similar to email (similarity: {similarity_email:.1%})",
            )
        return False, ""

    def validate_password(
        self, password: str, username: str, email: str
    ) -> dict[str,Any]:  # pyright: ignore[reportExplicitAny]
        """Complete Django-like password validation"""
        errors: list[str] = []

        # 1. Strength validation (zxcvbn)
        strength_result = zxcvbn(password)
        if strength_result["score"] < self.min_score:
            score_map: dict[int, str] = {
                0: "very weak",
                1: "weak",
                2: "good",
                3: "strong",
                4: "very strong",
            }
            feedback = strength_result["feedback"]
            error_msg: str = (
                f"Password is too weak (score: {score_map[strength_result['score']]}). "
                f"Suggestions: {feedback['suggestions'][0] if feedback['suggestions'] else 'Use a stronger password'}"
            )
            errors.append(error_msg)

        # 2. Similarity validation
        is_similar, similarity_msg = self.is_too_similar(password, username, email)
        if is_similar:
            errors.append(similarity_msg)

        # 3. Common passwords
        if password.lower() in self.common_passwords:
            errors.append("Password is too common")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "score": strength_result["score"],
            "feedback": strength_result["feedback"],
            "similarity_username": self.calculate_similarity(
                password, other_field=username
            ),
            "similarity_email": self.calculate_similarity(
                password, other_field=email.split("@")[0]
            ),
        }

    def verify_password(
        self, plain_password: str | bytes, hashed_password: str | bytes
    ) -> bool:
        return self.pwd_context.verify(password=plain_password, hash=hashed_password)

    def get_password_hash(self, password: str | bytes) -> str:
        return self.pwd_context.hash(password)


# Global instance
password_validator: PasswordValidator = PasswordValidator()
