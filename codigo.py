import socket
import threading
import time
import multiprocessing

# ===============================
# Servidor central de tráfico
# ===============================

def ejecutarServidor():
    host = '127.0.0.1'
    port = 65432
    clientesConectados = []
    bloqueoClientes = threading.Lock()

    def manejarCliente(conn, addr):
        idSemaforo = "desconocido"
        try:
            data = conn.recv(1024)
            if data:
                idSemaforo = data.decode('utf-8')
                with bloqueoClientes:
                    clientesConectados.append({"conn": conn, "id": idSemaforo})
                print(f"[Servidor] Semáforo registrado: {idSemaforo}")

            while True:
                time.sleep(10) # Pausa larga para no consumir CPU innecesariamente

        finally:
            with bloqueoClientes:
                clientesConectados[:] = [c for c in clientesConectados if c["conn"] != conn]
            conn.close()
            print(f"[Servidor] Semáforo desconectado: {idSemaforo}")

    def coordinadorTrafico():
        print("[Servidor] Coordinador de tráfico iniciado...")
        while True:
            time.sleep(2)
            with bloqueoClientes:
                if len(clientesConectados) >= 2:
                    copiaClientes = list(clientesConectados)
                    if len(copiaClientes) >= 2:
                         ejecutarCiclo(copiaClientes[0], copiaClientes[1])
                else:
                    print("[Servidor] Esperando al menos 2 semáforos...")

    def ejecutarCiclo(semaforoA, semaforoB):
        try:
            # --- FASE 1 ---
            print(f"\n[Servidor] CICLO NUEVO: {semaforoA['id']} → VERDE | {semaforoB['id']} → ROJO")
            semaforoA['conn'].sendall(b'VERDE')
            semaforoB['conn'].sendall(b'ROJO')

            confA = semaforoA['conn'].recv(1024)
            confB = semaforoB['conn'].recv(1024)
            print(f"[Servidor] Confirmaciones recibidas: {confA.decode()}, {confB.decode()}")

            # --- FASE 2 ---
            print(f"[Servidor] {semaforoA['id']} → AMARILLO")
            semaforoA['conn'].sendall(b'AMARILLO')
            confA = semaforoA['conn'].recv(1024)
            print(f"[Servidor] Confirmación recibida: {confA.decode()}")

            # --- FASE 3 ---
            print(f"[Servidor] {semaforoA['id']} → ROJO | {semaforoB['id']} → VERDE")
            semaforoA['conn'].sendall(b'ROJO')
            semaforoB['conn'].sendall(b'VERDE')
            confA = semaforoA['conn'].recv(1024)
            confB = semaforoB['conn'].recv(1024)
            print(f"[Servidor] Confirmaciones recibidas: {confA.decode()}, {confB.decode()}")

            # --- FASE 4 ---
            print(f"[Servidor] {semaforoB['id']} → AMARILLO")
            semaforoB['conn'].sendall(b'AMARILLO')
            confB = semaforoB['conn'].recv(1024)
            print(f"[Servidor] Confirmación recibida: {confB.decode()}")

        except Exception as e:
            print(f"[Servidor] Error durante el ciclo: {e}. Un semáforo pudo haberse desconectado.")


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidorSocket:
        servidorSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidorSocket.bind((host, port))
        servidorSocket.listen()
        print(f"[Servidor] Ejecutándose en {host}:{port}")

        hiloCoordinador = threading.Thread(target=coordinadorTrafico, daemon=True)
        hiloCoordinador.start()

        while True:
            conn, addr = servidorSocket.accept()
            threading.Thread(target=manejarCliente, args=(conn, addr), daemon=True).start()


# ===============================
# Cliente semáforo
# ===============================

def ejecutarSemaforo(idSemaforo):
    host = '127.0.0.1'
    port = 65432
    time.sleep(1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((host, port))
            print(f"[{idSemaforo}] Conectado al servidor")
            sock.sendall(idSemaforo.encode('utf-8'))

            while True:
                orden = sock.recv(1024).decode('utf-8')
                if not orden:
                    break

                print(f"[{idSemaforo}] Orden recibida → {orden}")
                # El cliente confirma que recibió y procesó la orden
                sock.sendall(f"OK-{orden}".encode('utf-8'))
        except ConnectionRefusedError:
            print(f"[{idSemaforo}] No se pudo conectar al servidor")
        except Exception as e:
            print(f"[{idSemaforo}] Error: {e}")
    print(f"[{idSemaforo}] Finalizado")


# ===============================
# Orquestador de procesos
# ===============================

if __name__ == '__main__':
    print("Iniciando simulación distribuida de semáforos...\n")

    procesoServidor = multiprocessing.Process(target=ejecutarServidor, daemon=True)
    procesoSemaforo1 = multiprocessing.Process(target=ejecutarSemaforo, args=("AvenidaPrincipal",))
    procesoSemaforo2 = multiprocessing.Process(target=ejecutarSemaforo, args=("CalleSecundaria",))

    procesoServidor.start()
    time.sleep(1) # Dar un segundo al servidor para que inicie bien
    procesoSemaforo1.start()
    procesoSemaforo2.start()

    try:
        # La simulación se ejecuta por 30 segundos
        time.sleep(30)
    finally:
        print("\nTerminando la simulación...")
        procesoServidor.terminate()
        procesoSemaforo1.terminate()
        procesoSemaforo2.terminate()
        print("Simulación finalizada")