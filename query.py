"""Fisch37 2021.06.12\n
This library provides handling for the query protocol of Minecraft used to get data about a server.
For information on how this protocol works, visit https://wwww.wiki.vg/Query (not my page)
"""

import asyncio, random, logging

CHALLENGE_REQ_TYPE = 0x09
STAT_REQ_TYPE      = 0x00

class __QueryProtocol__:
    """The asyncio.BaseProtocol adaptation for the QueryConnection class.\n
    This shouldn't be initialised outside of the QueryConnection.
    """
    def __init__(self, sessionId : int, isFullStat : bool,conv_finished : asyncio.Future):
        self.sessionId  : int  = sessionId
        self.isFullStat : bool = isFullStat
        self.challengeToken : int = None
        self.result = b""

        self.transport = None
        self.conv_finished : asyncio.Future = conv_finished
        pass
    def connection_made(self,transport):
        self.transport = transport # Saves the transport that was created to be used later
        transport.sendto(createQueryPacket(self.sessionId,CHALLENGE_REQ_TYPE,b"")) # Send a challenge token request
        pass

    def datagram_received(self,data,addr):
        logging.info(f"Data received: {data}")
        respType = data[0] # Get type in the response
        sessionId = int.from_bytes(data[1:5],"big") # Get & Decode the session Id
        if sessionId != self.sessionId: # Protect against potential leaks from other sources
            raise ValueError
        if respType == CHALLENGE_REQ_TYPE: # If received data is in response to a token request do this
            challengeToken = int(data[5:-1]) # Get token from data
            self.challengeToken = challengeToken # Safe token in the protocol
            # Send actual query with the new challenge token. 
            requestPayload = self.challengeToken.to_bytes(4,"big")
            requestPayload += b"\x00"*4 if self.isFullStat else b"" # Add required padding if a full stat is wanted

            self.transport.sendto(createQueryPacket(self.sessionId,STAT_REQ_TYPE,requestPayload)) # Send the query
            pass
        else: # If result from query is received
            self.result = data
            self.conv_finished.set_result(data)
        pass

    def error_received(self,data,addr):
        logging.error(f"Error with UDP Connection: {data}")
        pass

    def connection_lost(self,exc):
        pass

def createQueryPacket(sessionId : int, type : int, payload : bytes):
    packet = b"\xFE\xFD" # Packet with Magic already attached
    packet += type.to_bytes(1,"big") # Type 0 for base stat, 1 for full stat, 09 for challenge token
    packet += sessionId.to_bytes(4,"big") # Session ID as Int32
    packet += payload
    return packet
    pass

def createSessionId():
    sessionId = "0x"
    for i in range(4):
        sessionId += "0" + hex(random.randrange(0,16))[-1]
        pass
    return eval(sessionId)
    pass

