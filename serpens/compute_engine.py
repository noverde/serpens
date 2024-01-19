import logging
import requests

logger = logging.getLogger(__name__)

METADATA_HEADERS = {"Metadata-Flavor": "Google"}
METADATA_VM_IDENTITY_URL = (
    "http://metadata.google.internal/computeMetadata/v1/"
    "instance/service-accounts/default/identity?"
    "audience={audience}&format={format}&licenses={licenses}"
)


def acquire_token(audience, format="standard", licenses=True):
    url = METADATA_VM_IDENTITY_URL.format(audience=audience, format=format, licenses=licenses)

    response = requests.get(url, headers=METADATA_HEADERS)

    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response content: {response.content}")

    if not response.ok:
        return None

    return response.text
