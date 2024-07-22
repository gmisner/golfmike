import logging
import requests
from tenacity import retry, wait_fixed, stop_after_attempt

logger = logging.getLogger(__name__)


@retry(wait=wait_fixed(2), stop=stop_after_attempt(5))
def validate_xml_external(xml_data: str, xsd_url: str = None) -> bool:
    try:
        url = "https://www.freeformatter.com/xml-validator-xsd.html"
        files = {
            "xml-data": ("file.xml", xml_data, "application/xml"),
        }
        if xsd_url:
            files["xsd-schema-url"] = (None, xsd_url)
        response = requests.post(url, files=files)
        if response.status_code == 200:
            logger.info("XML validation successful.")
            return True
        else:
            logger.error(
                f"External validator returned status code: {response.status_code}"
            )
            return False
    except requests.RequestException as e:
        logger.error(f"Request to external validator failed: {e}")
        raise