class QueryConnection:
    """Handles Query Connections to a Minecraft Server.\n
    If you host a minecraft server, you will need to set enable-query = true in your server.properties.
    """
    def __init__(self,ip,port=25565):
        self.ip = ip
        self.port = port
        self.sessionId = createSessionId()
        pass

    def newSessionId(self):
        """Creates a new session Id\n
        This will work fine if used manually, but in most cases isn't neccessary.
        """
        sessionId = createSessionId()
        self.sessionId = sessionId
        return sessionId
        pass

    async def sendData(self, packet : bytes):
        """Sends raw data to the server\n
        Note: This should not be used manually
        """
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        transport, protocol = await loop.create_datagram_endpoint(lambda: __QueryProtocol__(packet, future), remote_addr=(self.ip,self.port))
        await future
        result : bytes = protocol.result
        return result

    async def basicStat(self):
        """Retrieves the basic statistics of a server.\n
        This includes: MOTD, gametype (creative, survival, etc.), map name, number of players online, maximum number of players, hostport, and hostip (this output can be questionable)
        """
        loop = asyncio.get_event_loop()
        future : asyncio.Future = loop.create_future()
        transport, protocol = await loop.create_datagram_endpoint(lambda: __QueryProtocol__(self.sessionId,False,future), remote_addr=(self.ip,self.port))
        result = await future
        
        logging.debug(f"Base Stat Response: {result}") 
        
        reqType = result[0]

        data : bytes = result[5:]
        retrievedData = {"MOTD":None,"gametype":None,"map":None,"numplayers":None,"maxplayers":None,"hostport":None,"hostip":None}
        remainingData = data
        for i in range(5):
            terminator = remainingData.find(b"\x00")
            retrievedData[list(retrievedData.keys())[i]] = remainingData[:terminator]
            
            remainingData = remainingData[terminator+1:]
            pass

        retrievedData["hostport"] = int.from_bytes(remainingData[:2],"little")
        retrievedData["hostip"] = remainingData[2:-1]

        ### Interpretation
        interpreted = {}
        interpreted["MOTD"] = retrievedData["MOTD"].decode("utf-8")
        interpreted["gametype"] = retrievedData["gametype"].decode("utf-8")
        interpreted["map"] = retrievedData["map"].decode("utf-8")
        interpreted["numplayers"] = int(retrievedData["numplayers"])
        interpreted["maxplayers"] = int(retrievedData["maxplayers"])
        interpreted["hostport"] = retrievedData["hostport"]
        interpreted["hostip"] = retrievedData["hostip"].decode("utf-8")

        return interpreted
        pass

    async def fullStat(self):
        """Retrieves the full statistic for a server.\n
        This includes every basic stat plus the following: game_id (generally MINECRAFT), game version (e.g. 1.16.5), pluginhost (e.g. CraftBukkit on Bukkit 1.16.5-R0.1-SNAPSHOT), plugins (if available), and players
        """
        loop = asyncio.get_event_loop()
        future : asyncio.Future = loop.create_future()
        transport, protocol = await loop.create_datagram_endpoint(lambda: __QueryProtocol__(self.sessionId,True,future), remote_addr=(self.ip,self.port))
        result = await future

        logging.debug(f"Full Stat Response: {result}")

        content : bytes = result[5:-1]
        base, players = content.split(b"\x01\x70\x6C\x61\x79\x65\x72\x5F\x00\x00")
        
        baseData = {}
        temp = base.split(b"\x00")
        for i in range(0,len(temp),2):
            if not temp[i] == b'':
                baseData[temp[i].decode("utf-8")] = temp[i+1] # Key Value pairs are behind each other in response
        del temp

        interpretedBase = {}
        interpretedBase["hostname"  ] = baseData["hostname"  ].decode("utf-8")
        interpretedBase["gametype"  ] = baseData["gametype"  ].decode("utf-8")
        interpretedBase["game_id"   ] = baseData["game_id"   ].decode("utf-8")
        interpretedBase["version"   ] = baseData["version"   ].decode("utf-8")
        interpretedBase["map"       ] = baseData["map"       ].decode("utf-8")
        interpretedBase["numplayers"] = int(baseData["numplayers"])
        interpretedBase["maxplayers"] = int(baseData["maxplayers"])
        interpretedBase["hostport"  ] = int(baseData["hostport"  ])
        interpretedBase["hostip"    ] = baseData["hostip"    ].decode("utf-8")
        
        if baseData["plugins"] != b"":
            interpretedBase["pluginhost"] = baseData["plugins"].split(b":")[0]
            interpretedBase["plugins"   ] = [plugins.decode("utf-8") for plugins in baseData["plugins"].split(b":")[1].split(b";")] if len(baseData["plugins"].split(b":")) > 1 else []
            pass
        
        playerList = [player.decode("utf-8") for player in players.split(b"\x00") if player != b""]
        
        interpreted = {}
        interpreted |= interpretedBase
        interpreted    ["players"   ] = playerList

        return interpreted
        pass
    pass