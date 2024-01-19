import requests

METADATA_HEADERS = {"Metadata-Flavor": "Google"}
METADATA_VM_IDENTITY_URL = (
    "http://metadata.google.internal/computeMetadata/v1/"
    "instance/service-accounts/default/identity?"
    "audience={audience}&format={format}&licenses={licenses}"
)


def acquire_token(audience, format="standard", licenses=True):
    url = METADATA_VM_IDENTITY_URL.format(audience=audience, format=format, licenses=licenses)

    response = requests.get(url, headers=METADATA_HEADERS)

    if not response.ok:
        return None

    return response.text
