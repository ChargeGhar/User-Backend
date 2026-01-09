from abc import ABC, abstractmethod
from typing import Dict, Optional
from django.core.files.uploadedfile import InMemoryUploadedFile

class CloudStorageService(ABC):
    """
    Abstract base class for cloud storage services.
    """
    @abstractmethod
    def upload_file(self, file: InMemoryUploadedFile, folder: str = '', public: bool = True) -> Dict:
        pass

    @abstractmethod
    def delete_file(self, file_identifier: str) -> bool:
        pass

    @abstractmethod
    def get_file_info(self, file_identifier: str) -> Optional[Dict]:
        pass

class CloudinaryService(CloudStorageService):
    def __init__(self):
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
        import os
        cloudinary.config(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            api_key=os.getenv('CLOUDINARY_API_KEY'),
            api_secret=os.getenv('CLOUDINARY_API_SECRET'),
            secure=True
        )
        self.uploader = cloudinary.uploader
        self.api = cloudinary.api

    def upload_file(self, file: InMemoryUploadedFile, folder: str = '', public: bool = True) -> Dict:
        # Upload file to Cloudinary
        result = self.uploader.upload(
            file,
            folder=folder,
            resource_type="auto",
            use_filename=True,
            unique_filename=True,
            overwrite=False
        )
        return {
            'file_url': result['secure_url'],
            'public_id': result['public_id'],
            'provider': 'cloudinary',
            'upload_result': result
        }

    def delete_file(self, file_identifier: str) -> bool:
        # file_identifier is public_id
        result = self.uploader.destroy(file_identifier, resource_type="auto")
        return result.get('result') == 'ok'

    def get_file_info(self, file_identifier: str) -> Optional[Dict]:
        try:
            info = self.api.resource(file_identifier, resource_type="auto")
            return info
        except Exception:
            return None


class S3Service(CloudStorageService):
    def __init__(self):
        import boto3
        import os
        self.bucket = os.getenv('AWS_STORAGE_BUCKET_NAME')
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_S3_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_S3_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
        )
        self.base_url = f"https://{self.bucket}.s3.{os.getenv('AWS_S3_REGION_NAME', 'us-east-1')}.amazonaws.com"

    def upload_file(self, file: InMemoryUploadedFile, folder: str = '', public: bool = True) -> Dict:
        import uuid
        filename = file.name
        key = f"{folder}/{uuid.uuid4().hex}_{filename}"
        extra_args = {'ACL': 'public-read'} if public else {}
        self.s3.upload_fileobj(file, self.bucket, key, ExtraArgs=extra_args)
        file_url = f"{self.base_url}/{key}"
        return {
            'file_url': file_url,
            'public_id': key,
            'provider': 's3',
            'upload_result': {'bucket': self.bucket, 'key': key}
        }

    def delete_file(self, file_identifier: str) -> bool:
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=file_identifier)
            return True
        except Exception:
            return False

    def get_file_info(self, file_identifier: str) -> Optional[Dict]:
        try:
            obj = self.s3.head_object(Bucket=self.bucket, Key=file_identifier)
            return obj
        except Exception:
            return None


class CloudStorageFactory:
    """
    Factory class to select the appropriate cloud storage service.
    """
    @staticmethod
    def get_storage_service() -> CloudStorageService:
        import os
        
        # Try to get provider from AppConfig first
        try:
            from api.user.system.models import AppConfig
            config = AppConfig.objects.filter(key='cloud_storage_provider', is_active=True).first()
            provider = config.value.lower() if config else None
        except Exception:
            provider = None
        
        # Fallback to environment variable
        if not provider:
            provider = os.getenv('CLOUD_STORAGE_PROVIDER', 'cloudinary').lower()
        
        if provider == 'cloudinary':
            return CloudinaryService()
        elif provider == 's3':
            return S3Service()
        else:
            # Default to Cloudinary
            return CloudinaryService()
