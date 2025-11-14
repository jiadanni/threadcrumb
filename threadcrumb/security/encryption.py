"""
Data encryption for sensitive information at rest.

Uses Fernet symmetric encryption (AES-128 with HMAC authentication).
"""

import base64
import logging
import os
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class DataEncryptor:
    """Encrypts and decrypts data using Fernet symmetric encryption."""

    def __init__(self, key: Optional[bytes] = None, key_file: Optional[Path] = None):
        """
        Initialize data encryptor.

        Args:
            key: Encryption key (32 url-safe base64-encoded bytes)
            key_file: Path to file containing encryption key

        Note:
            Requires cryptography package: pip install cryptography
        """
        try:
            from cryptography.fernet import Fernet
            self._Fernet = Fernet
        except ImportError:
            raise ImportError(
                "cryptography package required for encryption. "
                "Install with: pip install cryptography"
            )

        if key:
            self.key = key
        elif key_file and key_file.exists():
            self.key = self._load_key(key_file)
        else:
            # Generate new key if none provided
            self.key = self._Fernet.generate_key()
            logger.warning("No encryption key provided, generated new key")

        self.cipher = self._Fernet(self.key)

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new encryption key.

        Returns:
            32-byte url-safe base64-encoded key
        """
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key()
        except ImportError:
            raise ImportError(
                "cryptography package required. "
                "Install with: pip install cryptography"
            )

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """
        Encrypt data.

        Args:
            data: Data to encrypt (string or bytes)

        Returns:
            Encrypted data as bytes
        """
        if isinstance(data, str):
            data = data.encode('utf-8')

        return self.cipher.encrypt(data)

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data.

        Args:
            encrypted_data: Encrypted data bytes

        Returns:
            Decrypted data as bytes
        """
        return self.cipher.decrypt(encrypted_data)

    def decrypt_to_string(self, encrypted_data: bytes) -> str:
        """
        Decrypt data and return as string.

        Args:
            encrypted_data: Encrypted data bytes

        Returns:
            Decrypted data as UTF-8 string
        """
        decrypted = self.decrypt(encrypted_data)
        return decrypted.decode('utf-8')

    def encrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file.

        Args:
            input_path: Path to file to encrypt
            output_path: Path for encrypted file (default: input_path.enc)

        Returns:
            Path to encrypted file
        """
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")

        if output_path is None:
            output_path = input_path.with_suffix(input_path.suffix + '.enc')

        with open(input_path, 'rb') as f:
            data = f.read()

        encrypted_data = self.encrypt(data)

        with open(output_path, 'wb') as f:
            f.write(encrypted_data)

        logger.info(f"Encrypted file: {input_path} -> {output_path}")
        return output_path

    def decrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file.

        Args:
            input_path: Path to encrypted file
            output_path: Path for decrypted file

        Returns:
            Path to decrypted file
        """
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")

        if output_path is None:
            # Remove .enc extension if present
            if input_path.suffix == '.enc':
                output_path = input_path.with_suffix('')
            else:
                output_path = input_path.with_suffix('.decrypted')

        with open(input_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = self.decrypt(encrypted_data)

        with open(output_path, 'wb') as f:
            f.write(decrypted_data)

        logger.info(f"Decrypted file: {input_path} -> {output_path}")
        return output_path

    def save_key(self, key_file: Path):
        """
        Save encryption key to file.

        Args:
            key_file: Path to save key file
        """
        key_file.parent.mkdir(parents=True, exist_ok=True)

        with open(key_file, 'wb') as f:
            f.write(self.key)

        # Set restrictive permissions (owner read/write only)
        os.chmod(key_file, 0o600)

        logger.info(f"Saved encryption key to: {key_file}")

    def _load_key(self, key_file: Path) -> bytes:
        """Load encryption key from file."""
        with open(key_file, 'rb') as f:
            return f.read()


def encrypt_cache_directory(cache_dir: Path, encryptor: DataEncryptor):
    """
    Encrypt all files in a cache directory.

    Args:
        cache_dir: Directory containing cache files
        encryptor: DataEncryptor instance to use
    """
    if not cache_dir.exists():
        logger.warning(f"Cache directory does not exist: {cache_dir}")
        return

    encrypted_dir = cache_dir.parent / f"{cache_dir.name}_encrypted"
    encrypted_dir.mkdir(exist_ok=True)

    encrypted_count = 0

    for file_path in cache_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix != '.enc':
            relative_path = file_path.relative_to(cache_dir)
            output_path = encrypted_dir / relative_path.with_suffix(relative_path.suffix + '.enc')
            output_path.parent.mkdir(parents=True, exist_ok=True)

            encryptor.encrypt_file(file_path, output_path)
            encrypted_count += 1

    logger.info(f"Encrypted {encrypted_count} files to: {encrypted_dir}")


def decrypt_cache_directory(encrypted_dir: Path, output_dir: Path, encryptor: DataEncryptor):
    """
    Decrypt all files in an encrypted cache directory.

    Args:
        encrypted_dir: Directory containing encrypted files
        output_dir: Directory for decrypted files
        encryptor: DataEncryptor instance to use
    """
    if not encrypted_dir.exists():
        logger.warning(f"Encrypted directory does not exist: {encrypted_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    decrypted_count = 0

    for file_path in encrypted_dir.rglob('*.enc'):
        if file_path.is_file():
            relative_path = file_path.relative_to(encrypted_dir)
            output_path = output_dir / relative_path.with_suffix('')
            output_path.parent.mkdir(parents=True, exist_ok=True)

            encryptor.decrypt_file(file_path, output_path)
            decrypted_count += 1

    logger.info(f"Decrypted {decrypted_count} files to: {output_dir}")
