import ipaddress

YGGDRASIL_NETWORK = ipaddress.ip_network("200::/7")

def is_yggdrasil(addr):
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip in YGGDRASIL_NETWORK
