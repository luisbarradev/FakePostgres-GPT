import asyncio
import struct
import os
import openai
import re
from enum import Enum

openai.api_key = os.getenv('OPENAI_API_KEY')

PROTOCOL_VERSION = 196608  # Versión de protocolo 3.0
SSL_REQUEST_CODE = 80877103  # Código de solicitud SSL
SSL_DENIED_RESPONSE = b'N'

AUTHENTICATION_OK = 0

class MessageType(Enum):
    QUERY = b'Q'
    TERMINATE = b'X'

READY_STATUS_IDLE = b'I'

# Mensajes de respuesta
AUTHENTICATION_OK_RESPONSE = b'R' + struct.pack('!I', 8) + struct.pack('!I', AUTHENTICATION_OK)
READY_FOR_QUERY_RESPONSE = b'Z' + struct.pack('!I', 5) + READY_STATUS_IDLE

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Conexión aceptada desde {addr}")

    try:
        while True:
            length = await read_message_length(reader)
            startup_message = await reader.readexactly(length - 4)
            protocol_version = struct.unpack('!I', startup_message[:4])[0]

            if protocol_version == SSL_REQUEST_CODE:
                await handle_ssl_request(writer)
                continue
            elif protocol_version == PROTOCOL_VERSION:
                params = parse_startup_parameters(startup_message[4:])
                print(f"Parámetros de conexión: {params}")
                await authenticate_client(writer)
                await process_queries(reader, writer)
                break 
            else:
                print(f"Versión de protocolo desconocida: {protocol_version}")
                break

    except asyncio.IncompleteReadError:
        pass
    finally:
        print(f"Conexión desde {addr} cerrada")
        writer.close()
        await writer.wait_closed()

async def read_message_length(reader):
    length_bytes = await reader.readexactly(4)
    length = struct.unpack('!I', length_bytes)[0]
    return length

async def handle_ssl_request(writer):
    print("Solicitud SSL recibida")
    writer.write(SSL_DENIED_RESPONSE)
    await writer.drain()

def parse_startup_parameters(params_data):
    params = {}
    items = params_data.split(b'\x00')
    # Eliminar cadenas vacías al final
    while items and items[-1] == b'':
        items.pop()
    if len(items) % 2 != 0:
        print("Advertencia: Número impar de elementos en los parámetros del mensaje de inicio.")

    for key_bytes, value_bytes in zip(items[::2], items[1::2]):
        key = key_bytes.decode()
        value = value_bytes.decode()
        params[key] = value
    return params

async def authenticate_client(writer):
    writer.write(AUTHENTICATION_OK_RESPONSE)
    await writer.drain()

    writer.write(READY_FOR_QUERY_RESPONSE)
    await writer.drain()

async def process_queries(reader, writer):
    while True:
        try:
            msg_type = await reader.readexactly(1)
            length = await read_message_length(reader)
            msg = await reader.readexactly(length - 4)

            if msg_type == MessageType.QUERY.value:
                query = msg.decode().strip()
                print(f"Consulta recibida: {query}")
                if query.lower().startswith('select'):
                    await handle_select_query(writer, query)
                else:
                    # TODO: Manejar otras consultas (INSERT, UPDATE)
                    await send_command_complete(writer, "OK")
                    await send_ready_for_query(writer)
            elif msg_type == MessageType.TERMINATE.value:
                break
            else:
                print(f"Tipo de mensaje no soportado recibido: {msg_type}")
                break
        except asyncio.IncompleteReadError:
            break

async def handle_select_query(writer, query):

    data, columns = await generate_fake_data(query)
    if data is None or columns is None:
        await send_empty_query_response(writer)
        await send_ready_for_query(writer)
        return

    await send_row_description(writer, columns)

    for row in data:
        await send_data_row(writer, row)

    await send_command_complete(writer, f"SELECT {len(data)}")

    await send_ready_for_query(writer)

