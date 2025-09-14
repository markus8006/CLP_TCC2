import ipaddress

def get_subnet_from_ip(ip : str) -> str:
    """ Recebe um IP e retorna sua subrede

    Args:
        ip (str): _description_

    Returns:
        str: Rede_X.Y.Z.0-24
    """
    try:
        #Cria um objeto de endereço IP
        ip_obj : ipaddress.IPv4Address | ipaddress.IPv6Address
        ip_obj = ipaddress.ip_address(ip)

        #ignora IPs de loopback (localhost)
        if ip_obj.is_loopback:
            return None
        
        #Calcula a rede com máscara /24 
        rede = ipaddress.ip_network(f"{ip}/24", strict=False)

        #Formata o nome do grupo
        return f"Rede_{rede.network_address}-{rede.prefixlen}"
    
    except ValueError:
        #retorna None se a string do IP foor inválida
        return None
    
    except Exception as e:
        return None