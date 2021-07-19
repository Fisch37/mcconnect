# mcconnect
Provides modules that aid in interacting with a Minecraft server via Python code

## query
This module implements the Minecraft Query protocol.
It contains one class by the name `QueryConnection`.
This class needs an IP and can get a custom port at initialisation. The object can then be used to request information about the server specified by IP and port.
_Note: IP means something like 127.0.0.1, not google.com_
The port specified at creation should be the query port of the server.

There are two types of requests. The `basicStat` and the `fullStat`. Each have their own command. 
The Basic Stat provides:
  + MOTD: "MOTD"
  + Game type (e.g. survival): "gametype"
  + map name  (e.g. world): "map"
  + the number of players online: "numplayers"
  + the maximum number of players online: "maxplayers"
  + the hostport of the minecraft server (not the same as the query port): "hostport"
  + the host ip (this result can be a bit wonky): "hostip"

The function returns a dictionary with this information.

The Full Stat meanwhile provides some more information like:
  + The game id (which is in most cases Minecraft): "game_id"
  + The game version (specified like in the launcher): "version"
  + The name of a plugin loader, if available: "pluginhost"
  + The plugins loaded: "plugins"
  + The names of every player online: "players"

The "players" property is a list of strings.

## rcon
Rcon is short for "Remote Console". This protocol can be used to send commands remotely to a Minecraft Server.
To use this module, you only need to create a new `Rconnection` object with the ip of the server, its port, and a password (, which can be set in `server.properties` on the host). The coroutine `Rconnection.start()` will use this information to connect the session. Via `Rconnection.command(string)` you can then enter commands as you wish.

## connect
This module provides the ability to connect to a external host and launch a server on it.
At creation it requires 
  + a username and password for the ssh session established,
  + a command which will start the server,
  + a command which will wake the host if needed,
  + a command which will shut down the host if needed,
and can optionally have
  + a custom ssh port,
  + a True flag to disable host key checking,
  + and a command to ping the host with

The wakeCommand needs to cause the machine to boot in some way and then wait for it to have booted. If it is successful, it must return exit code 0.
The pingCommand must in some way check if the host is awake and return exit code 0 if that is true.

The class provides some functions to interact with the server.
### isAwake
This function checks if the host is awake. It is a coroutine.
### wakeUp
This function will boot up the machine. It is a coroutine.
### connect
This function will establish a new ssh connection to the host. It returns the new connection and is a coroutine.
### wake
This function combines the two above commands to one. It will raise a WakeError if the host couldn't be woken up and is a coroutine.
### start
This function starts the server via the launchCommand specified at init. It will raise a `ConnectionError` if it cannot find a ssh connection, will return the new `asyncssh.SSHClientProcess` and is a coroutine.
### writeCommand
This function can send a command to the server (if it is connected). Should the connection be closing at that point in time, it will raise a `CommandError`.
### processWatcher
Currently, this function will print out any data it gets from a `asyncssh.SSHClientProcess` such as the one provided by the `start` function.
The process needs to be provided as an argument.
