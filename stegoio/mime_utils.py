# stegoio/mime_utils.py
import os
import struct

# This py file contains functions to detect MIME types based on file extensions and magic numbers.
# It supports a wide range of common file types including videos, executables, PDFs, images, audio, documents, and more.
# Extracts data during decoding, and saves it as standardised name of 'recovered' + proper file extension.

# Primary functions:
# - detect_mime_type(file_path): Main function to get MIME type of a file by extension and magic number.
# - get_mime_from_extension(ext): Maps file extensions to MIME types.
# - get_mime_from_magic(header): Reads first 16 bytes of a file to verify actual type.
# - get_extension_from_mime(mime_type): Maps MIME types back to file extensions.


def detect_mime_type(file_path: str) -> str:
    """
    Detect MIME type based on file extension and magic numbers.
    Supports videos, executables, PDFs, images, audio, documents, and more.
    """
    # First check by file extension
    ext = os.path.splitext(file_path)[1].lower()
    mime_from_ext = get_mime_from_extension(ext)
    
    # For certain types, verify with magic numbers
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            mime_from_magic = get_mime_from_magic(header)
            
            # If magic number detection is more specific, use it
            if mime_from_magic and mime_from_magic != 'application/octet-stream':
                return mime_from_magic
                
    except (IOError, OSError):
        pass
    
    return mime_from_ext

# Looks at file extensions and maps them to correct MIME type
def get_mime_from_extension(ext: str) -> str:
    """Get MIME type from file extension."""
    ext_to_mime = {
        # Images
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        '.ico': 'image/x-icon',
        '.svg': 'image/svg+xml',
        
        # Audio
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.aac': 'audio/aac',
        '.wma': 'audio/x-ms-wma',
        '.m4a': 'audio/mp4',
        
        # Video
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.m4v': 'video/mp4',
        '.3gp': 'video/3gpp',
        '.ts': 'video/mp2t',
        
        # Documents
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',
        '.rtf': 'application/rtf',
        
        # Text files
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'text/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.csv': 'text/csv',
        '.md': 'text/markdown',
        '.yaml': 'text/yaml',
        '.yml': 'text/yaml',
        
        # Archives
        '.zip': 'application/zip',
        '.rar': 'application/vnd.rar',
        '.7z': 'application/x-7z-compressed',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.bz2': 'application/x-bzip2',
        '.xz': 'application/x-xz',
        
        # Executables
        '.exe': 'application/vnd.microsoft.portable-executable',
        '.msi': 'application/x-msi',
        '.dll': 'application/vnd.microsoft.portable-executable',
        '.com': 'application/x-msdownload',
        '.bat': 'application/x-bat',
        '.cmd': 'application/x-bat',
        '.sh': 'application/x-sh',
        '.deb': 'application/vnd.debian.binary-package',
        '.rpm': 'application/x-rpm',
        '.dmg': 'application/x-apple-diskimage',
        '.pkg': 'application/x-newton-compatible-pkg',
        '.app': 'application/x-apple-app',
        
        # Programming files
        '.py': 'text/x-python',
        '.java': 'text/x-java-source',
        '.c': 'text/x-c',
        '.cpp': 'text/x-c++',
        '.h': 'text/x-c',
        '.hpp': 'text/x-c++',
        '.cs': 'text/x-csharp',
        '.php': 'text/x-php',
        '.rb': 'text/x-ruby',
        '.go': 'text/x-go',
        '.rs': 'text/x-rust',
        '.swift': 'text/x-swift',
        '.kt': 'text/x-kotlin',
        
        # Fonts
        '.ttf': 'font/ttf',
        '.otf': 'font/otf',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.eot': 'application/vnd.ms-fontobject',
        
        # Other common types
        '.bin': 'application/octet-stream',
        '.iso': 'application/x-iso9660-image',
        '.torrent': 'application/x-bittorrent',
        '.sqlite': 'application/vnd.sqlite3',
        '.db': 'application/x-sqlite3',
    }
    
    return ext_to_mime.get(ext, 'application/octet-stream')

