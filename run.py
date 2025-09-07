# /run.py
from clp_app import create_app

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' permite que a aplicação seja acessada por outros
    # dispositivos na mesma rede, não apenas pelo seu próprio computador.
    app.run(host='0.0.0.0', port=5000, debug=True)

    