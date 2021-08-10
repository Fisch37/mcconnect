import asyncio, random
from mcconnect.errors import *

MAX_CS_LENGTH = 1446
MAX_SC_LENGTH = 4096

BUFFER_SIZE = 8192

class RequestTypes:
    LOGIN   = 3
    COMMAND = 2
    RESPONSE= 0

    __INVALID__ = 200

class PacketError(Exception):
    """Something went wrong with the packet
    """
    pass

def createRconPacket(reqId : int, type : int, payload : str,*,forcedLength : int = None):
    if len(payload)+1 > MAX_CS_LENGTH: raise PacketError("Payload too large") # Includes the null terminator

    byteReqId   = reqId.to_bytes(4,"little",signed=True)
    byteType    = type.to_bytes(4,"little",signed=True)
    bytePayload = payload.encode("ascii") + b"\x00"

    lengthlessPacket = byteReqId + byteType + bytePayload + b"\x00"
    packet = int.to_bytes(len(lengthlessPacket) if forcedLength == None else forcedLength,4,"little",signed=True) + lengthlessPacket
    return packet

def extractFromPacket(packet : bytes):
    byteLength  = packet[:4]
    byteReqId   = packet[4:8]
    byteType    = packet[8:12]
    bytePayload = packet[12:-2]
    
    return (
        int.from_bytes(byteLength,"little",signed=True) , 
        int.from_bytes(byteReqId ,"little",signed=True) ,
        int.from_bytes(byteType  ,"little",signed=True) ,
        bytePayload
    )

def removeColours(payload : bytes):
    discoloured = b""
    for part in payload.split(b"\xa7"):
        discoloured += part[1:]
        pass
    return discoloured
    pass

def createReqId():
    return int.from_bytes(random.randbytes(3) + b"\x00","little",signed=True)
    pass

class Rconnection:
    def __init__(self,ip : str,port : int,password : str):
        self.ip = ip
        self.port = port
        self.password = password
        
        self.connection : tuple[asyncio.StreamReader,asyncio.StreamWriter] = None
        self.reqId = createReqId()
        pass

    async def connect(self):
        reader, writer = await asyncio.open_connection(self.ip,self.port)
        self.connection = (reader, writer)
        pass

    async def sendData(self,type : int,payload : str,*, returnRaw : bool = False):
        if self.connection == None or self.connection[0].at_eof() or self.connection[1].is_closing(): raise ConnectionError("No connection established or connection is closed")
        packet : bytes = createRconPacket(self.reqId,type,payload)
        
        reader, writer = self.connection
        await writer.drain()
        writer.write(packet)

        if type == RequestTypes.COMMAND:
            contraPacket = createRconPacket(self.reqId,RequestTypes.__INVALID__,"")
            writer.write(contraPacket)
            expectedEndPackage = createRconPacket(self.reqId,RequestTypes.RESPONSE,f"Unknown request {hex(RequestTypes.__INVALID__)[2:]}")

            finished = False
            buffer = b""
            while not finished:
                buffer += await reader.read(BUFFER_SIZE)
                finished = buffer.endswith(expectedEndPackage)
                pass
            rawPackets : bytes = buffer.removesuffix(expectedEndPackage)
            
            packets : list[bytes] = []
            packetBeginPos = 0
            while packetBeginPos < len(rawPackets):
                thisPacketLen : int = int.from_bytes(rawPackets[packetBeginPos:packetBeginPos+4],"little",signed=True) + 4
                packets.append(rawPackets[packetBeginPos:packetBeginPos+thisPacketLen])
                packetBeginPos+=thisPacketLen
                pass

            data = b""
            for packet in packets:
                packetLength, packetReqId, packetType, packetPayload = extractFromPacket(packet)
                data+=packetPayload
                pass
            return data.decode("ascii")
            pass
        elif type == RequestTypes.LOGIN:
            data : bytes = await reader.read(BUFFER_SIZE)
        
            if not returnRaw:
                dataLength = int.from_bytes(data[:4],"little",signed=True)
                if dataLength + 4 != len(data): raise PacketError

                dataId = int.from_bytes(data[4:8],"little",signed=True)
                if dataId == -1: raise AuthError("Authentication failed")
                elif dataId != self.reqId: raise CommandError("Response did not match the request")

                if returnRaw:
                    return data
                dataType = data[8:12]
                dataPayload = data[12:-2]

                return dataPayload
            else:
                return data
            pass
        pass

    async def command(self,cmd : str):
        return await self.sendData(RequestTypes.COMMAND,cmd)
        pass

    async def login(self):
        data : bytes = await self.sendData(RequestTypes.LOGIN,self.password)
        pass

    async def start(self):
        await self.connect()
        await self.login()
        pass
    pass

async def __main__():
    rcon = Rconnection("127.0.0.1",25575,"test")
    await rcon.start()
    while True:
        print(await rcon.command(input("Please enter a command: ")))
    pass

if __name__=="__main__":
    asyncio.run(__main__())
    pass