async def generate_fake_data(query):
    try:
        table_name, conditions, limit = parse_select_query(query)
        if not table_name:
            print("No se pudo extraer el nombre de la tabla de la consulta.")
            return None, None

        prompt = f"Genera una lista de diccionarios en formato JSON que representen filas de la tabla '{table_name}' en una base de datos."
        if conditions:
            prompt += f" Cada fila debe satisfacer la condición: {conditions}."
        prompt += " Cada diccionario debe tener nombres de columnas como claves y valores realistas."
        if limit:
            prompt += f" Proporciona {limit} filas."
        else:
            prompt += " Proporciona 10 filas."
        prompt += " No incluyas texto adicional o formato, solo proporciona los datos JSON puros."


        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Generas datos para tablas de bases de datos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        generated_text = response['choices'][0]['message']['content']
        print(f"Texto generado: {generated_text}")
        data, columns = parse_generated_data(generated_text)
        return data, columns

    except Exception as e:
        print(f"Error al generar datos: {e}")
        return None, None

def parse_select_query(query):
    try:
        query = query.strip().rstrip(';')
        # Expresión regular para analizar consultas SELECT
        pattern = re.compile(
            r"SELECT\s+(?P<columns>.+?)\s+FROM\s+(?P<table>\w+)(?:\s+WHERE\s+(?P<where>.+?))?(?:\s+LIMIT\s+(?P<limit>\d+))?",
            re.IGNORECASE
        )
        match = pattern.match(query)
        if not match:
            return None, None, None
        table_name = match.group('table')
        conditions = match.group('where')
        limit = match.group('limit')
        return table_name, conditions, limit
    except Exception as e:
        print(f"Error al analizar la consulta: {e}")
        return None, None, None

def parse_generated_data(text):
    try:
        # Remover formato Markdown si está presente
        if text.startswith("```"):
            # Remover backticks y etiquetas de lenguaje
            text = re.sub(r"```(\w+)?", "", text).strip()
            text = text.rstrip("```").strip()

        # Intentar cargar el JSON
        import json
        data = json.loads(text)
        if not isinstance(data, list):
            print("Los datos generados no son una lista.")
            return None, None
        if not data:
            print("Los datos generados están vacíos.")
            return None, None
        columns = list(data[0].keys())
        return data, columns
    except json.JSONDecodeError as e:
        print(f"Error al parsear el JSON: {e}")
        return None, None

async def send_row_description(writer, columns):
    fields = []
    for column in columns:
        field = (
            column.encode() + b'\x00' +
            struct.pack('!I', 0) +      # OID de tabla
            struct.pack('!h', 0) +      # Número de atributo de columna
            struct.pack('!I', 25) +     # OID de tipo de datos (25 = TEXT)
            struct.pack('!h', -1) +     # Tamaño de tipo de datos (-1 para variable)
            struct.pack('!I', 0) +      # Modificador de tipo
            struct.pack('!h', 0)        # Código de formato
        )
        fields.append(field)

    num_fields = len(fields)
    body = struct.pack('!h', num_fields) + b''.join(fields)
    message = b'T' + struct.pack('!I', len(body) + 4) + body
    writer.write(message)
    await writer.drain()

async def send_data_row(writer, row):
    fields = []
    for value in row.values():
        if value is None:
            # -1 indica valor NULL
            fields.append(struct.pack('!I', -1))
        else:
            val_bytes = str(value).encode()
            fields.append(struct.pack('!I', len(val_bytes)) + val_bytes)
    num_fields = len(fields)
    body = struct.pack('!h', num_fields) + b''.join(fields)
    message = b'D' + struct.pack('!I', len(body) + 4) + body
    writer.write(message)
    await writer.drain()

async def send_command_complete(writer, command_tag):
    # Incluir el terminador nulo en la etiqueta de comando
    command_tag_bytes = command_tag.encode('utf-8') + b'\x00'
    # Calcular la longitud del contenido del mensaje
    length = len(command_tag_bytes) + 4  # La longitud incluye el campo de longitud y la etiqueta de comando
    # Construir el mensaje
    message = b'C' + struct.pack('!I', length) + command_tag_bytes
    writer.write(message)
    await writer.drain()

async def send_empty_query_response(writer):
    message = b'I' + struct.pack('!I', 4)
    writer.write(message)
    await writer.drain()

async def send_ready_for_query(writer):
    writer.write(READY_FOR_QUERY_RESPONSE)
    await writer.drain()

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 5432)
    print("Servidor escuchando en el puerto 5432")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
