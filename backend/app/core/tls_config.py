"""
TLS 1.3 configuration for secure data in transit.
Implements SSL/TLS settings for FastAPI and Nginx.
"""
import ssl
import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TLSConfig:
    """TLS 1.3 configuration manager for secure communications."""
    
    def __init__(self):
        self.cert_dir = Path("certs")
        self.cert_dir.mkdir(exist_ok=True)
        
        # TLS certificate paths
        self.cert_file = self.cert_dir / "server.crt"
        self.key_file = self.cert_dir / "server.key"
        self.ca_file = self.cert_dir / "ca.crt"
        
        # TLS configuration
        self.tls_version = ssl.TLSVersion.TLSv1_3
        self.cipher_suites = [
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256"
        ]
    
    def create_ssl_context(self, 
                          cert_file: Optional[str] = None, 
                          key_file: Optional[str] = None) -> ssl.SSLContext:
        """
        Create SSL context with TLS 1.3 configuration.
        
        Args:
            cert_file: Path to SSL certificate file
            key_file: Path to SSL private key file
            
        Returns:
            Configured SSL context
        """
        # Create SSL context with TLS 1.3
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        # Set minimum TLS version to 1.3
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Security settings
        context.check_hostname = False  # Will be handled by reverse proxy
        context.verify_mode = ssl.CERT_NONE  # Client cert verification optional
        
        # Set cipher suites (TLS 1.3 uses different cipher suites)
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS")
        
        # Load certificate and key
        cert_path = cert_file or str(self.cert_file)
        key_path = key_file or str(self.key_file)
        
        if os.path.exists(cert_path) and os.path.exists(key_path):
            context.load_cert_chain(cert_path, key_path)
            logger.info(f"Loaded SSL certificate from {cert_path}")
        else:
            logger.warning("SSL certificate files not found. Using self-signed certificate.")
            self.generate_self_signed_cert()
            context.load_cert_chain(str(self.cert_file), str(self.key_file))
        
        return context
    
    def generate_self_signed_cert(self) -> None:
        """Generate self-signed certificate for development/testing."""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            import datetime
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "AE"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Dubai"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Dubai"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Intelligent AI Assistant"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.DNSName("0.0.0.0"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Write certificate
            with open(self.cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            with open(self.key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            os.chmod(self.cert_file, 0o644)
            
            logger.info("Generated self-signed SSL certificate")
            
        except ImportError:
            logger.error("cryptography package required for certificate generation")
            raise
        except Exception as e:
            logger.error(f"Failed to generate self-signed certificate: {e}")
            raise
    
    def get_nginx_tls_config(self) -> str:
        """
        Generate Nginx TLS configuration for TLS 1.3.
        
        Returns:
            Nginx configuration string
        """
        return f"""
# TLS 1.3 Configuration
ssl_protocols TLSv1.3;
ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256;
ssl_prefer_server_ciphers off;

# SSL Certificate paths
ssl_certificate {self.cert_file};
ssl_certificate_key {self.key_file};

# SSL Session settings
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;

# Security headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' wss: https:; media-src 'self'; object-src 'none'; frame-src 'none';" always;

# Disable server tokens
server_tokens off;
"""
    
    def get_fastapi_ssl_config(self) -> Dict[str, Any]:
        """
        Get SSL configuration for FastAPI/Uvicorn.
        
        Returns:
            Dictionary with SSL configuration parameters
        """
        return {
            "ssl_keyfile": str(self.key_file),
            "ssl_certfile": str(self.cert_file),
            "ssl_version": ssl.PROTOCOL_TLS_SERVER,
            "ssl_cert_reqs": ssl.CERT_NONE,
            "ssl_ca_certs": str(self.ca_file) if self.ca_file.exists() else None,
        }
    
    def validate_tls_config(self) -> bool:
        """
        Validate TLS configuration and certificate files.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check if certificate files exist
            if not self.cert_file.exists() or not self.key_file.exists():
                logger.error("SSL certificate or key file not found")
                return False
            
            # Try to create SSL context
            context = self.create_ssl_context()
            
            # Verify TLS version
            if context.minimum_version != ssl.TLSVersion.TLSv1_3:
                logger.error("TLS 1.3 not properly configured")
                return False
            
            logger.info("TLS configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"TLS configuration validation failed: {e}")
            return False
    
    def get_security_headers(self) -> Dict[str, str]:
        """
        Get security headers for HTTP responses.
        
        Returns:
            Dictionary of security headers
        """
        return {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' wss: https:; "
                "media-src 'self'; "
                "object-src 'none'; "
                "frame-src 'none';"
            ),
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            )
        }


# Global TLS configuration instance
_tls_config: Optional[TLSConfig] = None


def get_tls_config() -> TLSConfig:
    """Get or create the global TLS configuration instance."""
    global _tls_config
    
    if _tls_config is None:
        _tls_config = TLSConfig()
    
    return _tls_config