# Reads the first 16 bytes of a file to verify actual type
def get_mime_from_magic(header: bytes) -> str:
    """Detect MIME type from file magic numbers (first 16 bytes)."""
    if len(header) < 4:
        return 'application/octet-stream'
    
    # PDF
    if header.startswith(b'%PDF'):
        return 'application/pdf'
    
    # PNG
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    
    # JPEG
    if header.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    
    # GIF
    if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return 'image/gif'
    
    # BMP
    if header.startswith(b'BM'):
        return 'image/bmp'
    
    # WAV
    if header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WAVE':
        return 'audio/wav'
    
    # MP3
    if header.startswith(b'ID3') or (header[0:2] == b'\xff\xfb'):
        return 'audio/mpeg'
    
    # MP4/M4V/M4A
    if len(header) >= 8 and header[4:8] in [b'ftyp', b'mdat', b'moov']:
        return 'video/mp4'
    
    # AVI
    if header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'AVI ':
        return 'video/x-msvideo'
    
    # ZIP files (also covers DOCX, XLSX, etc.)
    if header.startswith(b'PK\x03\x04') or header.startswith(b'PK\x05\x06'):
        return 'application/zip'
    
    # RAR
    if header.startswith(b'Rar!\x1a\x07\x00') or header.startswith(b'Rar!\x1a\x07\x01\x00'):
        return 'application/vnd.rar'
    
    # 7-Zip
    if header.startswith(b'7z\xbc\xaf\x27\x1c'):
        return 'application/x-7z-compressed'
    
    # Windows executable
    if header.startswith(b'MZ'):
        return 'application/vnd.microsoft.portable-executable'
    
    # ELF executable (Linux)
    if header.startswith(b'\x7fELF'):
        return 'application/x-executable'
    
    # Mach-O executable (macOS)
    if header.startswith(b'\xfe\xed\xfa\xce') or header.startswith(b'\xfe\xed\xfa\xcf'):
        return 'application/x-mach-binary'
    
    return 'application/octet-stream'

# Reverse process to get file extension from MIME type
# When decoding, this converts MIME type back to the proper file extension
def get_extension_from_mime(mime_type: str) -> str:
    """Get appropriate file extension from MIME type."""
    mime_to_ext = {
        # Images
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/gif': '.gif',
        'image/bmp': '.bmp',
        'image/webp': '.webp',
        'image/tiff': '.tiff',
        'image/x-icon': '.ico',
        'image/svg+xml': '.svg',
        
        # Audio
        'audio/wav': '.wav',
        'audio/mpeg': '.mp3',
        'audio/ogg': '.ogg',
        'audio/flac': '.flac',
        'audio/aac': '.aac',
        'audio/x-ms-wma': '.wma',
        'audio/mp4': '.m4a',
        
        # Video
        'video/mp4': '.mp4',
        'video/x-msvideo': '.avi',
        'video/quicktime': '.mov',
        'video/x-ms-wmv': '.wmv',
        'video/x-flv': '.flv',
        'video/webm': '.webm',
        'video/x-matroska': '.mkv',
        'video/3gpp': '.3gp',
        'video/mp2t': '.ts',
        
        # Documents
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/vnd.oasis.opendocument.text': '.odt',
        'application/vnd.oasis.opendocument.spreadsheet': '.ods',
        'application/vnd.oasis.opendocument.presentation': '.odp',
        'application/rtf': '.rtf',
        
        # Text files
        'text/plain': '.txt',
        'text/html': '.html',
        'text/css': '.css',
        'text/javascript': '.js',
        'application/json': '.json',
        'application/xml': '.xml',
        'text/csv': '.csv',
        'text/markdown': '.md',
        'text/yaml': '.yaml',
        
        # Archives
        'application/zip': '.zip',
        'application/vnd.rar': '.rar',
        'application/x-7z-compressed': '.7z',
        'application/x-tar': '.tar',
        'application/gzip': '.gz',
        'application/x-bzip2': '.bz2',
        'application/x-xz': '.xz',
        
        # Executables
        'application/vnd.microsoft.portable-executable': '.exe',
        'application/x-msi': '.msi',
        'application/x-msdownload': '.com',
        'application/x-bat': '.bat',
        'application/x-sh': '.sh',
        'application/vnd.debian.binary-package': '.deb',
        'application/x-rpm': '.rpm',
        'application/x-apple-diskimage': '.dmg',
        'application/x-newton-compatible-pkg': '.pkg',
        'application/x-apple-app': '.app',
        'application/x-executable': '',  # No extension for ELF
        'application/x-mach-binary': '',  # No extension for Mach-O
        
        # Programming files
        'text/x-python': '.py',
        'text/x-java-source': '.java',
        'text/x-c': '.c',
        'text/x-c++': '.cpp',
        'text/x-csharp': '.cs',
        'text/x-php': '.php',
        'text/x-ruby': '.rb',
        'text/x-go': '.go',
        'text/x-rust': '.rs',
        'text/x-swift': '.swift',
        'text/x-kotlin': '.kt',
        
        # Fonts
        'font/ttf': '.ttf',
        'font/otf': '.otf',
        'font/woff': '.woff',
        'font/woff2': '.woff2',
        'application/vnd.ms-fontobject': '.eot',
        
        # Other
        'application/x-iso9660-image': '.iso',
        'application/x-bittorrent': '.torrent',
        'application/vnd.sqlite3': '.sqlite',
        'application/x-sqlite3': '.db',
    }
    
    return mime_to_ext.get(mime_type, '.bin')