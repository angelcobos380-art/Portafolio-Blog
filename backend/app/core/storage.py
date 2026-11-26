from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time

import httpx

from app.core.config import settings
from app.core.database import new_id

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@dataclass
class StoredObject:
    storage_key: str
    url: str


class StorageBackend(ABC):
    @abstractmethod
    def save(self, data: bytes, mime: str) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str, base_url: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def save(self, data: bytes, mime: str) -> StoredObject:
        ext = MIME_TO_EXT.get(mime, ".bin")
        key = f"{new_id()}{ext}"
        target = self.base_dir / key
        target.write_bytes(data)
        return StoredObject(storage_key=key, url=f"{self.base_url}/{key}")

    def delete(self, storage_key: str) -> None:
        target = self.base_dir / storage_key
        if target.exists():
            target.unlink()


class CloudinaryStorageBackend(StorageBackend):
    def __init__(self, cloud_name: str, api_key: str, api_secret: str, folder: str) -> None:
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.folder = folder

    def _sign(self, params: dict) -> str:
        to_sign = "&".join(f"{k}={params[k]}" for k in sorted(params)) + self.api_secret
        return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

    def save(self, data: bytes, mime: str) -> StoredObject:
        timestamp = int(time.time())
        public_id = new_id()
        sign_params = {"folder": self.folder, "public_id": public_id, "timestamp": timestamp}
        signature = self._sign(sign_params)
        ext = MIME_TO_EXT.get(mime, ".bin")

        url = f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/upload"
        resp = httpx.post(
            url,
            data={
                **sign_params,
                "api_key": self.api_key,
                "signature": signature,
            },
            files={"file": (f"{public_id}{ext}", data, mime)},
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        return StoredObject(
            storage_key=payload["public_id"],
            url=payload["secure_url"],
        )

    def delete(self, storage_key: str) -> None:
        timestamp = int(time.time())
        sign_params = {"public_id": storage_key, "timestamp": timestamp}
        signature = self._sign(sign_params)
        url = f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/destroy"
        resp = httpx.post(
            url,
            data={
                **sign_params,
                "api_key": self.api_key,
                "signature": signature,
            },
            timeout=15.0,
        )
        resp.raise_for_status()


def get_storage_backend() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower().strip()
    if backend == "cloudinary":
        if not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET):
            raise RuntimeError("Faltan variables CLOUDINARY_* para STORAGE_BACKEND=cloudinary.")
        return CloudinaryStorageBackend(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            folder=settings.CLOUDINARY_FOLDER,
        )
    return LocalStorageBackend(
        base_dir=settings.MEDIA_LOCAL_DIR,
        base_url=settings.MEDIA_BASE_URL,
    )
