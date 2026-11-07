import re
import io
import gc
from typing import Optional

class DataSecurityGuard:
    @staticmethod
    def sanitize_log(message: str) -> str:
        """
        Masks Indian Tax PII (PAN, Aadhaar, Bank Account Numbers).
        """
        # 1. Mask PAN (ABCDE1234F -> ABCDE****F)
        masked = re.sub(r"\b([A-Z]{5})\d{4}([A-Z])\b", r"\1****\2", message)
        
        # 2. Mask Aadhaar (12 digits with explicit space or hyphen delimiter: 1234 5678 9012)
        masked = re.sub(r"\b\d{4}[\s\-]\d{4}[\s\-](\d{4})\b", r"XXXX-XXXX-\1", masked)
        
        # 3. Mask Bank Account Numbers (continuous 9 to 18 digits, keeps last 4 digits)
        masked = re.sub(r"\b\d{5,14}(\d{4})\b", r"*******\1", masked)
        
        return masked

    @staticmethod
    def zero_memory_buffer(buffer: Optional[io.BytesIO]):
        """
        Wipes sensitive in-memory byte buffers and triggers garbage collection.
        """
        if buffer:
            try:
                buffer.seek(0)
                buffer.write(b"\x00" * buffer.getbuffer().nbytes)
                buffer.close()
            except Exception:
                pass
        gc.collect()